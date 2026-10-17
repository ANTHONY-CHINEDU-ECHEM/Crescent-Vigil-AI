// Retrieval: a port of crescent_vigil/retrieval/index.py (BM25F, latent semantic space, context features, ranker).
import { canonical, tokens } from "./text";

export interface PassageT {
  pid: string; kind: string; title: string; body: string; source: string;
  phases: string[]; situations: string[]; entities: string[];
}

export interface IndexExport {
  vocab: string[]; df: number[]; avg_len: Record<string, number>;
  tf: Record<string, Record<string, number>>[]; lens: Record<string, number>[];
  lsa_idf: number[]; lsa_components: number[][]; doc_vecs: number[][];
  entity_tokens: string[][][]; title_tokens: string[][]; passages: PassageT[];
  params: { k1: number; b: number; field_weights: Record<string, number> };
}

export interface RankerT { features: string[]; weights: number[]; bias: number; mean: number[]; std: number[] }

const FIELDS = ["title", "entities", "body"];

export class Index {
  vocab = new Map<string, number>();
  entitySets: Set<string>[][];
  titleSets: Set<string>[];
  constructor(public x: IndexExport, public situationTerms: Record<string, string[]>) {
    x.vocab.forEach((w, i) => this.vocab.set(w, i));
    this.entitySets = x.entity_tokens.map((ents) => ents.map((e) => new Set(e)));
    this.titleSets = x.title_tokens.map((t) => new Set(t));
  }

  get passages() { return this.x.passages; }

  bm25(qtoks: string[]): number[] {
    const N = this.x.passages.length;
    const out = new Array(N).fill(0);
    const { k1, b, field_weights } = this.x.params;
    const uniq = Array.from(new Set(qtoks)).sort();
    for (const w of uniq) {
      const j = this.vocab.get(w);
      if (j === undefined) continue;
      const n = this.x.df[j];
      const idf = Math.log(1 + (N - n + 0.5) / (n + 0.5));
      for (let i = 0; i < N; i++) {
        let t = 0;
        for (const f of FIELDS) {
          const c = this.x.tf[i][f][w] || 0;
          if (c) t += field_weights[f] * c / (1 - b + b * this.x.lens[i][f] / this.x.avg_len[f]);
        }
        if (t) out[i] += idf * t / (k1 + t);
      }
    }
    return out;
  }

  lsa(qtoks: string[]): number[] {
    const N = this.x.passages.length;
    const counts = new Map<string, number>();
    for (const w of qtoks) counts.set(w, (counts.get(w) || 0) + 1);
    const v = new Map<number, number>();
    for (const [w, n] of counts) {
      const j = this.vocab.get(w);
      if (j !== undefined) v.set(j, (1 + Math.log(n)) * this.x.lsa_idf[j]);
    }
    let nv = 0;
    for (const val of v.values()) nv += val * val;
    nv = Math.sqrt(nv);
    if (nv === 0) return new Array(N).fill(0);
    const K = this.x.lsa_components.length;
    const q = new Array(K).fill(0);
    for (let k = 0; k < K; k++) {
      let s = 0;
      for (const [j, val] of v) s += (val / nv) * this.x.lsa_components[k][j];
      q[k] = s;
    }
    const nq = Math.sqrt(q.reduce((a, c) => a + c * c, 0));
    if (!nq) return new Array(N).fill(0);
    return this.x.doc_vecs.map((d) => d.reduce((a, c, k) => a + c * (q[k] / nq), 0));
  }

  situationsFor(text: string, record?: string[]): Set<string> {
    const t = canonical(text);
    const found = new Set<string>();
    for (const [s, terms] of Object.entries(this.situationTerms)) if (terms.some((term) => t.includes(term))) found.add(s);
    for (const r of record || []) found.add(r);
    return found;
  }

  features(query: string, minute: number | null, admittedMin: number | null, recordSits?: string[]): number[][] {
    const qt = tokens(query);
    const qset = new Set(qt);
    const bm = this.bm25(qt);
    const mx = Math.max(...bm);
    const order = bm.map((v, i) => [v, i]).sort((a, b) => (b[0] - a[0]) || (a[1] - b[1])).map((p) => p[1]);
    const rank = new Array(bm.length);
    order.forEach((i, r) => (rank[i] = r + 1));
    const ls = this.lsa(qt);
    const phase = phaseFromMinute(minute, admittedMin);
    const sits = this.situationsFor(query, recordSits);
    return this.x.passages.map((p, i) => {
      const ph = phase === null ? 0.5 : p.phases.includes(phase) ? 1.0 : 0.0;
      const sp = new Set(p.situations);
      let inter = 0;
      for (const s of sits) if (sp.has(s)) inter++;
      const so = sp.size && sits.size ? inter / sp.size : 0.0;
      let hits = 0;
      for (const e of this.entitySets[i]) if (e.size && [...e].every((w) => qset.has(w))) hits++;
      const eh = Math.min(1.0, hits / 2.0);
      const tt = this.titleSets[i];
      let tov = 0;
      for (const w of tt) if (qset.has(w)) tov++;
      const to = tt.size ? tov / tt.size : 0.0;
      return [mx > 0 ? bm[i] / mx : 0.0, bm[i] > 0 ? 1.0 / rank[i] : 0.0, Math.max(0.0, ls[i]), ph, so, eh, to];
    });
  }
}

export function score(r: RankerT, F: number[][], mask?: number[]): number[] {
  const w = r.weights.slice();
  for (const m of mask || []) w[m] = 0;
  return F.map((row) => row.reduce((a, v, j) => a + ((v - r.mean[j]) / r.std[j]) * w[j], 0) + r.bias);
}

export function argsortDesc(s: number[]): number[] {
  return s.map((v, i) => [v, i]).sort((a, b) => (b[0] - a[0]) || (a[1] - b[1])).map((p) => p[1]);
}

export function phaseFromMinute(minute: number | null, admittedMin: number | null): string | null {
  if (minute === null || minute === undefined) return null;
  if (admittedMin !== null && admittedMin !== undefined && minute >= admittedMin) return minute - admittedMin < 24 * 60 ? "ward" : "late";
  if (minute <= 30) return "arrival";
  if (minute <= 120) return "early";
  if (minute <= 24 * 60) return "ward";
  if (minute <= 72 * 60) return "late";
  return "discharge";
}
