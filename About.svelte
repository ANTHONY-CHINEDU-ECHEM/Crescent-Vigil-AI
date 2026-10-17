<script lang="ts">
  let { data } = $props();
  const c = data.reports.cohort;
</script>

<div class="cols">
  <article class="panel prose">
    <h2>What this is</h2>
    <p>Crescent Vigil AI supports emergency and ward staff caring for adults in a sickle cell vaso occlusive crisis. At any minute of an attendance it
      replays the record, shows what is due and what is overdue, puts the patient's own signed care plan ahead of generic guidance, raises red flags,
      estimates the chance of acute chest syndrome over the next 24 hours, and answers questions with sentences that each cite their source.</p>
    <p>Every sentence is checked before it is shown: it must cite something that exists, its words and numbers must appear in what it cites, it must not
      recommend an agent the plan or guidance says to avoid, and it must not contain a dose. Doses always come from the signed plan or the prescriber.</p>
    <h2>Intended use</h2>
    <p>A research and teaching tool. It is not a medical device and must not be used to make or delay decisions about real patients.</p>
    <h2>Limitations</h2>
    <ul>
      <li>Every patient is synthetic. The generator is calibrated to published figures, but real departments differ, so absolute performance here
        says little about performance on real records.</li>
      <li>The scenario gold standard is a decision table written from the same guidance cards; agreement measures faithful implementation, not clinical validity.</li>
      <li>Guidance cards paraphrase national guidance at a point in time and cover adult care only; children and pregnancy are out of scope.</li>
      <li>The deterioration model sees four hourly observations; episodes diagnosed early in an admission give it little time to warn.</li>
      <li>The equity audit checks effects that were injected into the data. On real data it can show associations, not causes.</li>
    </ul>
  </article>
  <aside class="panel">
    <h2>Data</h2>
    {#if c}
      <dl>
        <dt>Patients</dt><dd class="num">{c.patients.toLocaleString()}</dd>
        <dt>Attendances</dt><dd class="num">{c.attendances.toLocaleString()}</dd>
        <dt>Admissions</dt><dd class="num">{c.admissions.toLocaleString()}</dd>
        <dt>Observation sets</dt><dd class="num">{c.obs_rows.toLocaleString()}</dd>
        <dt>Events</dt><dd class="num">{c.events.toLocaleString()}</dd>
        <dt>Sites</dt><dd class="num">{c.sites}</dd>
      </dl>
    {/if}
    <h2>Sources</h2>
    <ol class="src">{#each Object.entries(data.sources) as [k, v]}<li><span class="mono">{k}</span> {v}</li>{/each}</ol>
  </aside>
</div>

<style>
  .cols { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 14px; align-items: start; }
  @media (max-width: 800px) { .cols { grid-template-columns: minmax(0, 1fr); } }
  .prose { max-width: 72ch; display: flex; flex-direction: column; gap: 10px; }
  .prose ul { margin: 0; padding-left: 18px; display: flex; flex-direction: column; gap: 6px; }
  dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 8px 0 16px; }
  dt { color: var(--muted); }
  dd { margin: 0; text-align: right; }
  .src { padding-left: 0; list-style: none; font-size: 0.82rem; display: flex; flex-direction: column; gap: 6px; margin-top: 8px; }
</style>
