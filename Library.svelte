<script lang="ts">
  import { score, argsortDesc } from "../engine/retrieval";
  let { data, copilot } = $props();
  const cards = data.index.passages;
  let q = $state("");
  let minute = $state("");
  const FEAT = ["BM25F", "rank", "semantic", "phase", "situation", "entities", "title"];
  const results = $derived.by(() => {
    if (!q.trim()) return [];
    const m = minute === "" ? null : Number(minute);
    const F = copilot.index.features(q, m, null, []);
    const s = score(data.ranker, F);
    return argsortDesc(s).slice(0, 6).map((i: number) => ({ card: cards[i], score: s[i], f: F[i] }));
  });
  const src = (code: string) => code.split(",").map((c: string) => data.sources[c.trim()] ?? c.trim()).join("; ");
</script>

<div class="stack">
  <div class="panel">
    <h2>Search the guidance</h2>
    <p class="muted small">The same ranker the copilot uses: lexical, semantic and context features weighted by a model fitted on development questions.
      Add the minutes since arrival to see the phase feature at work.</p>
    <div class="row">
      <input id="libq" type="text" bind:value={q} placeholder="For example: sats falling on the ward" />
      <input id="libm" type="number" min="0" bind:value={minute} placeholder="minute" aria-label="Minutes since arrival" />
    </div>
    {#if results.length}
      <ol class="res">
        {#each results as r}
          <li>
            <div class="row between"><strong><span class="mono">{r.card.pid}</span> {r.card.title}</strong><span class="num muted">{r.score.toFixed(2)}</span></div>
            <p class="small">{r.card.body}</p>
            <div class="row tight">{#each r.f as v, j}<span class="chip">{FEAT[j]} <span class="num">{v.toFixed(2)}</span></span>{/each}</div>
          </li>
        {/each}
      </ol>
    {/if}
  </div>

  <div class="panel">
    <h2>{cards.length} guidance cards</h2>
    <p class="muted small">Each card paraphrases one recommendation from a published source and carries the phases and situations it applies to.</p>
    <div class="cards">
      {#each cards as c}
        <article>
          <div class="row between"><span class="mono accent">{c.pid}</span><span class="small muted">{c.phases.length === 5 ? "any phase" : c.phases.join(", ")}</span></div>
          <h3>{c.title}</h3>
          <p class="small">{c.body}</p>
          <p class="muted tiny">{c.source.startsWith("S") ? src(c.source) : c.source}</p>
        </article>
      {/each}
    </div>
  </div>
</div>

<style>
  .small { font-size: 0.85rem; }
  .tiny { font-size: 0.75rem; margin-top: 4px; }
  .between { justify-content: space-between; }
  .tight { gap: 4px; }
  .accent { color: var(--accent); }
  input { padding: 8px 10px; border: 1px solid var(--line); border-radius: 6px; background: var(--surface-2); }
  #libq { flex: 1; min-width: 200px; }
  #libm { width: 110px; }
  .res { list-style: none; padding: 0; margin: 12px 0 0; display: flex; flex-direction: column; gap: 10px; }
  .res li { border-top: 1px solid var(--line); padding-top: 8px; }
  .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(min(100%, 300px), 1fr)); gap: 10px; margin-top: 10px; }
  article { border: 1px solid var(--line); border-radius: 6px; padding: 10px; background: var(--surface-2); min-width: 0; }
  article h3 { font-size: 0.95rem; margin: 4px 0; }
</style>
