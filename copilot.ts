// The copilot state machine: a port of crescent_vigil/agent/copilot.py.
import { actionsFor, recordEvidence, type Protocol } from "./actions";
import { check } from "./guard";
import { predict, snapshotFeatures, type ModelExport } from "./model";
import { argsortDesc, Index, phaseFromMinute, score, type IndexExport, type RankerT } from "./retrieval";
import { snapshot, type AttRecord, type Snapshot } from "./snapshot";
import { tokens } from "./text";
import { verify } from "./verifier";

const SENT = /(?<=[.!?])\s+(?=[A-Z])/;
const ANALGESIA_WORDS = new Set(["analgesia", "opioid", "morphine", "diamorphine", "oxycodone", "plan", "route", "dose", "agent",
  "first", "line", "subcutaneou", "intravenou", "oral"]);
const HISTORY_WORDS = new Set(["previou", "last", "history", "time", "usual", "prior", "earlier"]);
const PHASES = ["arrival", "early", "ward", "late", "discharge"];

export interface EngineData {
  protocol: Protocol; index: IndexExport; ranker: RankerT; situation_terms: Record<string, string[]>;
  model: ModelExport | null; sources: Record<string, string>;
}

export function recordSituations(snap: Snapshot, P: Protocol): string[] {
  const s = new Set<string>();
  const c = snap.attendance.complaint;
  if (["pain", "chest", "abdominal", "priapism"].includes(c)) s.add("pain");
  if (c === "chest") s.add("chest");
  if (c === "neuro") { s.add("neuro"); s.add("stroke"); }
  if (c === "priapism") s.add("priapism");
  if (c === "abdominal") s.add("abdominal");
  if (c === "fever") { s.add("fever"); s.add("infection"); }
  const v = snap.vitals;
  if (v && Object.keys(v).length) {
    if (v.temp >= P.temp_flag) { s.add("fever"); s.add("infection"); }
    if (v.spo2 < P.spo2_flag || snap.patient.baseline_spo2 - v.spo2 >= P.spo2_drop_flag) { s.add("chest"); s.add("deterioration"); }
  }
  if (snap.plan) s.add("plan");
  return [...s].sort();
}

export function bestSentence(text: string, qtoks: Set<string>): string {
  const sents = text.split(SENT).map((x) => x.trim()).filter(Boolean);
  if (!sents.length) return text;
  let best = 0, bi = 0;
  sents.forEach((x, i) => {
    const sc = [...new Set(tokens(x))].filter((w) => qtoks.has(w)).length;
    if (sc > best) { best = sc; bi = i; }
  });
  return sents[bi];
}

function planPassages(plan: any) {
  if (!plan) return [];
  const pid = plan.plan_id;
  const P = PHASES;
  return [
    { pid: `${pid}.A`, kind: "plan", title: "First line analgesia in the individual plan",
      body: `The signed plan names ${plan.first_line_agent} by the ${plan.route} route as first line analgesia. ${plan.dose_text}.`, phases: P.slice(0, 3) },
    { pid: `${pid}.B`, kind: "plan", title: "Agents to avoid in the individual plan",
      body: "The plan says to avoid " + plan.avoid.join(", ") + "." + (plan.intolerance ? ` Documented intolerance of ${plan.intolerance}.` : ""), phases: P },
    { pid: `${pid}.C`, kind: "plan", title: "Adjuncts and reassessment in the individual plan",
      body: "The plan lists " + plan.adjuncts.join(" and ") + ` as adjuncts and asks for pain reassessment every ${plan.reassess_min} minutes.`, phases: P.slice(0, 3) },
    { pid: `${pid}.D`, kind: "plan", title: "Clinical notes in the individual plan", body: plan.notes, phases: P },
  ];
}

