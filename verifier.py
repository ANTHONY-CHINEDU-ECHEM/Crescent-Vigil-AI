"""Sentence level verification of every composed answer.

A sentence survives only if all of these hold:

1. It cites at least one evidence item that exists (a guidance card, a plan
   section, a history passage, a record fact or the model output).
2. Enough of its content words appear in the cited evidence (lexical support).
3. Every number in it appears in the cited evidence (numeric support).
4. It does not recommend an agent the plan or national guidance says to avoid.
5. It does not recommend an opioid other than the plan's first line agent when
   a plan is on the record.
6. It contains no drug dose.

System messages (refusals and scope notices) are exempt from support checks but
are still checked for doses and forbidden agents.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from ..retrieval.text import tokens

NUM = re.compile(r"(?<![A-Za-z])\d+(?:\.\d+)?")
DOSE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|milligrams?|micrograms?|mcg|ml|units?)\b|\bmg\s*/\s*kg\b", re.I)
NEGATION = re.compile(r"\b(?:avoid|do not|don't|never|not|no|rules? (?:it )?out|instead of|intolerance|contraindicat)", re.I)
OPIOIDS = ("morphine", "diamorphine", "oxycodone", "hydromorphone", "fentanyl", "pethidine", "codeine", "tramadol")
GENERIC = set(tokens("the a this that is are be with by for from now give use check record ask review tell patient "
                     "minute minutes since after before percent point points degrees hours ago due target consider prompt "
                     "start continue not yet done any can should may"))
SUPPORT_MIN = 0.4


def affirmed(low: str, term: str) -> bool:
    """True when the term appears at least once without a negation earlier in its own clause."""
    for m in re.finditer(rf"\b{re.escape(term)}\b", low):
        start = max(low.rfind(c, 0, m.start()) for c in ".;:!?")
        clause = low[start + 1:m.start()]
        if not NEGATION.search(clause):
            return True
    return False


@dataclass
class Verdict:
    ok: bool
    reasons: list
    support: float


def numbers(text: str) -> set[str]:
    out = set()
    for n in NUM.findall(text):
        f = float(n)
        out.add(str(int(f)) if f == int(f) else str(f))
    return out


def check_sentence(s: dict, evidence: dict[str, str], forbidden: set[str], plan_agent: str | None) -> Verdict:
    reasons = []
    text = s["text"]
    low = text.lower()
    if DOSE.search(text):
        reasons.append("contains a dose")
    history = s.get("kind") == "history"
    for f in forbidden:
        if not history and affirmed(low, f.lower()):
            reasons.append(f"recommends avoided agent {f}")
    if plan_agent and not history:
        for op in OPIOIDS:
            if op != plan_agent and op not in {f.lower() for f in forbidden} and affirmed(low, op) \
                    and not re.search(rf"\b{op}\b[^.]*\bgiven at minute\b", low):
                reasons.append(f"names {op} although the plan's first line agent is {plan_agent}")
    if s.get("kind") == "system":
        return Verdict(not reasons, reasons, 1.0)
    cites = [c for c in s.get("cites", []) if c in evidence]
    if not cites:
        reasons.append("no valid citation")
        return Verdict(False, reasons, 0.0)
    ev = " ".join(evidence[c] for c in cites)
    content = [w for w in tokens(text) if w not in GENERIC and not w.replace(".", "").isdigit()]
    evt = set(tokens(ev))
    support = sum(w in evt for w in content) / len(content) if content else 1.0
    if support < SUPPORT_MIN:
        reasons.append(f"weak support {support:.2f}")
    missing = numbers(text) - numbers(ev)
    if missing:
        reasons.append("unsupported numbers " + ",".join(sorted(missing)))
    return Verdict(not reasons, reasons, round(support, 3))


def verify(sentences: list[dict], evidence: dict[str, str], forbidden: set[str], plan_agent: str | None) -> tuple[list, list]:
    kept, dropped = [], []
    for s in sentences:
        v = check_sentence(s, evidence, forbidden, plan_agent)
        s = {**s, "verified": v.ok, "support": v.support}
        if v.ok:
            kept.append(s)
        else:
            dropped.append({**s, "reasons": v.reasons})
    return kept, dropped
