<script lang="ts">
  let { data } = $props();
  const ev = data.reports.evaluation;
  const b = ev?.blind;
  const d = ev?.dev;
  const pct = (x: number | null) => (x === null || x === undefined ? "n/a" : `${(100 * x).toFixed(1)}%`);
  const METHOD: Record<string, string> = { bm25f: "BM25F alone", lsa: "Latent semantic alone", learned: "Learned ranker",
    without_phase_match: "without phase", without_situation_overlap: "without situation", without_entity_hits: "without entities", without_title_overlap: "without title overlap" };
  const ABL: Record<string, string> = { without_phase_feature: "Without the phase feature", without_situation_feature: "Without the situation feature",
    without_entity_feature: "Without the entity feature", without_record_situations: "Without situations from the record", bm25f_only: "BM25F only" };
  const PERT: Record<string, string> = { insert_dose: "A dose inserted", swap_to_forbidden_agent: "An avoided agent recommended", change_number: "A number changed",
    drop_citations: "Citations removed", wrong_card: "Cited to the wrong card" };
</script>

{#if !ev}
  <div class="panel"><p class="muted">Run make evaluate to build the evaluation report.</p></div>
{:else}
  <div class="stack">
    <div class="panel">
      <h2>Protocol</h2>
      <p class="small">Scenarios, gold actions and held out questions were frozen and hashed at <span class="num">{ev.frozen.frozen_at}</span>
        before any model, index or copilot existed (combined SHA256 <span class="num">{ev.frozen.combined_sha256.slice(0, 12)}…</span>).
        The blind set is sites {ev.frozen.blind_definition.sites.join(" and ")} in full plus every 2025 attendance elsewhere:
        {ev.frozen.counts.blind_site_attendances.toLocaleString()} and {ev.frozen.counts.blind_temporal_attendances.toLocaleString()} attendances.
        {#if b}It was scored once at <span class="num">{b.scored_at}</span>.{/if}</p>
    </div>

    {#if b}
      <div class="two">
        <div class="panel">
          <h3>Copilot on {b.copilot.all.scenarios} blind scenarios</h3>
          <p class="muted small">Gold actions come from a decision table written from the same guidance cards, so perfect agreement shows the
            engine implements the table faithfully on unseen hospitals and a later year. It is not evidence of clinical validity.</p>
          <div class="scroll-x"><table><tbody>
            <tr><td>Actions, precision and recall</td><td class="n">{pct(b.copilot.all.actions.precision)} · {pct(b.copilot.all.actions.recall)}</td></tr>
            <tr><td>Red flags, precision and recall</td><td class="n">{pct(b.copilot.all.red_flags.precision)} · {pct(b.copilot.all.red_flags.recall)}</td></tr>
            <tr><td>Overdue steps, precision and recall</td><td class="n">{pct(b.copilot.all.overdue.precision)} · {pct(b.copilot.all.overdue.recall)}</td></tr>
            <tr><td>Exact action set</td><td class="n">{pct(b.copilot.all.exact_action_set)}</td></tr>
            <tr><td>Actions cited to an acceptable card</td><td class="n">{pct(b.copilot.all.citation_correct)} of {b.copilot.all.citations_scored}</td></tr>
            <tr><td>Plan agent and route correct</td><td class="n">{pct(b.copilot.all.plan_agent_route_correct)} of {b.copilot.all.plan_scenarios}</td></tr>
            <tr><td>Sentences verified</td><td class="n">{pct(b.copilot.all.verified_rate)} of {b.copilot.all.sentences}</td></tr>
            <tr><td>Avoided agents recommended</td><td class="n">{b.copilot.all.forbidden_agent_leaks}</td></tr>
            <tr><td>Doses shown</td><td class="n">{b.copilot.all.dose_leaks}</td></tr>
            <tr><td>Safety probes passed</td><td class="n">{b.probes.passed} of {b.probes.probes}</td></tr>
          </tbody></table></div>
        </div>
        <div class="panel">
          <h3>Retrieval on {b.retrieval.questions} blind questions</h3>
          <div class="scroll-x"><table>
            <thead><tr><th>Method</th><th class="n">Hit@1</th><th class="n">Recall@3</th><th class="n">MRR</th><th class="n">nDCG@10</th></tr></thead>
            <tbody>{#each Object.entries(b.retrieval.methods) as [k, m]}
              <tr class:strong={k === "learned"}><td>{METHOD[k] ?? k}</td><td class="n">{m["hit@1"].toFixed(3)}</td><td class="n">{m["recall@3"].toFixed(3)}</td><td class="n">{m.mrr.toFixed(3)}</td><td class="n">{m["ndcg@10"].toFixed(3)}</td></tr>
            {/each}</tbody>
          </table></div>
        </div>
      </div>

      <div class="two">
        <div class="panel">
          <h3>Grounding ablations, blind scenarios</h3>
          <p class="muted small">Share of actions whose retrieved card is one of the acceptable cards for that action.</p>
          <div class="scroll-x"><table>
            <thead><tr><th>Configuration</th><th class="n">Citation correct</th><th class="n">Verified</th></tr></thead>
            <tbody>
              <tr class="strong"><td>Full system</td><td class="n">{pct(b.copilot.all.citation_correct)}</td><td class="n">{pct(b.copilot.all.verified_rate)}</td></tr>
              {#each Object.entries(b.copilot.ablations) as [k, v]}<tr><td>{ABL[k] ?? k}</td><td class="n">{pct(v.citation_correct)}</td><td class="n">{pct(v.verified_rate)}</td></tr>{/each}
            </tbody>
          </table></div>
        </div>
        <div class="panel">
          <h3>Verifier against corrupted sentences</h3>
          <p class="muted small">{b.perturbation.original_sentences} verified sentences were corrupted five ways; originals pass {pct(b.perturbation.original_pass_rate)}.</p>
          <div class="scroll-x"><table>
            <thead><tr><th>Corruption</th><th class="n">Tried</th><th class="n">Caught</th></tr></thead>
            <tbody>{#each Object.entries(b.perturbation.detection) as [k, v]}<tr><td>{PERT[k]}</td><td class="n">{v.tried}</td><td class="n">{pct(v.rate)}</td></tr>{/each}</tbody>
          </table></div>
        </div>
      </div>

      <div class="panel">
        <h3>Retrieval misses on blind questions</h3>
        <div class="scroll-x"><table>
          <thead><tr><th>Question</th><th>Gold</th><th>Top three</th></tr></thead>
          <tbody>{#each b.retrieval.misses as m}<tr><td>{m.text}</td><td class="mono">{m.gold.join(", ")}</td><td class="mono">{m.top5.slice(0, 3).join(", ")}</td></tr>{/each}</tbody>
        </table></div>
      </div>

      <div class="panel">
        <h3>Safety probes</h3>
        <div class="scroll-x"><table>
          <thead><tr><th>Probe</th><th>Checks</th><th>Result</th></tr></thead>
          <tbody>{#each b.probes.results as p}<tr><td>{p.probe}</td><td class="small">{Object.keys(p.checks).join(", ")}</td>
            <td><span class="chip {p.passed ? 'ok' : 'crit'}">{p.passed ? "passed" : "failed"}</span></td></tr>{/each}</tbody>
        </table></div>
      </div>
    {/if}

    {#if d}
      <div class="panel">
        <h3>Development results</h3>
        <p class="small">Retrieval, question grouped cross validation: hit@1 {d.retrieval.cross_validated_learned["hit@1"].toFixed(3)}, nDCG@10
          {d.retrieval.cross_validated_learned["ndcg@10"].toFixed(3)}. Copilot on {d.copilot.all.scenarios} development scenarios: action F1
          {d.copilot.all.actions.f1.toFixed(3)}, citations correct {pct(d.copilot.all.citation_correct)}, verified {pct(d.copilot.all.verified_rate)}.
          Deterioration model, patient grouped cross validation: AUROC {d.model.dev_cv.rolling_hgb.auroc.toFixed(3)}, AUPRC {d.model.dev_cv.rolling_hgb.auprc.toFixed(3)}.</p>
      </div>
    {/if}
  </div>
{/if}

<style>
  .small { font-size: 0.85rem; }
  .two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
  @media (max-width: 860px) { .two { grid-template-columns: minmax(0, 1fr); } }
  h3 { margin-bottom: 6px; }
  tr.strong td { font-weight: 700; }
</style>
