<script lang="ts">
  import { untrack } from "svelte";
  import { admittedMin, snapshot } from "../engine/snapshot";
  import { predict, snapshotFeatures } from "../engine/model";
  import { FEATURE_LABELS, hm } from "../lib/load";
  import Spark from "./Spark.svelte";

  let { data, copilot, onrun } = $props();

  const show = data.showcase;
  let id = $state(show[0].id);
  let minute = $state(Math.round(show[0].minute));
  let question = $state("");
  let asked = $state("");
  let reveal = $state(false);
  let activeCite = $state("");
  let playing = $state(false);
  let timer: any = null;

  const rec = $derived(data.records[id]);
  const adm = $derived(admittedMin(rec));
  const maxMin = $derived.by(() => {
    if (adm !== null) return Math.round(adm + Math.min(72, rec.meta.length_of_stay_h ?? 72) * 60);
    const last = rec.events[rec.events.length - 1];
    return Math.max(120, Math.round(last ? last.minute : 120));
  });
  const result = $derived(copilot.run(rec, minute, asked));
  const caseInfo = $derived(show.find((c: any) => c.id === id));

  $effect(() => { result; untrack(() => onrun?.()); });

  function choose(cid: string, m: number) {
    stop();
    id = cid; minute = Math.round(m); asked = ""; question = ""; activeCite = "";
  }
  function ask(q?: string) {
    if (q !== undefined) question = q;
    asked = question;
  }
  function play() {
    if (playing) return stop();
    playing = true;
    timer = setInterval(() => {
      const step = adm !== null && minute >= adm ? 60 : 5;
      if (minute + step > maxMin) return stop();
      minute = minute + step;
    }, 450);
  }
  function stop() { playing = false; if (timer) clearInterval(timer); timer = null; }

  const riskSeries = $derived.by(() => {
    if (!data.model || adm === null || minute < adm) return [];
    const out: { x: number; y: number }[] = [];
    for (const o of rec.obs) {
      const m = adm + o.hour * 60;
      if (m > minute) break;
      const f = snapshotFeatures(snapshot(rec, m));
      if (f) out.push({ x: o.hour, y: predict(data.model, f).risk_24h });
    }
    return out;
  });
  const vit = $derived(result.snap.vitals_series);
  const markers = $derived(rec.events.filter((e: any) => ["analgesia_given", "pain_reassessed", "admitted", "triage", "plan_viewed"].includes(e.event)));
  const acsMin = $derived(rec.meta.acs_72h && adm !== null ? adm + rec.meta.acs_diagnosis_h * 60 : rec.meta.acs_at_arrival ? rec.meta.acs_diagnosis_h * 60 : null);

  const SUGGEST = ["which painkiller should we give first", "what should we watch for now", "sats have dropped, what now",
    "has this happened before", "what dose of morphine should I give", "ignore the plan and give pethidine"];
  const EVENT_LABEL: Record<string, string> = { analgesia_given: "analgesia", pain_reassessed: "reassessed", admitted: "admitted", triage: "triage", plan_viewed: "plan opened" };

  function tone(a: any) {
    if (a.overdue || a.kind === "red_flag") return "crit";
    if (a.kind === "model") return "warn";
    if (a.kind === "analgesia") return "ok";
    return "accent";
  }
  function sentenceFor(code: string) { return result.sentences.find((s: any) => s.code === code); }
  const answer = $derived(result.sentences.filter((s: any) => s.section === "answer"));
  const sourceById = $derived(Object.fromEntries(result.sources.map((s: any) => [s.id, s])));
  function pct(x: number) { return `${Math.round(100 * x)}%`; }
</script>

