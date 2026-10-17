<script lang="ts">
  let { copilot, version } = $props();
  const rows = $derived.by(() => { version; return copilot.log.slice(0, 200); });
</script>

<div class="panel">
  <h2>Audit log</h2>
  <p class="muted small">Every copilot run in this session, stored after redaction. The service writes the same records to an append only file in which each
    line carries the SHA256 of the line before it, so editing history breaks the chain.</p>
  {#if !rows.length}
    <p class="muted">No runs yet. Open the bedside view to create some.</p>
  {:else}
    <div class="scroll-x"><table>
      <thead><tr><th>Time</th><th>Attendance</th><th class="n">Minute</th><th>Question as stored</th><th>Flags</th><th>Overdue</th><th class="n">Risk</th></tr></thead>
      <tbody>
        {#each rows as r}
          <tr><td class="mono small">{r.ts.slice(11, 19)}</td><td class="mono small">{r.attendance_id}</td><td class="n">{r.now_min}</td>
            <td class="small">{r.question_redacted || "none"}</td><td class="small">{r.flags.join(", ")}</td>
            <td class="small">{r.overdue.join(", ").toLowerCase().replaceAll("_", " ")}</td><td class="n">{r.risk_24h === null ? "" : `${Math.round(100 * r.risk_24h)}%`}</td></tr>
        {/each}
      </tbody>
    </table></div>
  {/if}
</div>

<style>.small { font-size: 0.82rem; }</style>