function historyPassages(h: any, patientId: string) {
  const out: any[] = [];
  if (h.attendances) {
    out.push({ pid: `H.${patientId}.S`, kind: "history", title: "Summary of previous attendances",
      body: `${h.attendances} previous attendances with ${h.admissions} admissions; acute chest syndrome ` +
        `after admission ${h.acs_after_admission} times and at arrival ${h.acs_at_arrival} times.` +
        (h.median_door_to_analgesia_min !== null && h.median_door_to_analgesia_min !== undefined
          ? ` Median previous door to analgesia ${pyFixed0(h.median_door_to_analgesia_min)} minutes.` : "") });
  }
  (h.recent || []).forEach((r: any, i: number) => {
    const parts = [`Attendance on ${r.arrival} with ${r.complaint}`];
    if (r.first_agent) parts.push(`first analgesia ${r.first_agent} ${r.first_route} at ${pyFixed0(r.door_to_analgesia_min)} minutes`);
    parts.push(r.admitted ? "admitted" : "discharged from the department");
    if (r.acs) parts.push(r.acs_diagnosis_h ? `acute chest syndrome diagnosed ${pyFixed0(r.acs_diagnosis_h)} hours into the episode` : "acute chest syndrome diagnosed");
    out.push({ pid: `H.${patientId}.${i + 1}`, kind: "history", title: `Previous attendance ${r.arrival}`, body: parts.join("; ") + "." });
  });
  return out;
}

import { pyFixed } from "./text";
function pyFixed0(x: number) { return pyFixed(x, 0); }

export class Copilot {
  index: Index;
  cards: Map<string, any>;
  log: any[] = [];
  constructor(public data: EngineData) {
    this.index = new Index(data.index, data.situation_terms);
    this.cards = new Map(data.index.passages.map((p) => [p.pid, p]));
  }

  rank(query: string, minute: number, admittedMin: number | null, sits: string[], mask?: number[]) {
    const F = this.index.features(query, minute, admittedMin, sits);
    const s = score(this.data.ranker, F, mask);
    return argsortDesc(s).slice(0, 8).map((i) => [this.index.passages[i].pid, s[i]] as [string, number]);
  }