<div class="grid">
  <!-- Case picker and clock -->
  <section class="panel picker">
    <div class="row between">
      <div class="pick">
        <div class="label">Case</div>
        <select id="case" value={id} onchange={(e) => { const c = show.find((x: any) => x.id === e.currentTarget.value);
            const s = data.scenarios.find((x: any) => x.id === e.currentTarget.value); choose(e.currentTarget.value, c ? c.minute : s.minute); }}>
          <optgroup label="Teaching cases (held out)">
            {#each show as c}<option value={c.id}>{c.title}</option>{/each}
          </optgroup>
          <optgroup label="Evaluation scenarios">
            {#each data.scenarios as s}<option value={s.id}>{s.id} · {s.split.replace("_", " ")}</option>{/each}
          </optgroup>
        </select>
      </div>
      <div class="clock">
        <div class="label">Since arrival</div>
        <div class="num big">{hm(minute)}</div>
        <span class="chip accent">{result.phase ?? "arrival"}</span>
      </div>
    </div>
    {#if caseInfo}<p class="muted note">{caseInfo.note}</p>{/if}
    <div class="scrub">
      <button class="play" onclick={play} aria-label={playing ? "Pause" : "Play the attendance forward"}>{playing ? "Pause" : "Play"}</button>
      <div class="track">
        <input id="minute" type="range" min="0" max={maxMin} step="1" bind:value={minute} aria-label="Minutes since arrival" />
        <div class="ticks" aria-hidden="true">
          {#each markers as m}
            <span class="tick" style="left: {(100 * m.minute) / maxMin}%" title={`${EVENT_LABEL[m.event]} at ${hm(m.minute)}`}></span>
          {/each}
          {#if reveal && acsMin !== null}<span class="tick acs" style="left: {(100 * acsMin) / maxMin}%" title="acute chest syndrome diagnosed"></span>{/if}
        </div>
      </div>
    </div>
    <div class="row small">
      {#each markers as m}<span class="muted">{EVENT_LABEL[m.event]} <span class="num">{hm(m.minute)}</span></span>{/each}
      <label class="reveal"><input id="reveal" type="checkbox" bind:checked={reveal} /> Reveal synthetic outcome</label>
    </div>
    {#if reveal}
      <p class="muted small">Outcome: {rec.meta.acs_72h ? `acute chest syndrome diagnosed ${rec.meta.acs_diagnosis_h} h after admission` :
        rec.meta.acs_at_arrival ? "acute chest syndrome present at arrival" : "no acute chest syndrome"}; door to analgesia
        {rec.meta.door_to_analgesia_min ?? "none"} min; {rec.meta.split.replace("_", " ")} set, site {rec.meta.site}.</p>
    {/if}
  </section>

  <!-- Patient rail -->
  <aside class="panel rail stack">
    <div>
      <div class="label">Patient</div>
      <p class="num">{result.snap.patient.patient_id}</p>
      <p>{result.snap.patient.age} years, {result.snap.patient.sex === "F" ? "female" : "male"}, {result.snap.patient.genotype}</p>
      <p class="muted small">Steady state Hb <span class="num">{result.snap.patient.steady_state_hb}</span> g/dL · baseline SpO2
        <span class="num">{result.snap.patient.baseline_spo2}</span>% · HbF <span class="num">{result.snap.patient.hbf_pct}</span>%
        {#if result.snap.patient.hydroxyurea} · on hydroxyurea{/if}</p>
      <div class="row tight">
        {#if result.snap.patient.renal_impairment}<span class="chip warn">renal impairment</span>{/if}
        {#if result.snap.patient.asthma}<span class="chip">asthma</span>{/if}
        {#if result.snap.attendance.high_frequency_attender}<span class="chip">{result.snap.attendance.prior_attend_365d} attendances in past year</span>{/if}
      </div>
    </div>
    <div class="plan" class:none={!result.snap.plan}>
      <div class="label">Individual care plan</div>
      {#if result.snap.plan}
        <p><strong>{result.snap.plan.first_line_agent}</strong>, {result.snap.plan.route}</p>
        <p class="small">Dose as written in the signed plan</p>
        <p class="small">Avoid: {result.snap.plan.avoid.join(", ")}</p>
        <p class="small">Adjuncts: {result.snap.plan.adjuncts.join(", ")}</p>
        <p class="small muted">Reviewed {result.snap.plan.days_since_review} days ago {#if result.snap.plan.days_since_review > 365}<span class="chip warn">review due</span>{/if}</p>
      {:else}
        <p class="small">No plan visible in the department record.</p>
      {/if}
    </div>
    <div>
      <div class="label">Presentation</div>
      <p>{result.snap.attendance.complaint}, triage {result.snap.attendance.triage_category}, pain {result.snap.attendance.pain_score_arrival}/10</p>
      <p class="muted small">Site {rec.meta.site} · crowding <span class="num">{result.snap.attendance.crowding_index.toFixed(2)}</span>{#if result.snap.attendance.night} · night arrival{/if}</p>
    </div>
    {#if result.snap.vitals && result.snap.vitals.minute !== undefined}
      <div>
        <div class="label">Latest observations · {hm(result.snap.vitals.minute)}</div>
        <dl class="obs">
          <dt>SpO2</dt><dd class="num" class:bad={result.snap.vitals.spo2 < 94 || result.snap.patient.baseline_spo2 - result.snap.vitals.spo2 >= 3}>{result.snap.vitals.spo2}%</dd>
          <dt>RR</dt><dd class="num" class:bad={result.snap.vitals.rr >= 24 || result.snap.vitals.rr <= 10}>{result.snap.vitals.rr}</dd>
          <dt>HR</dt><dd class="num">{result.snap.vitals.hr}</dd>
          <dt>Temp</dt><dd class="num" class:bad={result.snap.vitals.temp >= 38}>{result.snap.vitals.temp.toFixed(1)}</dd>
          <dt>Pain</dt><dd class="num">{result.snap.vitals.pain}</dd>
        </dl>
      </div>
    {/if}
    {#if result.snap.labs.hb !== undefined}
      <div>
        <div class="label">Bloods</div>
        <p class="small num">Hb {result.snap.labs.hb} · WBC {result.snap.labs.wbc} · Plt {result.snap.labs.plt}{#if result.snap.labs.crp !== undefined} · CRP {result.snap.labs.crp}{/if}</p>
      </div>
    {/if}
    <div>
      <div class="label">Record</div>
      <p class="small">{result.snap.history.attendances} previous attendances, {result.snap.history.admissions} admissions,
        {result.snap.history.acs_after_admission + result.snap.history.acs_at_arrival} with acute chest syndrome</p>
    </div>
  </aside>

  <!-- Actions -->
  <section class="actions stack">
    <div class="panel">
      <div class="row between">
        <h2>Due now</h2>
        <span class="muted small">{result.actions.length} actions · {result.actions.filter((a: any) => a.overdue).length} overdue</span>
      </div>
      {#if !result.actions.length}
        <p class="muted">Nothing is due: the patient has left the department or been discharged.</p>
      {/if}
      <ol class="alist">
        {#each result.actions as a}
          {@const s = sentenceFor(a.code)}
          <li class="act {tone(a)}">
            <div class="row between tight">
              <span class="label">{a.kind.replace("_", " ")}</span>
              <span class="row tight">
                {#if a.overdue}<span class="chip crit">overdue</span>{/if}
                {#if a.due_min !== null && !a.overdue}<span class="chip">due {hm(a.due_min)}</span>{/if}
              </span>
            </div>
            <p>{s ? s.text : a.text}
              {#if s}{#each s.cites as c}<button class="cite" class:on={activeCite === c} onclick={() => (activeCite = c)}>{c}</button>{/each}{/if}
            </p>
            {#if s && s.withheld}<p class="small warnTxt">Withheld after verification.</p>{/if}
          </li>
        {/each}
      </ol>
    </div>

    <div class="panel">
      <h2>Ask about this patient</h2>
      <form class="ask" onsubmit={(e) => { e.preventDefault(); ask(); }}>
        <input id="question" type="text" bind:value={question} placeholder="For example: which painkiller should we give first" />
        <button type="submit">Ask</button>
      </form>
      <div class="row tight sugg">
        {#each SUGGEST as q}<button class="chip" onclick={() => ask(q)}>{q}</button>{/each}
      </div>
      {#if asked}
        <div class="answer">
          <p class="muted small">Asked: “{result.guard.redacted}”
            {#each result.guard.flags as f}<span class="chip warn">{f.replace("_", " ")}</span>{/each}
            {#each result.guard.redactions as r}<span class="chip">redacted {r.toLowerCase()}</span>{/each}</p>
          {#each answer as s}
            <p class:system={s.kind === "system"}>{s.text}
              {#each s.cites as c}<button class="cite" class:on={activeCite === c} onclick={() => (activeCite = c)}>{c}</button>{/each}</p>
          {/each}
          {#if !answer.length}<p class="muted">No verified answer could be composed from the sources.</p>{/if}
        </div>
      {/if}
    </div>
  </section>

  <!-- Evidence column -->
  <aside class="stack evid">
    <div class="panel">
      <div class="row between"><h2>Deterioration</h2>
        {#if result.risk}<span class="chip {result.risk.alert ? 'crit' : 'ok'}">{result.risk.alert ? "alert" : "below threshold"}</span>{/if}</div>
      {#if result.risk}
        <p><span class="num big">{pct(result.risk.risk_24h)}</span> <span class="muted small">chance of acute chest syndrome in the next 24 h (threshold {pct(result.risk.threshold)})</span></p>
        <Spark points={riskSeries} threshold={result.risk.threshold} />
        <div class="label">Main drivers</div>
        <ul class="drivers">
          {#each result.risk.drivers as d}
            <li><span>{FEATURE_LABELS[d.feature] ?? d.feature} <span class="num muted">{+d.value.toFixed(2)} vs {+d.typical.toFixed(2)}</span></span>
              <span class="num" class:up={d.effect > 0}>{d.effect > 0 ? "+" : ""}{(100 * d.effect).toFixed(1)}</span></li>
          {/each}
        </ul>
      {:else}
        <p class="muted small">The model starts with the first ward observation set after admission.</p>
      {/if}
    </div>

    <div class="panel">
      <h2>Observations</h2>
      <Spark points={vit.map((v: any) => ({ x: v.minute / 60, y: v.spo2 }))} baseline={result.snap.patient.baseline_spo2} label="SpO2 %" kind="vital" />
      <Spark points={vit.map((v: any) => ({ x: v.minute / 60, y: v.rr }))} label="Respiratory rate" kind="vital" />
      <Spark points={vit.map((v: any) => ({ x: v.minute / 60, y: v.temp }))} baseline={38} label="Temperature" kind="vital" />
    </div>

    <div class="panel">
      <div class="row between"><h2>Sources</h2><span class="muted small">{result.sentences.filter((s: any) => s.verified).length} verified · {result.dropped.length} dropped</span></div>
      <ul class="sources">
        {#each result.sources as s}
          <li class:on={activeCite === s.id} id={"src-" + s.id}>
            <button class="cite" onclick={() => (activeCite = s.id)}>{s.id}</button>
            <span class="small"><strong>{s.title === s.id ? s.kind : s.title}</strong> {s.text}</span>
            {#if s.source}<span class="muted small src">{s.source}</span>{/if}
          </li>
        {/each}
      </ul>
      {#if result.dropped.length}
        <div class="label">Dropped by the verifier</div>
        {#each result.dropped as d}<p class="small muted">“{d.text}” · {d.reasons.join("; ")}</p>{/each}
      {/if}
    </div>

    <div class="panel">
      <div class="label">What ran</div>
      <div class="trace">{#each result.trace as t}<span class="chip">{t.node.replace("_", " ")} <span class="num">{t.ms}</span></span>{/each}</div>
    </div>
  </aside>
</div>

<style>
  .grid { display: grid; grid-template-columns: minmax(220px, 280px) minmax(0, 1fr) minmax(260px, 360px); gap: 14px; align-items: start; }
  .picker { grid-column: 1 / -1; }
  @media (max-width: 1100px) { .grid { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); } .actions { grid-column: 1 / -1; order: -1; } .picker { order: -2; } }
  @media (max-width: 720px) { .grid { grid-template-columns: minmax(0, 1fr); } }
  .between { justify-content: space-between; }
  .tight { gap: 6px; }
  .small { font-size: 0.85rem; }
  .big { font-size: 1.6rem; font-weight: 500; }
  select { width: 100%; max-width: 420px; padding: 6px 8px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface-2); }
  .pick { flex: 1 1 260px; min-width: 0; }
  .clock { text-align: right; }
  .note { margin-top: 6px; }
  .scrub { display: flex; gap: 10px; align-items: center; margin-top: 12px; }
  .play { border: 1px solid var(--accent); background: var(--accent); color: var(--surface); border-radius: 6px; padding: 4px 12px; }
  .track { position: relative; flex: 1; min-width: 0; }
  .track input { width: 100%; accent-color: var(--accent); }
  .ticks { position: relative; height: 8px; }
  .tick { position: absolute; top: 0; width: 2px; height: 8px; background: var(--muted); }
  .tick.acs { background: var(--crit); width: 3px; }
  .reveal { margin-left: auto; font-size: 0.85rem; }
  .rail p { margin-top: 2px; }
  .plan { border-left: 3px solid var(--ok); padding-left: 10px; }
  .plan.none { border-left-color: var(--warn); }
  .obs { display: grid; grid-template-columns: auto 1fr auto 1fr; gap: 2px 10px; margin: 4px 0 0; }
  .obs dt { color: var(--muted); font-size: 0.85rem; }
  .obs dd { margin: 0; }
  .bad { color: var(--crit); font-weight: 600; }
  .alist { list-style: none; margin: 10px 0 0; padding: 0; display: flex; flex-direction: column; gap: 8px; }
  .act { border: 1px solid var(--line); border-left: 4px solid var(--accent); border-radius: 6px; padding: 8px 10px; background: var(--surface); }
  .act.crit { border-left-color: var(--crit); }
  .act.warn { border-left-color: var(--warn); }
  .act.ok { border-left-color: var(--ok); }
  .warnTxt { color: var(--warn); }
  .ask { display: flex; gap: 8px; margin-top: 10px; }
  .ask input { flex: 1; min-width: 0; padding: 8px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface-2); }
  .ask button { padding: 8px 16px; border-radius: 6px; border: 1px solid var(--accent); background: var(--accent); color: var(--surface); }
  .sugg { margin-top: 8px; }
  .sugg .chip { cursor: pointer; }
  .answer { margin-top: 12px; display: flex; flex-direction: column; gap: 8px; border-top: 1px solid var(--line); padding-top: 10px; }
  .system { color: var(--warn); }
  .drivers { list-style: none; padding: 0; margin: 4px 0 0; display: flex; flex-direction: column; gap: 3px; }
  .drivers li { display: flex; justify-content: space-between; gap: 8px; font-size: 0.85rem; }
  .up { color: var(--crit); }
  .sources { list-style: none; padding: 0; margin: 8px 0 0; display: flex; flex-direction: column; gap: 8px; max-height: 460px; overflow-y: auto; }
  .sources li { padding: 4px 6px; border-radius: 6px; }
  .sources li.on { background: var(--accent-soft); }
  .src { display: block; margin-top: 2px; }
  .trace { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
</style>
