<script lang="ts">
  // Multi series line chart drawn to one scale, with labelled axes, a faint grid and a legend.
  let { series = [], xLabel = "", yLabel = "", xMax = null, yMax = null, yMin = 0, xMin = 0, diagonal = false,
        refY = null, refLabel = "", height = 220, pctY = false, pctX = false } = $props();
  const W = 520, L = 46, R = 12, T = 12, B = 34;
  const H = $derived(height);
  const allX = $derived(series.flatMap((s: any) => s.points.map((p: any) => p[0])));
  const allY = $derived(series.flatMap((s: any) => s.points.map((p: any) => p[1])));
  const X1 = $derived(xMax ?? Math.max(...allX, xMin + 1));
  const Y1 = $derived(yMax ?? Math.max(...allY, yMin + 1e-9));
  const sx = (x: number) => L + ((x - xMin) / (X1 - xMin)) * (W - L - R);
  const sy = (y: number) => T + (1 - (y - yMin) / (Y1 - yMin)) * (H - T - B);
  const ticks = (lo: number, hi: number, n = 5) => Array.from({ length: n + 1 }, (_, i) => lo + ((hi - lo) * i) / n);
  const fx = (v: number) => (pctX ? `${Math.round(v * 100)}%` : Math.abs(v) >= 100 || Number.isInteger(v) ? v.toFixed(0) : v.toFixed(1));
  const fy = (v: number) => (pctY ? `${Math.round(v * 100)}%` : Math.abs(v) >= 100 || Number.isInteger(v) ? v.toFixed(0) : v.toFixed(2));
  const COLORS = ["var(--chart-1)", "var(--chart-2)", "var(--chart-3)", "var(--ok)"];
  function d(points: number[][]) { return points.map((p, i) => `${i ? "L" : "M"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join(" "); }
</script>

<div class="scroll-x">
  <svg viewBox="0 0 {W} {H}" width="100%" style="min-width: 300px" role="img" aria-label={`${yLabel} by ${xLabel}`}>
    {#each ticks(yMin, Y1) as g}
      <line x1={L} x2={W - R} y1={sy(g)} y2={sy(g)} stroke="var(--chart-grid)" />
      <text x={L - 6} y={sy(g) + 3} text-anchor="end">{fy(g)}</text>
    {/each}
    {#each ticks(xMin, X1) as g}
      <text x={sx(g)} y={H - B + 14} text-anchor="middle">{fx(g)}</text>
    {/each}
    {#if diagonal}<line x1={sx(xMin)} y1={sy(yMin)} x2={sx(X1)} y2={sy(Y1)} stroke="var(--muted)" stroke-dasharray="3 3" />{/if}
    {#if refY !== null}
      <line x1={L} x2={W - R} y1={sy(refY)} y2={sy(refY)} stroke="var(--crit)" stroke-dasharray="4 3" />
      <text x={W - R} y={sy(refY) - 4} text-anchor="end">{refLabel}</text>
    {/if}
    {#each series as s, i}
      <path d={d(s.points)} fill="none" stroke={s.color ?? COLORS[i % 4]} stroke-width="2" stroke-dasharray={s.dash ?? ""} />
      {#if s.dots}{#each s.points as p}<circle cx={sx(p[0])} cy={sy(p[1])} r="4" fill={s.color ?? COLORS[i % 4]} />{/each}{/if}
    {/each}
    {#each series as s}
      {#each s.points.filter((_: any, j: number) => j % Math.max(1, Math.ceil(s.points.length / 60)) === 0) as p}
        <circle class="hit" cx={sx(p[0])} cy={sy(p[1])} r="7"><title>{s.name}: {xLabel} {fx(p[0])}, {yLabel} {fy(p[1])}</title></circle>
      {/each}
    {/each}
    <text x={(L + W - R) / 2} y={H - 2} text-anchor="middle">{xLabel}</text>
    <text x={12} y={(T + H - B) / 2} text-anchor="middle" transform={`rotate(-90 12 ${(T + H - B) / 2})`}>{yLabel}</text>
  </svg>
</div>
<div class="legend">
  {#each series as s, i}<span><i style="background: {s.color ?? COLORS[i % 4]}"></i>{s.name}</span>{/each}
</div>

<style>
  .hit { fill: transparent; }
  .hit:hover { fill: var(--accent-soft); stroke: var(--accent); }
  .legend { display: flex; flex-wrap: wrap; gap: 12px; font-size: 0.8rem; color: var(--muted); margin-top: 4px; }
  .legend i { display: inline-block; width: 12px; height: 3px; vertical-align: middle; margin-right: 5px; border-radius: 2px; }
</style>