  run(rec: AttRecord, now: number, question = "", ablate: any = {}) {
    const trace: any[] = [];
    const t0 = () => performance.now();
    let t = t0();
    const mark = (name: string) => { const n = t0(); trace.push({ node: name, ms: Math.round((n - t) * 100) / 100 }); t = n; };
    const P = this.data.protocol;
    const g = check(question);
    mark("guard");
    const snap = snapshot(rec, now);
    const phase = phaseFromMinute(now, snap.derived.admitted_min);
    const sitsRec = recordSituations(snap, P);
    mark("situate");
    let risk: any = null;
    if (this.data.model && !ablate.no_model) {
      const f = snapshotFeatures(snap);
      if (f) risk = { ...predict(this.data.model, f), features: f };
    }
    mark("assess_risk");
    const actions = actionsFor(snap, P, risk);
    const evidence = recordEvidence(snap, P, risk);
    const patientPassages = [...planPassages(snap.plan), ...historyPassages(snap.history, snap.patient.patient_id)];
    for (const p of patientPassages) evidence[p.pid] = `${p.title}. ${p.body}`;
    mark("plan_actions");
    const adm = snap.derived.admitted_min;
    const sits = ablate.no_record_situations ? [] : sitsRec;
    const sentences: any[] = [];
    for (const a of actions) {
      const ranked = this.rank(a.query, now, adm, sits, ablate.mask);
      a.card = ranked[0][0];
      a.card_score = Math.round(ranked[0][1] * 1000) / 1000;
      const c = this.cards.get(a.card)!;
      evidence[a.card] = `${c.title}. ${c.body}`;
      let cites = [...a.evidence, ...a.plan_cite, a.card];
      if (ablate.no_plan_first && a.plan_cite.length) cites = [...a.evidence, a.card];
      sentences.push({ text: a.text, cites, kind: "action", code: a.code, section: "actions" });
    }
    mark("ground_actions");
    // Answer path.
    const answer: any[] = [];
    let retrieved: any[] = [];
    const q = g.redacted.trim();
    const flags = g.flags;
    const plan = snap.plan;
    const system = (text: string) => answer.push({ text, cites: [], kind: "system", section: "answer" });
    const citeCard = (pid: string, sentence?: string) => {
      const p = this.cards.get(pid)!;
      evidence[pid] = `${p.title}. ${p.body}`;
      answer.push({ text: sentence ?? p.body, cites: [pid], kind: "guidance", section: "answer" });
    };
    answerBlock: if (q) {
      if (flags.includes("injection")) { system("This request asks the system to set aside its instructions or the patient's plan, so it has not been acted on. The actions above still apply."); break answerBlock; }
      if (flags.includes("off_topic")) { system("This question is outside what Crescent Vigil covers: emergency and ward care of adults with sickle cell disease."); break answerBlock; }
      if (flags.includes("crisis")) citeCard("G063");
      if (flags.includes("paediatric_scope")) citeCard("G059");
      if (flags.includes("pregnancy_scope")) citeCard("G060");
      if (flags.includes("dose_request")) {
        citeCard("G062");
        if (plan) answer.push({ text: `The signed plan names ${plan.first_line_agent} by the ${plan.route} route; ${plan.dose_text.toLowerCase()}.`,
          cites: [`${plan.plan_id}.A`], kind: "plan", section: "answer" });
        break answerBlock;
      }
      if (flags.includes("pethidine")) citeCard("G007");
      const qt = new Set(tokens(q));
      const ranked = this.rank(q, now, adm, sits, ablate.mask);
      retrieved = ranked.slice(0, 5).map(([pid, s]) => ({ pid, score: Math.round(s * 1000) / 1000, title: this.cards.get(pid).title }));
      if (plan && !ablate.no_plan_first && [...qt].some((w) => ANALGESIA_WORDS.has(w))) {
        answer.push({ text: `The signed plan names ${plan.first_line_agent} by the ${plan.route} route as first line; the dose is as written in the signed individual plan.`,
          cites: [`${plan.plan_id}.A`], kind: "plan", section: "answer" });
        if (plan.avoid.length) answer.push({ text: "The plan says to avoid " + plan.avoid.join(", ") + ".", cites: [`${plan.plan_id}.B`], kind: "plan", section: "answer" });
      }
      if ([...qt].some((w) => HISTORY_WORDS.has(w)) && snap.history.attendances) {
        const hp = patientPassages.filter((p) => p.kind === "history");
        if (hp.length) answer.push({ text: hp[0].body, cites: [hp[0].pid], kind: "history", section: "answer" });
      }
      const used = new Set(answer.flatMap((s) => s.cites));
      const top = ranked[0][1];
      for (const [pid, s] of ranked.slice(0, 3)) {
        if (used.has(pid) || s < top - 2.0 || answer.filter((o) => o.kind === "guidance").length >= 2) continue;
        citeCard(pid, bestSentence(this.cards.get(pid).body, qt));
      }
    }
    mark("answer_question");
    const forbidden = new Set(["pethidine", ...(plan ? plan.avoid.filter((x: string) => x !== "NSAIDs") : [])]);
    const all = [...sentences, ...answer];
    let [kept, dropped] = ablate.no_verifier ? [all.map((s) => ({ ...s, verified: null })), []] : verify(all, evidence, forbidden, plan ? plan.first_line_agent : null);
    const codesKept = new Set(kept.map((s: any) => s.code));
    for (const d of dropped) {
      if (d.code && !codesKept.has(d.code)) kept.push({ text: "One step could not be verified against its sources and is withheld; check it with the haematology team.",
        cites: [], kind: "system", section: d.section, code: d.code, withheld: true });
    }
    mark("verify");
    const record = { ts: new Date().toISOString(), attendance_id: rec.id, now_min: now, question_redacted: g.redacted, redactions: g.redactions,
      flags, actions: actions.map((a) => a.code), overdue: actions.filter((a) => a.overdue).map((a) => a.code),
      sentences: kept.length, dropped: dropped.length, risk_24h: risk ? Math.round(risk.risk_24h * 10000) / 10000 : null };
    this.log.unshift(record);
    mark("audit");
    const cited = [...new Set(kept.flatMap((s: any) => s.cites))].sort();
    const sources = cited.map((c) => {
      if (this.cards.has(c)) {
        const p = this.cards.get(c);
        return { id: c, kind: "guidance", title: p.title, text: p.body,
          source: p.source.startsWith("S") ? p.source.split(",").map((x: string) => this.data.sources[x.trim()] || x.trim()).join("; ") : p.source };
      }
      if (c.startsWith("R.") || c.startsWith("M.")) return { id: c, kind: c.startsWith("R.") ? "record" : "model", title: c, text: evidence[c] };
      const pp = patientPassages.find((p) => p.pid === c);
      return pp ? { id: c, kind: pp.kind, title: pp.title, text: pp.body } : { id: c, kind: "unknown", title: c, text: "" };
    });
    const riskOut = risk ? { risk_24h: risk.risk_24h, alert: risk.alert, threshold: risk.threshold, drivers: risk.drivers } : null;
    return { attendance_id: rec.id, now_min: now, phase, snap, guard: g, risk: riskOut, actions, sentences: kept, dropped, sources,
      retrieved, record_situations: sitsRec, trace, record };
  }
}
