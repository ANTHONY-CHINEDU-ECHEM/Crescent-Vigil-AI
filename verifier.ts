// Sentence verifier: a port of crescent_vigil/agent/verifier.py.
import { tokens } from "./text";

const NUM = /(?<![A-Za-z])\d+(?:\.\d+)?/g;
export const DOSE = /\b\d+(?:\.\d+)?\s*(?:mg|milligrams?|micrograms?|mcg|ml|units?)\b|\bmg\s*\/\s*kg\b/i;
const NEGATION = /\b(?:avoid|do not|don't|never|not|no|rules? (?:it )?out|instead of|intolerance|contraindicat)/i;
const OPIOIDS = ["morphine", "diamorphine", "oxycodone", "hydromorphone", "fentanyl", "pethidine", "codeine", "tramadol"];
const SUPPORT_MIN = 0.4;
let GENERIC: Set<string> | null = null;

function generic(): Set<string> {
  if (!GENERIC) GENERIC = new Set(tokens("the a this that is are be with by for from now give use check record ask review tell patient " +
    "minute minutes since after before percent point points degrees hours ago due target consider prompt " +
    "start continue not yet done any can should may"));
  return GENERIC;
}

function esc(s: string) { return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"); }

export function affirmed(low: string, term: string): boolean {
  const rx = new RegExp(`\\b${esc(term)}\\b`, "g");
  let m: RegExpExecArray | null;
  while ((m = rx.exec(low))) {
    const start = Math.max(...[".", ";", ":", "!", "?"].map((c) => low.lastIndexOf(c, m!.index - 1)));
    const clause = low.slice(start + 1, m.index);
    if (!NEGATION.test(clause)) return true;
  }
  return false;
}

export function numbers(text: string): Set<string> {
  const out = new Set<string>();
  for (const n of text.match(NUM) || []) {
    const f = parseFloat(n);
    out.add(Number.isInteger(f) ? String(f) : String(f));
  }
  return out;
}

export interface Verdict { ok: boolean; reasons: string[]; support: number }

export function checkSentence(s: any, evidence: Record<string, string>, forbidden: Set<string>, planAgent: string | null): Verdict {
  const reasons: string[] = [];
  const text: string = s.text;
  const low = text.toLowerCase();
  if (DOSE.test(text)) reasons.push("contains a dose");
  const history = s.kind === "history";
  for (const f of [...forbidden].sort()) {
    if (!history && affirmed(low, f.toLowerCase())) reasons.push(`recommends avoided agent ${f}`);
  }
  if (planAgent && !history) {
    const fl = new Set([...forbidden].map((f) => f.toLowerCase()));
    for (const op of OPIOIDS) {
      if (op !== planAgent && !fl.has(op) && affirmed(low, op) && !new RegExp(`\\b${op}\\b[^.]*\\bgiven at minute\\b`).test(low)) {
        reasons.push(`names ${op} although the plan's first line agent is ${planAgent}`);
      }
    }
  }
  if (s.kind === "system") return { ok: reasons.length === 0, reasons, support: 1.0 };
  const cites = (s.cites || []).filter((c: string) => c in evidence);
  if (!cites.length) { reasons.push("no valid citation"); return { ok: false, reasons, support: 0.0 }; }
  const ev = cites.map((c: string) => evidence[c]).join(" ");
  const G = generic();
  const content = tokens(text).filter((w) => !G.has(w) && !/^\d+$/.test(w.replace(".", "")));
  const evt = new Set(tokens(ev));
  const support = content.length ? content.filter((w) => evt.has(w)).length / content.length : 1.0;
  if (support < SUPPORT_MIN) reasons.push(`weak support ${support.toFixed(2)}`);
  const evn = numbers(ev);
  const missing = [...numbers(text)].filter((n) => !evn.has(n)).sort();
  if (missing.length) reasons.push("unsupported numbers " + missing.join(","));
  return { ok: reasons.length === 0, reasons, support: Math.round(support * 1000) / 1000 };
}

export function verify(sentences: any[], evidence: Record<string, string>, forbidden: Set<string>, planAgent: string | null) {
  const kept: any[] = [], dropped: any[] = [];
  for (const s of sentences) {
    const v = checkSentence(s, evidence, forbidden, planAgent);
    const t = { ...s, verified: v.ok, support: v.support };
    if (v.ok) kept.push(t); else dropped.push({ ...t, reasons: v.reasons });
  }
  return [kept, dropped];
}
