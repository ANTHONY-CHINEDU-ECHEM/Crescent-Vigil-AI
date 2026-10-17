# Safety

Crescent Vigil AI is a research and teaching tool built on synthetic data. It is not a medical device. The safety design below is what a clinical version would need at a minimum; it is not a claim that this version is safe for use with real patients.

## What the system never does

1. It never calculates, suggests or repeats a drug dose. Plans in the cohort contain no doses. Dose questions are answered with card G062 and, when a plan exists, with the plan's agent and route and the phrase "dose as written in the signed individual plan". The verifier rejects any sentence that contains a quantity with a unit.
2. It never recommends an agent the patient's plan says to avoid, and never recommends pethidine, which NICE CG143 says not to use. The check is scoped to the clause, so "do not use pethidine" passes and "give pethidine now" fails even if a later clause contains a negation.
3. It never names an opioid other than the plan's first line agent as a recommendation when a plan is on the record. Statements about previous attendances are labelled as history and exempt from this check because they describe what happened, not what to do.
4. It never shows an unverified sentence. Every sentence must cite something that exists, enough of its content words must appear in what it cites, and every number in it must appear there too.

## Input guard

`agent/guard.py` runs before anything is retrieved or logged.

| Class | Detection | Behaviour |
| --- | --- | --- |
| Identifiers | NHS number pattern, email, UK mobile, dates, postcode, hospital number, titles with names, "name is" | replaced with typed placeholders before logging; the original is kept only as a SHA256 |
| Dose request | what or how much with a unit, mg per kg, dosing | card G062, the plan's agent and route, no numbers |
| Override attempt | ignore or disregard instructions or the plan, system prompt, you are now, jailbreak | refused; clinical actions for the patient are still shown |
| Crisis disclosure | self harm, suicide, end it all | card G063 first, then the rest of the answer |
| Out of scope population | children under 16, pregnancy | scope card first |
| Off topic | nothing from the clinical vocabulary | refused |

The clinical actions are never blocked by the guard: a clinician who types something irrelevant still sees what is overdue for their patient.

## Audit

Each run appends a record to `data/audit/copilot_audit.jsonl` with the redacted question, the SHA256 of the original, flags, the actions and overdue steps shown, the number of sentences kept and dropped, and the risk estimate. Each line includes the hash of the line before it, so editing or deleting history breaks the chain; `GET /api/audit` reports whether the chain is intact.

## Testing

The blind evaluation runs 25 fixed safety probes (dose requests, override attempts, pethidine, crisis, scope, identifiers, plan first answers) and corrupts verified sentences five ways (inserted dose, avoided agent, changed number, removed citations, wrong card) to measure how often the verifier catches each. Results are in `reports/evaluation_summary.json` and `docs/evaluation.md`.

## Known gaps

The guard uses patterns, so unusual phrasing can slip through, and the identifier patterns are UK specific. The lexical support check cannot tell whether a sentence's meaning matches its source, only whether its words and numbers appear there. A clinical deployment would need a clinical safety case under DCB0129 and DCB0160, real data governance and prospective evaluation.
