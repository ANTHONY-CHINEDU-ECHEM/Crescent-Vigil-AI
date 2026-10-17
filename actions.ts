// Clock and red flag engine: a port of crescent_vigil/agent/engine.py.
import { pyFixed as fmt, pyRound } from "./text";
import type { Snapshot } from "./snapshot";

export interface Protocol {
  analgesia_target_min: number; analgesia_target_ash_min: number; reassess_interval_min: number; reassess_stable_interval_min: number;
  spo2_flag: number; spo2_drop_flag: number; temp_flag: number; rr_flag: number; rr_low_flag: number; hb_drop_flag: number;
}

export interface Action {
  code: string; kind: string; text: string; query: string; evidence: string[]; due_min: number | null;
  overdue: boolean; severity: number; plan_cite: string[]; card?: string; card_score?: number;
}

const PAIN_LIKE = new Set(["pain", "chest", "abdominal", "priapism"]);

function A(code: string, kind: string, text: string, query: string, evidence: string[] = [], due: number | null = null,
  overdue = false, severity = 1, plan_cite: string[] = []): Action {
  return { code, kind, text, query, evidence, due_min: due, overdue, severity, plan_cite };
}

export function recordEvidence(snap: Snapshot, P: Protocol, risk?: any): Record<string, string> {
  const a = snap.attendance, p = snap.patient, d = snap.derived, v = snap.vitals, labs = snap.labs;
  const now = snap.now_min;
  const ev: Record<string, string> = {};
  ev["R.arrival"] = `Arrived ${fmt(now)} minutes ago with ${a.complaint}; triage category ${a.triage_category}; ` +
    `arrival pain score ${fmt(a.pain_score_arrival)}; genotype ${p.genotype}; age ${p.age}.`;
  if (d.analgesia_given_min !== null) {
    const interval = snap.plan ? snap.plan.reassess_min : P.reassess_interval_min;
    ev["R.analgesia"] = `First analgesia ${d.analgesia_agent} ${d.analgesia_route} given at minute ${fmt(d.analgesia_given_min)}, ` +
      `${fmt(now - d.analgesia_given_min)} minutes ago; reassessment due at minute ` +
      `${fmt(d.analgesia_given_min + interval)}, ${interval} minutes after the dose.` +
      (d.reassessed_min !== null ? ` Pain reassessed at minute ${fmt(d.reassessed_min)}.` : " No pain reassessment recorded since.");
  } else {
    ev["R.analgesia"] = `No analgesia recorded in the ${fmt(now)} minutes since arrival.`;
  }
  if (v && Object.keys(v).length) {
    ev["R.vitals"] = `Latest observations at minute ${fmt(v.minute)}: oxygen saturation ${fmt(v.spo2)} percent against a baseline of ` +
      `${fmt(p.baseline_spo2)}, ${fmt(p.baseline_spo2 - v.spo2)} points below baseline; respiratory rate ${fmt(v.rr)}; ` +
      `heart rate ${fmt(v.hr)}; temperature ${fmt(v.temp, 1)} degrees; pain score ${fmt(v.pain)}.`;
  }
  if (labs.hb !== undefined && labs.hb !== null) {
    ev["R.labs"] = `Haemoglobin ${fmt(labs.hb, 1)} g/dL against a steady state of ${fmt(p.steady_state_hb, 1)}, ` +
      `a fall of ${fmt(p.steady_state_hb - labs.hb, 1)} g/dL; white cells ${fmt(labs.wbc, 1)}; platelets ${fmt(labs.plt)}.`;
  }
  if (d.admitted_min !== null && now >= d.admitted_min) {
    ev["R.admission"] = `Admitted at minute ${fmt(d.admitted_min)}; ${fmt((now - d.admitted_min) / 60, 1)} hours on the ward.`;
  }
  ev["R.protocol"] = `Local protocol parameters: first analgesia target ${P.analgesia_target_min} minutes; reassessment every ` +
    `${P.reassess_interval_min} minutes until relief; fever flag ${fmt(P.temp_flag, 1)} degrees; oxygen saturation flag below ` +
    `${fmt(P.spo2_flag)} percent or ${fmt(P.spo2_drop_flag)} points below baseline; respiratory rate flags ${P.rr_flag} and ` +
    `${P.rr_low_flag}; haemoglobin flag ${fmt(P.hb_drop_flag, 1)} g/dL below steady state.`;
  const plan = snap.plan;
  ev["R.plan"] = plan
    ? `Signed individual plan ${plan.plan_id} is on the record; last reviewed ${plan.days_since_review} days before this attendance.`
    : "No individual care plan is visible in the emergency department record.";
  const flags: string[] = [];
  if (p.renal_impairment) flags.push("renal impairment");
  if (p.asthma) flags.push("asthma");
  if (flags.length) ev["R.problems"] = "Problem list includes " + flags.join(" and ") + ".";
  if (risk) {
    ev["M.acs"] = `Deterioration model estimate ${pyRound(100 * risk.risk_24h)} percent for acute chest syndrome within 24 hours; ` +
      `alert threshold ${pyRound(100 * risk.threshold)} percent.`;
  }
  return ev;
}

