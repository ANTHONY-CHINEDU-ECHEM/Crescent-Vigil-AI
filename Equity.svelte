<script lang="ts">
  import Chart from "./Chart.svelte";
  let { data } = $props();
  const eq = data.reports.equity;
  let slice = $state("dev");
  const SLICES = [["dev", "Development sites"], ["blind_site", "Held out sites"], ["blind_temporal", "2025"]];
  const cur = $derived(eq ? eq[slice] : null);
  const NAMES: Record<string, string> = {
    crowding: "Department crowding (per unit)", triage_cat2: "Triage category 2", triage_cat1: "Triage category 1",
    plan_visible: "Individual plan visible", high_frequency_attender: "Frequent attender", night: "Night arrival", female: "Female", age_50_plus: "Age 50 and over",
  };
  const km = (names: string[]) => cur ? names.map((n) => ({ name: n, points: eq.dev.km_grid.map((g: number, i: number) => [g, cur.km[n][i]]) })) : [];
  const pct = (x: number) => `${(100 * x).toFixed(1)}%`;
  // Forest plot geometry
  const FW = 520, FL = 190, FR = 16;
  const lo = -0.6, hi = 0.6;
  const fx = (v: number) => FL + ((v - lo) / (hi - lo)) * (FW - FL - FR);
</script>

{#if !eq}
  <div class="panel"><p class="muted">Run make audit to build the equity report.</p></div>
{:else}
  <div class="stack">
    <div class="panel">
      <div class="row between">
        <div>
          <h2>Door to analgesia</h2>
          <p class="muted small">{cur.label}: {cur.attendances.toLocaleString()} attendances with pain, chest, abdominal or priapism presentations.</p>
        </div>
        <div class="seg" role="group" aria-label="Data slice">
          {#each SLICES as [k, l]}<button class:on={slice === k} onclick={() => (slice = k)}>{l}</button>{/each}
        </div>
      </div>
      <div class="tiles">
        <div><div class="label">Median</div><div class="num big">{cur.overall.median_min} min</div></div>
        <div><div class="label">Within 30 min (NICE)</div><div class="num big">{pct(cur.overall.within_30)}</div></div>
        <div><div class="label">Within 60 min (ASH)</div><div class="num big">{pct(cur.overall.within_60)}</div></div>
        <div><div class="label">Reassessed in 30 min</div><div class="num big">{pct(cur.overall.reassessed_within_30)}</div></div>
        <div><div class="label">Plan followed when visible</div><div class="num big">{pct(cur.overall.plan_followed_when_visible)}</div></div>
        <div><div class="label">Pethidine given</div><div class="num big">{cur.overall.pethidine_given}</div></div>
      </div>
    </div>

    <div class="two">
      <div class="panel">
        <h3>Share given analgesia by minute, plan visibility</h3>
        <Chart series={km(["plan visible", "no plan visible"])} xLabel="minutes since arrival" yLabel="share given analgesia" yMax={1} xMax={180} pctY refY={null} />
      </div>
      <div class="panel">
        <h3>Share given analgesia by minute, attendance frequency</h3>
        <Chart series={km(["not frequent", "frequent attender"])} xLabel="minutes since arrival" yLabel="share given analgesia" yMax={1} xMax={180} pctY />
      </div>
    </div>

    <div class="panel">
      <h3>Adjusted effects on time to analgesia, against the effects the generator injected</h3>
      <p class="muted small">Regression of log minutes with site fixed effects and robust errors. A ratio above one means a longer wait. Hollow ticks mark the true injected values; bars are 95% intervals.</p>
      <div class="scroll-x">
        <svg viewBox="0 0 {FW} {cur.recovery.length * 30 + 30}" width="100%" style="min-width: 420px; max-width: 720px; display: block" role="img" aria-label="Forest plot of recovered effects">
          {#each [-0.4, -0.2, 0, 0.2, 0.4] as g}
            <line x1={fx(g)} x2={fx(g)} y1="6" y2={cur.recovery.length * 30 + 8} stroke={g === 0 ? "var(--muted)" : "var(--chart-grid)"} />
            <text x={fx(g)} y={cur.recovery.length * 30 + 22} text-anchor="middle">×{Math.exp(g).toFixed(2)}</text>
          {/each}
          {#each cur.recovery as r, i}
            <text x="4" y={i * 30 + 22} style="fill: var(--ink); font-family: var(--font-body); font-size: 12px">{NAMES[r.effect]}</text>
            <line x1={fx(r.ci95[0])} x2={fx(r.ci95[1])} y1={i * 30 + 18} y2={i * 30 + 18} stroke="var(--chart-1)" stroke-width="3" />
            <circle cx={fx(r.estimate)} cy={i * 30 + 18} r="4.5" fill="var(--chart-1)" />
            <rect x={fx(r.true) - 1.5} y={i * 30 + 9} width="3" height="18" fill="none" stroke="var(--chart-2)" stroke-width="1.5" />
          {/each}
        </svg>
      </div>
      <p class="small">{cur.recovery.filter((r: any) => r.covered).length} of {cur.recovery.length} intervals contain the injected value.</p>
    </div>

    <div class="panel">
      <h3>If every existing plan were visible at arrival</h3>
      <p>{cur.counterfactual_all_plans_visible.attendances_with_hidden_plan.toLocaleString()} attendances had a plan that the department could not see.
        Applying the estimated effect of a visible plan to them moves the share treated within 30 minutes from
        <strong class="num">{pct(cur.counterfactual_all_plans_visible.within_30_now)}</strong> to
        <strong class="num">{pct(cur.counterfactual_all_plans_visible.within_30_if_visible)}</strong>.</p>
    </div>

    <div class="two">
      {#each [["plan", "Plan visibility"], ["frequent_attender", "Attendances in the past year"], ["night", "Arrival time"], ["sex", "Sex"], ["age", "Age"], ["site", "Site"]] as [k, title]}
        <div class="panel">
          <h3>{title}</h3>
          <div class="scroll-x"><table>
            <thead><tr><th>Group</th><th class="n">Attendances</th><th class="n">Median</th><th class="n">≤30 min</th><th class="n">≤60 min</th><th class="n">Reassessed</th></tr></thead>
            <tbody>{#each cur.groups[k] as g}<tr><td>{g.group}</td><td class="n">{g.attendances.toLocaleString()}</td><td class="n">{g.median_min}</td>
              <td class="n">{pct(g.within_30)}</td><td class="n">{pct(g.within_60)}</td><td class="n">{pct(g.reassessed_within_30)}</td></tr>{/each}</tbody>
          </table></div>
        </div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .between { justify-content: space-between; }
  .small { font-size: 0.85rem; }
  .big { font-size: 1.35rem; }
  .tiles { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-top: 12px; }
  .two { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
  @media (max-width: 860px) { .two { grid-template-columns: minmax(0, 1fr); } }
  .seg { display: flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
  .seg button { border: none; background: var(--surface); padding: 5px 10px; font-size: 0.85rem; }
  .seg button.on { background: var(--accent-soft); color: var(--accent); font-weight: 700; }
  h3 { margin-bottom: 6px; }
</style>
