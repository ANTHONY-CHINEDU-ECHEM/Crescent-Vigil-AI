<script lang="ts">
  import Chart from "./Chart.svelte";
  import { FEATURE_LABELS } from "../lib/load";
  let { data } = $props();
  const cv = data.reports.curves;
  const tr = data.reports.training;
  const blind = data.reports.evaluation?.blind?.model;
  const ph = data.reports.post_hoc;
  const NAMES: Record<string, string> = { hgb: "Gradient boosted model", logistic: "Logistic regression", rule: "Saturation rule" };
  const pct = (x: number) => `${(100 * x).toFixed(1)}%`;
  const imp = tr ? tr.importance.slice(0, 12) : [];
  const impMax = imp.length ? Math.max(...imp.map((d: any) => d.drop_in_auprc)) : 1;
  const leadMax = cv ? Math.max(...cv.lead_hist.map((d: any) => d.n)) : 1;
</script>

<div class="stack">
  <div class="panel">
    <h2>Acute chest syndrome in the next 24 hours</h2>
    <p class="muted small">A gradient boosted discrete time hazard model scores every four hourly observation set after admission. It was trained on
      development sites only and scored once on two unseen hospitals and on 2025 attendances.</p>
    {#if blind}
      <div class="scroll-x"><table>
        <thead><tr><th>Blind set, every observation set</th><th class="n">AUROC</th><th class="n">AUPRC</th><th class="n">Brier</th></tr></thead>
        <tbody>
          {#each [["rolling_hgb", "Gradient boosted model"], ["rolling_logistic", "Logistic regression"], ["rolling_rule", "Saturation rule"]] as [k, l]}
            <tr><td>{l}</td><td class="n">{blind.all[k].auroc.toFixed(3)}</td><td class="n">{blind.all[k].auprc.toFixed(3)}</td><td class="n">{blind.all[k].brier ?? "n/a"}</td></tr>
          {/each}
          <tr><td>Admission model, 72 hours</td><td class="n">{blind.admission_hgb.auroc.toFixed(3)}</td><td class="n">{blind.admission_hgb.auprc.toFixed(3)}</td><td class="n">{blind.admission_hgb.brier}</td></tr>
        </tbody>
      </table></div>
    {:else}
      <p class="muted">The blind evaluation has not been run yet.</p>
    {/if}
  </div>

  {#if cv && blind}
    <div class="two">
      <div class="panel"><h3>Receiver operating characteristic</h3>
        <Chart series={Object.entries(cv.roc).map(([k, v]) => ({ name: NAMES[k], points: v }))} xLabel="false positive rate" yLabel="true positive rate" xMax={1} yMax={1} diagonal pctX pctY /></div>
      <div class="panel"><h3>Precision and recall</h3>
        <Chart series={Object.entries(cv.pr).map(([k, v]) => ({ name: NAMES[k], points: v }))} xLabel="recall" yLabel="precision" xMax={1} yMax={1} pctX pctY /></div>
      <div class="panel"><h3>Calibration</h3>
        <Chart series={[{ name: "Gradient boosted model", points: cv.calibration.map((b: any) => [b.predicted, b.observed]), dots: true }]}
          xLabel="predicted risk" yLabel="observed rate" xMax={Math.max(...cv.calibration.map((b: any) => b.predicted)) * 1.05}
          yMax={Math.max(...cv.calibration.map((b: any) => Math.max(b.observed, b.predicted))) * 1.05} diagonal pctX pctY /></div>
      <div class="panel"><h3>Alert threshold trade off</h3>
        <Chart series={[{ name: "admissions with acute chest syndrome alerted", points: cv.tradeoff.map((t: any) => [t.threshold, t.sensitivity]) },
                        { name: "admissions without it alerted", points: cv.tradeoff.map((t: any) => [t.threshold, t.false_alert]) }]}
          xLabel="alert threshold" yLabel="share of admissions" xMax={0.6} yMax={1} pctX pctY /></div>
    </div>

    <div class="two">
      <div class="panel">
        <h3>Alerts at the threshold fixed on development data</h3>
        <div class="scroll-x"><table>
          <thead><tr><th>Policy</th><th class="n">Caught</th><th class="n">Median lead</th><th class="n">False alert admissions</th><th class="n">Alerts per 100 days</th></tr></thead>
          <tbody>
            {#each [["hgb_at_frozen_threshold", `Model ≥ ${pct(blind.alerts.hgb_at_frozen_threshold.threshold)}`], ["logistic_at_dev_threshold", "Logistic regression"], ["rule", "Saturation rule"]] as [k, l]}
              <tr><td>{l}</td><td class="n">{pct(blind.alerts[k].episode_sensitivity)}</td><td class="n">{blind.alerts[k].median_lead_time_h} h</td>
                <td class="n">{pct(blind.alerts[k].false_alert_admissions)}</td><td class="n">{blind.alerts[k].alerts_per_100_patient_days}</td></tr>
            {/each}
          </tbody>
        </table></div>
      </div>
      <div class="panel">
        <h3>Hours of warning before the diagnosis</h3>
        <svg viewBox="0 0 520 170" width="100%" role="img" aria-label="Histogram of lead time">
          {#each cv.lead_hist as b, i}
            <rect x={40 + i * 25} y={140 - (120 * b.n) / leadMax} width="21" height={(120 * b.n) / leadMax} fill="var(--chart-1)" />
            {#if i % 2 === 0}<text x={50 + i * 25} y="156" text-anchor="middle">{b.h}</text>{/if}
          {/each}
          <line x1="38" x2="510" y1="140" y2="140" stroke="var(--line)" />
          <text x="275" y="168" text-anchor="middle">hours between first alert and diagnosis</text>
        </svg>
      </div>
    </div>

    <div class="two">
      <div class="panel">
        <h3>Where it fails</h3>
        {#if ph}
          <ul class="plain">
            <li>{blind.failures.missed_episodes.toLocaleString()} of {blind.alerts.hgb_at_frozen_threshold.episodes_with_acs.toLocaleString()} episodes were never alerted.
              They were not diagnosed earlier than caught episodes (median {ph.missed.median_diagnosis_h} h against {ph.caught.median_diagnosis_h} h). They were lower risk
              patients: {pct(ph.missed.severe_genotype)} had a severe genotype against {pct(ph.caught.severe_genotype)}, with fewer previous episodes
              ({ph.missed.mean_previous_acs} against {ph.caught.mean_previous_acs}) and a median risk at the first ward observation of {pct(ph.missed.median_risk_at_first_obs)}
              against {pct(ph.caught.median_risk_at_first_obs)}.</li>
            <li>The {blind.failures.false_alert_admissions.toLocaleString()} admissions alerted without acute chest syndrome were the mirror image: {pct(ph.false_alerts.severe_genotype)}
              severe genotype against {pct(ph.quiet_without_acs.severe_genotype)}, higher peak opioid load ({ph.false_alerts.median_peak_opioid_load} against
              {ph.quiet_without_acs.median_peak_opioid_load}) and more previous episodes. Fever and transient desaturation added little.</li>
            <li>So the model leans on baseline risk more than on the trend in the observations, and the alert burden at 80% of episodes caught is high. This is
              the main thing to improve. The analysis reads the stored blind predictions and does not score the blind set again.</li>
          </ul>
        {/if}
      </div>
      <div class="panel">
        <h3>By group</h3>
        <div class="scroll-x"><table>
          <thead><tr><th>Group</th><th class="n">AUROC</th><th class="n">AUPRC</th><th class="n">Caught</th></tr></thead>
          <tbody>{#each blind.subgroups as s}<tr><td>{s.group}</td><td class="n">{s.auroc.toFixed(3)}</td><td class="n">{s.auprc.toFixed(3)}</td><td class="n">{pct(s.alert_sensitivity)}</td></tr>{/each}</tbody>
        </table></div>
      </div>
    </div>
  {/if}

  {#if tr}
    <div class="panel">
      <h3>What the model relies on</h3>
      <p class="muted small">Permutation importance on a patient grouped hold out fold of development data: the fall in AUPRC when one feature is shuffled.</p>
      <div class="bars">
        {#each imp as d}
          <span class="name">{FEATURE_LABELS[d.feature] ?? d.feature}</span>
          <span class="bar"><i style="width: {Math.max(1, (100 * d.drop_in_auprc) / impMax)}%"></i></span>
          <span class="num">{d.drop_in_auprc.toFixed(3)}</span>
        {/each}
      </div>
      <p class="muted small">Chosen settings by grouped cross validation: learning rate {tr.chosen.learning_rate}, {tr.chosen.max_leaf_nodes} leaves, {tr.chosen.max_iter} trees, alert threshold {pct(tr.alert_threshold)} for 80% of development episodes alerted.</p>
    </div>
  {/if}
</div>

<style>
  .small { font-size: 0.85rem; }
  .two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
  @media (max-width: 860px) { .two { grid-template-columns: minmax(0, 1fr); } }
  h3 { margin-bottom: 6px; }
  .plain { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 6px; }
  .bars { display: grid; grid-template-columns: minmax(120px, 220px) 1fr auto; gap: 4px 10px; align-items: center; margin-top: 8px; font-size: 0.85rem; }
  .bar { background: var(--surface-2); height: 10px; border-radius: 3px; overflow: hidden; }
  .bar i { display: block; height: 100%; background: var(--chart-1); }
  .name { min-width: 0; }
</style>