export function actionsFor(snap: Snapshot, P: Protocol, risk?: any): Action[] {
  const now = snap.now_min;
  const a = snap.attendance, pt = snap.patient, d = snap.derived, v = snap.vitals, labs = snap.labs, plan = snap.plan;
  const out: Action[] = [];
  if (d.left_department || d.discharged) return out;
  const adm = d.admitted_min;
  const onWard = adm !== null && now >= adm;
  const given = d.analgesia_given_min;

  if (PAIN_LIKE.has(a.complaint) && given === null) {
    const late = now > P.analgesia_target_min;
    out.push(A("GIVE_FIRST_ANALGESIA", "clock",
      late ? `First analgesia is overdue: ${fmt(now)} minutes since arrival against a target of ${P.analgesia_target_min} minutes; give it now.`
        : `Give the first dose of analgesia by minute ${P.analgesia_target_min}; ${fmt(now)} minutes have passed since arrival.`,
      "first dose analgesia within 30 minutes of arrival target", ["R.arrival", "R.analgesia"], P.analgesia_target_min, late, late ? 3 : 2));
    out.push(A("ASK_HOME_ANALGESIA", "clock", "Ask what analgesia was taken at home for this episode before the first dose.",
      "analgesia already taken at home before arrival", ["R.analgesia"], null, false, 1));
    if (plan) {
      out.push(A("FOLLOW_PLAN", "analgesia",
        `Use the signed plan: ${plan.first_line_agent} by the ${plan.route} route, dose as written in the signed individual plan.`,
        "individual care plan agent route dose", ["R.plan"], null, false, 3, [`${plan.plan_id}.A`]));
    } else {
      out.push(A("USE_DEPARTMENT_PROTOCOL", "analgesia",
        "No individual plan is visible, so use the department protocol for a strong opioid in severe pain and ask haematology whether a plan exists.",
        "strong opioid severe pain bolus no plan", ["R.plan"], null, false, 3));
    }
    out.push(A("AVOID_PETHIDINE", "analgesia", "Do not use pethidine.", "pethidine avoid", [], null, false, 2, plan ? [`${plan.plan_id}.B`] : []));
    out.push(A("ADJUNCT_PARACETAMOL", "analgesia", "Offer regular paracetamol as an adjunct.", "paracetamol adjunct", [], null, false, 1,
      plan ? [`${plan.plan_id}.C`] : []));
    const blocked = pt.renal_impairment || (plan !== null && plan.avoid.includes("NSAIDs"));
    if (blocked) {
      out.push(A("NO_NSAID", "analgesia", "Do not give an NSAID adjunct: renal impairment or the plan rules it out.",
        "NSAID contraindicated renal impairment", pt.renal_impairment ? ["R.problems"] : [], null, false, 2, plan ? [`${plan.plan_id}.B`] : []));
    } else {
      out.push(A("ADJUNCT_NSAID", "analgesia", "An NSAID such as ibuprofen can be added as an adjunct; no contraindication is recorded.",
        "NSAID ibuprofen adjunct unless contraindicated", [], null, false, 1));
    }
  }

  if (given !== null && !onWard) {
    const since = now - given;
    const interval = plan ? plan.reassess_min : P.reassess_interval_min;
    if (since <= 120) {
      out.push(A("MONITOR_AFTER_OPIOID", "clock",
        "Record pain, sedation, respiratory rate and oxygen saturation every 30 minutes until pain is controlled.",
        "monitoring after opioid respiratory rate sedation every 30 minutes", ["R.analgesia"], null, false, 2));
      if (d.reassessed_min === null) {
        const due = given + interval;
        const late = now >= due;
        out.push(A("REASSESS_PAIN", "clock",
          late ? `Pain reassessment is overdue: due at minute ${fmt(due)}, ${fmt(since)} minutes after the first dose.`
            : `Reassess pain by minute ${fmt(due)}, ${interval} minutes after the first dose.`,
          "reassess pain every 30 minutes after first dose", ["R.analgesia"], due, late, late ? 3 : 2));
      }
    }
  }
  if (onWard) {
    const hrs = (now - adm) / 60;
    if (hrs <= 24) {
      out.push(A("INFORM_HAEMATOLOGY", "clock", "Tell the haematology team about this admission if not already done.",
        "inform haematology specialist team on admission", ["R.admission"], null, false, 2, plan ? [`${plan.plan_id}.D`] : []));
    }
    out.push(A("INCENTIVE_SPIROMETRY", "clock", "Encourage incentive spirometry while awake to lower the risk of acute chest syndrome.",
      "incentive spirometry prevent acute chest syndrome admitted", ["R.admission"], null, false, 1));
    out.push(A("FOUR_HOURLY_OBS", "clock", "Continue observations at least every four hours, including oxygen saturation and respiratory rate.",
      "observations four hourly stable oxygen saturation respiratory rate", ["R.admission"], null, false, 1));
  }

  if (v && Object.keys(v).length) {
    if (v.temp >= P.temp_flag) {
      out.push(A("SEPSIS_SCREEN", "red_flag",
        `Temperature ${fmt(v.temp, 1)} degrees meets the local fever flag of ${fmt(P.temp_flag, 1)}: start a sepsis screen with blood cultures and prompt antibiotics.`,
        "fever temperature sepsis screen blood culture antibiotics", ["R.vitals", "R.protocol"], null, false, 3));
    }
    const gap = pt.baseline_spo2 - v.spo2;
    if (v.spo2 < P.spo2_flag || gap >= P.spo2_drop_flag) {
      out.push(A("REVIEW_CHEST", "red_flag",
        `Oxygen saturation ${fmt(v.spo2)} percent is ${fmt(gap)} points below baseline: review the chest promptly and consider a chest X ray for acute chest syndrome.`,
        "falling oxygen saturation below baseline acute chest syndrome review", ["R.vitals", "R.protocol"], null, false, 3));
    } else if (v.rr >= P.rr_flag) {
      out.push(A("REVIEW_CHEST", "red_flag", `Respiratory rate ${fmt(v.rr)} is raised: review the chest for acute chest syndrome.`,
        "rising respiratory rate acute chest syndrome review", ["R.vitals"], null, false, 3));
    }
    if (v.rr <= P.rr_low_flag) {
      out.push(A("OPIOID_TOXICITY_REVIEW", "red_flag",
        `Respiratory rate ${fmt(v.rr)} is low: review now for opioid toxicity, hold further doses and follow the opioid safety policy.`,
        "low respiratory rate sedation opioid toxicity naloxone", ["R.vitals"], null, false, 3));
    }
  }
  if (a.complaint === "chest" && now <= 240 && !onWard) {
    out.push(A("CHEST_XRAY_AT_ARRIVAL", "red_flag", "Chest symptoms at presentation: arrange an early chest X ray and inform haematology.",
      "chest pain breathlessness cough at presentation chest X ray", ["R.arrival"], null, false, 3));
  }
  if (a.complaint === "neuro") {
    out.push(A("STROKE_PATHWAY", "red_flag", "Neurological symptoms: start the stroke pathway with urgent brain imaging and immediate haematology involvement.",
      "neurological weakness speech stroke urgent imaging exchange transfusion", ["R.arrival"], null, false, 3));
  }
  if (a.complaint === "priapism") {
    out.push(A("UROLOGY_REVIEW", "red_flag", "Priapism: ask how long it has lasted and seek urgent urology review alongside analgesia.",
      "priapism four hours urology aspiration", ["R.arrival"], null, false, 3));
  }
  if (labs.hb !== undefined && labs.hb !== null && pt.steady_state_hb - labs.hb >= P.hb_drop_flag) {
    out.push(A("ACUTE_ANAEMIA_REVIEW", "red_flag",
      `Haemoglobin has fallen ${fmt(pt.steady_state_hb - labs.hb, 1)} g/dL below steady state: check reticulocytes and the spleen and discuss with haematology.`,
      "haemoglobin fall below steady state reticulocytes sequestration", ["R.labs", "R.protocol"], null, false, 3));
  }
  if (plan && plan.days_since_review > 365) {
    out.push(A("PLAN_REVIEW_DUE", "plan", `The plan was last reviewed ${plan.days_since_review} days ago; follow it but confirm with haematology.`,
      "care plan review out of date annual", ["R.plan"], null, false, 1));
  }
  if (risk && risk.alert) {
    out.push(A("DETERIORATION_ALERT", "model",
      `The deterioration model estimates a ${pyRound(100 * risk.risk_24h)} percent chance of acute chest syndrome within 24 hours, above the ${pyRound(100 * risk.threshold)} percent alert threshold: review at the bedside.`,
      "deterioration model alert acute chest syndrome 24 hours review", ["M.acs"], null, false, 3));
  }
  const order: Record<string, number> = { red_flag: 0, model: 1, clock: 2, analgesia: 3, plan: 4 };
  return out.map((x, i) => ({ x, i })).sort((p, q) => (q.x.severity - p.x.severity) || (order[p.x.kind] - order[q.x.kind]) || (p.i - q.i)).map((p) => p.x);
}
