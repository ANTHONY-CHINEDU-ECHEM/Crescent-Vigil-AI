<script lang="ts">
  // Small line chart with a faint grid, an emphasised last point and an optional reference line.
  let { points = [], threshold = null, baseline = null, label = "", kind = "risk" } = $props();
  const W = 320, H = 86, L = 34, R = 8, T = 10, B = 18;
  const xs = $derived(points.map((p: any) => p.x));
  const ys = $derived(points.map((p: any) => p.y));
  const x0 = $derived(xs.length ? Math.min(...xs) : 0);
  const x1 = $derived(xs.length ? Math.max(...xs, x0 + 1) : 1);
  const yRange = $derived.by(() => {
    if (kind === "risk") return [0, Math.max(0.5, ...(ys.length ? ys : [0]), (threshold ?? 0) * 1.4)];
    const vals = [...ys, ...(baseline !== null ? [baseline] : [])];
    if (!vals.length) return [0, 1];
    const lo = Math.min(...vals), hi = Math.max(...vals);
    const pad = Math.max(1, (hi - lo) * 0.15);
    return [lo - pad, hi + pad];
  });
  const sx = (x: number) => L + ((x - x0) / (x1 - x0 || 1)) * (W - L - R);
  const sy = (y: number) => T + (1 - (y - yRange[0]) / (yRange[1] - yRange[0] || 1)) * (H - T - B);
  const path = $derived(points.map((p: any, i: number) => `${i ? "L" : "M"}${sx(p.x).toFixed(1)},${sy(p.y).toFixed(1)}`).join(" "));
  const area = $derived(points.length > 1 && kind === "risk" ? `${path} L${sx(points[points.length - 1].x).toFixed(1)},${sy(yRange[0])} L${sx(points[0].x).toFixed(1)},${sy(yRange[0])} Z` : "");
  const fmt = (v: number) => (kind === "risk" ? `${Math.round(v * 100)}%` : Math.abs(v) < 10 ? v.toFixed(1) : v.toFixed(0));
  const last = $derived(points.length ? points[points.length - 1] : null);
</script>

<figure>
  {#if label}<figcaption class="label">{label}</figcaption>{/if}
  {#if points.length}
    <svg viewBox="0 0 {W} {H}" width="100%" role="img" aria-label={label || "risk over time"}>
      {#each [yRange[0], (yRange[0] + yRange[1]) / 2, yRange[1]] as g}
        <line x1={L} x2={W - R} y1={sy(g)} y2={sy(g)} stroke="var(--chart-grid)" stroke-width="1" />
        <text x={L - 4} y={sy(g) + 3} text-anchor="end">{fmt(g)}</text>
      {/each}
      {#if threshold !== null}
        <line x1={L} x2={W - R} y1={sy(threshold)} y2={sy(threshold)} stroke="var(--crit)" stroke-dasharray="4 3" stroke-width="1" />
      {/if}
      {#if baseline !== null}
        <line x1={L} x2={W - R} y1={sy(baseline)} y2={sy(baseline)} stroke="var(--muted)" stroke-dasharray="2 3" stroke-width="1" />
      {/if}
      {#if area}<path d={area} fill="var(--accent-soft)" stroke="none" />{/if}
      <path d={path} fill="none" stroke="var(--chart-1)" stroke-width="1.8" />
      {#each points as p}<circle class="hit" cx={sx(p.x)} cy={sy(p.y)} r="6"><title>{p.x.toFixed(1)} h: {fmt(p.y)}</title></circle>{/each}
      {#if last}<circle cx={sx(last.x)} cy={sy(last.y)} r="4" fill="var(--chart-1)" />{/if}
      <text x={L} y={H - 4}>{x0.toFixed(0)} h</text>
      <text x={W - R} y={H - 4} text-anchor="end">{x1.toFixed(0)} h</text>
    </svg>
  {:else}
    <p class="muted small">No readings yet.</p>
  {/if}
</figure>

<style>
  figure { margin: 6px 0; }
  .hit { fill: transparent; }
  .hit:hover { fill: var(--accent-soft); stroke: var(--accent); }
  .small { font-size: 0.85rem; }
</style>
