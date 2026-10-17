<script lang="ts">
  import { onMount } from "svelte";
  import { loadBundle, makeCopilot } from "./lib/load";
  import Bedside from "./views/Bedside.svelte";
  import Equity from "./views/Equity.svelte";
  import ModelView from "./views/ModelView.svelte";
  import Evaluation from "./views/Evaluation.svelte";
  import Library from "./views/Library.svelte";
  import AuditLog from "./views/AuditLog.svelte";
  import About from "./views/About.svelte";

  const TABS = [
    ["bedside", "Bedside"], ["equity", "Equity audit"], ["model", "Deterioration model"], ["evaluation", "Evaluation"],
    ["library", "Guidance"], ["audit", "Audit log"], ["about", "About"],
  ];
  let data: any = $state(null);
  let copilot: any = $state(null);
  let error = $state("");
  let tab = $state("bedside");
  let logVersion = $state(0);
  let theme = $state("");

  onMount(async () => {
    const h = location.hash.replace("#", "");
    if (TABS.some(([k]) => k === h)) tab = h;
    try {
      data = await loadBundle();
      copilot = makeCopilot(data);
    } catch (e: any) {
      error = e.message;
    }
  });

  function go(k: string) {
    tab = k;
    try { history.replaceState(null, "", "#" + k); } catch {}
  }
  function toggleTheme() {
    const cur = document.documentElement.getAttribute("data-theme");
    const dark = cur ? cur === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    theme = dark ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", theme);
  }
</script>

<header class="top">
  <div class="brand">
    <svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true">
      <circle cx="16" cy="16" r="13" fill="var(--accent)" />
      <circle cx="21.5" cy="12.5" r="11" fill="var(--bg)" />
    </svg>
    <div>
      <h1>Crescent Vigil AI</h1>
      <p class="muted sub">Vaso occlusive crisis decision support with care plan first retrieval</p>
    </div>
  </div>
  <div class="row right">
    <span class="chip warn">Synthetic data · research and education only</span>
    <button class="ghost" onclick={toggleTheme} aria-label="Switch light or dark theme">Theme</button>
  </div>
</header>

<nav class="tabs" aria-label="Workspaces">
  {#each TABS as [k, label]}
    <button class:on={tab === k} onclick={() => go(k)} aria-current={tab === k ? "page" : undefined}>{label}</button>
  {/each}
</nav>

<main>
  {#if error}
    <div class="panel"><h2>The bundle did not load</h2><p class="muted">{error}</p></div>
  {:else if !data}
    <div class="panel loading"><p>Loading the engine, the guidance index and the model into your browser…</p></div>
  {:else if tab === "bedside"}
    <Bedside {data} {copilot} onrun={() => (logVersion += 1)} />
  {:else if tab === "equity"}
    <Equity {data} />
  {:else if tab === "model"}
    <ModelView {data} />
  {:else if tab === "evaluation"}
    <Evaluation {data} />
  {:else if tab === "library"}
    <Library {data} {copilot} />
  {:else if tab === "audit"}
    <AuditLog {copilot} version={logVersion} />
  {:else}
    <About {data} />
  {/if}
</main>

<footer class="muted">
  Crescent Vigil AI runs entirely in this page. It never calculates doses, and every sentence it shows cites its source and is verified first.
  It is not a medical device.
</footer>

<style>
  .top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; padding-block: 16px 10px; }
  .brand { display: flex; gap: 12px; align-items: center; }
  .sub { font-size: 0.85rem; }
  .right { justify-content: flex-end; }
  .ghost { background: transparent; border: 1px solid var(--line); border-radius: 6px; padding: 3px 10px; }
  .tabs { display: flex; gap: 4px; overflow-x: auto; border-bottom: 1px solid var(--line); margin-bottom: 14px; }
  .tabs button { background: none; border: none; padding: 8px 12px; color: var(--muted); border-bottom: 2px solid transparent; white-space: nowrap; }
  .tabs button.on { color: var(--ink); border-bottom-color: var(--accent); font-weight: 700; }
  main { min-height: 60vh; }
  .loading { padding-block: 40px; text-align: center; }
  footer { font-size: 0.8rem; padding-block: 24px; max-width: 75ch; }
</style>
