// Tokeniser: a line by line port of crescent_vigil/retrieval/text.py.
let RULES: [RegExp, string][] = [];
let STOP = new Set<string>();

export function initText(rules: [string, string][], stop: string[]): void {
  RULES = rules.map(([p, r]) => [new RegExp(`\\b(?:${p})\\b`, "gi"), r]);
  STOP = new Set(stop);
}

export function canonical(text: string): string {
  let t = text.toLowerCase().replace(/-/g, " ");
  for (const [rx, rep] of RULES) t = t.replace(rx, rep);
  return t;
}

export function stem(w: string): string {
  if (w.length <= 4 || /^\d+$/.test(w)) return w;
  if (w.endsWith("ies") && w.length > 5) return w.slice(0, -3) + "y";
  for (const suf of ["ing", "ed", "es", "s"]) {
    if (w.endsWith(suf) && w.length - suf.length >= 4) return w.slice(0, -suf.length);
  }
  return w;
}

export function tokens(text: string): string[] {
  const t = canonical(text);
  const m = t.match(/[a-z0-9]+(?:\.[0-9]+)?/g) || [];
  return m.filter((w) => !STOP.has(w)).map(stem);
}

/** Python style fixed point formatting: exact ties round to even, as f"{x:.nf}" does. */
export function pyFixed(x: number, nd = 0): string {
  // toFixed rounds exact ties upward; Python rounds them to even. Ties are decided on the exact binary value,
  // which toPrecision exposes in full, so only true ties are treated differently.
  if (!Number.isFinite(x)) return String(x);
  const neg = x < 0 || Object.is(x, -0);
  const exact = Math.abs(x).toPrecision(100);
  const [ip, fp = ""] = exact.split(".");
  const keep = fp.slice(0, nd), rest = fp.slice(nd);
  const tie = rest.length > 0 && rest[0] === "5" && /^0*$/.test(rest.slice(1));
  if (!tie) return x.toFixed(nd);
  const digits = (ip + keep).replace(/^0+(?=\d)/, "");
  const last = Number(digits[digits.length - 1]);
  let n = BigInt(digits);
  if (last % 2 === 1) n += 1n;
  let s = n.toString().padStart(nd + 1, "0");
  s = nd ? `${s.slice(0, s.length - nd)}.${s.slice(s.length - nd)}` : s;
  return (neg ? "-" : "") + s;
}

/** Python round() to an integer: ties to even. */
export function pyRound(x: number): number {
  if (Number.isInteger(x * 2) && !Number.isInteger(x)) {
    const n = Math.floor(x);
    return n % 2 === 0 ? n : n + 1;
  }
  return Math.round(x);
}
