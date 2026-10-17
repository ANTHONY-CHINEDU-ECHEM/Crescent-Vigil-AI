// The browser engine must reproduce the Python copilot on the shared fixture.
import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { initText } from "../src/engine/text";
import { Copilot } from "../src/engine/copilot";

const bundle = JSON.parse(readFileSync(new URL("../public/data/bundle.json", import.meta.url), "utf8"));
const fixture = JSON.parse(readFileSync(new URL("../src/engine/parity_fixture.json", import.meta.url), "utf8"));
initText(bundle.synonyms, bundle.stop);
const cp = new Copilot({ protocol: bundle.protocol, index: bundle.index, ranker: bundle.ranker, situation_terms: bundle.situation_terms,
  model: bundle.model, sources: bundle.sources });

describe("parity with the Python copilot", () => {
  it(`reproduces ${fixture.length} fixture cases`, () => {
    const failures: string[] = [];
    for (const f of fixture) {
      const r = cp.run(bundle.records[f.id], f.now, f.q);
      const got = {
        codes: r.actions.map((a: any) => a.code), cards: r.actions.map((a: any) => a.card),
        overdue: r.actions.filter((a: any) => a.overdue).map((a: any) => a.code),
        sentences: r.sentences.map((s: any) => ({ text: s.text, cites: s.cites, kind: s.kind })), dropped: r.dropped.length,
        flags: r.guard.flags, redacted: r.guard.redacted, retrieved: r.retrieved.map((x: any) => x.pid), situations: r.record_situations,
        drivers: r.risk ? r.risk.drivers.map((d: any) => d.feature) : null,
      };
      const want = { codes: f.codes, cards: f.cards, overdue: f.overdue, sentences: f.sentences, dropped: f.dropped, flags: f.flags,
        redacted: f.redacted, retrieved: f.retrieved, situations: f.situations, drivers: f.drivers };
      for (const k of Object.keys(want) as (keyof typeof want)[]) {
        if (JSON.stringify(got[k]) !== JSON.stringify(want[k])) failures.push(`${f.id}@${f.now} "${f.q}" ${k}: ${JSON.stringify(got[k]).slice(0, 300)} != ${JSON.stringify(want[k]).slice(0, 300)}`);
      }
      const rp = r.risk ? r.risk.risk_24h : null;
      if ((rp === null) !== (f.risk === null) || (rp !== null && Math.abs(rp - f.risk) > 1e-9)) failures.push(`${f.id}@${f.now} risk ${rp} != ${f.risk}`);
    }
    expect(failures.slice(0, 15)).toEqual([]);
  });
});
