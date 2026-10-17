# Evaluation

## Protocol

1. The blind set was defined in `config.py` before any data existed: sites G and H in full, and every 2025 attendance at sites A to F.
2. After generating the cohort and before building any index, model or copilot, `make freeze` sampled 800 development and 800 blind scenarios (an attendance and a minute; a quarter drawn from rare presentations, 60% of admitted ones placed on the ward), computed gold actions with the reference decision table in `eval/gold.py`, split the 174 held out questions (116 development, 58 blind) and recorded SHA256 hashes. Frozen at 09:26:58 UTC on 17 October 2026, combined hash `2e54d11f…`.
3. All tuning used development data: the ranker on development questions, the model settings and alert threshold by patient grouped cross validation, and every fix to the copilot on development scenarios.
4. The blind set was scored once, at 10:06:55 UTC on 17 October 2026, with every component fixed. `data/eval/blind_runs.json` records the run; any later run would appear there.

## Copilot on scenarios

| Metric | Development (800) | Blind (800) | Blind sites (400) | Blind 2025 (400) |
| --- | --- | --- | --- | --- |
| Action precision and recall | 100% and 100% | 100% and 100% | 100% and 100% | 100% and 100% |
| Red flag precision and recall | 100% and 100% | 100% and 100% | 100% and 100% | 100% and 100% |
| Overdue steps found | 144 of 144 | 130 of 130 | 64 of 64 | 66 of 66 |
| Actions cited to an acceptable card | 2,344 of 2,344 | 2,288 of 2,288 | | |
| Plan agent and route stated correctly | 56 of 56 | 56 of 56 | | |
| Sentences verified | 100% of 2,398 | 100% of 2,345 | | |
| Avoided agents recommended | 0 | 0 | 0 | 0 |
| Doses shown | 0 | 0 | 0 | 0 |

**How to read this.** The gold actions come from a decision table written from the same guidance cards as the engine, so perfect agreement shows the engine implements that table faithfully on new hospitals and a later year. It is not evidence of clinical validity. Two bugs found on development scenarios before the blind run show why the check is still worth having: the verifier rejected the fever flag sentence because the 38.0 degree threshold was not in any cited evidence (fixed by citing the local protocol parameters), and it rejected the plan sentence for patients whose plan named diamorphine because a substring test found "morphine" inside it (fixed with word boundaries).

Grounding ablations made no difference to scenario citations: every configuration, including BM25F alone, retrieved an acceptable card for every action. The action queries are written by the engine and match their cards closely, so the context features earn their place on free text questions, below, not on actions.

## Retrieval on held out questions

| Method | Hit@1 | Recall@3 | Recall@5 | MRR | nDCG@10 |
| --- | --- | --- | --- | --- | --- |
| BM25F alone | 0.707 | 0.767 | 0.828 | 0.792 | 0.803 |
| Latent semantic alone | 0.672 | 0.802 | 0.828 | 0.776 | 0.789 |
| **Learned ranker** | **0.759** | **0.819** | **0.879** | **0.823** | **0.838** |
| without phase | 0.741 | 0.819 | 0.888 | 0.816 | 0.834 |
| without situation | 0.724 | 0.784 | 0.888 | 0.804 | 0.814 |
| without entities | 0.759 | 0.819 | 0.879 | 0.823 | 0.838 |
| without title overlap | 0.759 | 0.819 | 0.897 | 0.824 | 0.838 |

Blind, 58 questions. On development questions the learned ranker reached hit@1 0.836 under question grouped cross validation, so performance fell by about eight points on unseen phrasing. Of the 14 blind misses, five had the right card in second or third place. The rest show typical failure modes: "are we late" phrasing with no shared words with the 30 minute card, "plan not visible on our system" pulled towards plan review cards, and "how many milligrams of oxycodone" missing the dose card. In the copilot that last question never reaches retrieval because the guard routes it to card G062; the probe below confirms it.

## Safety

All 25 probes passed on blind scenarios: five dose requests (no numbers, G062 cited), five override attempts (refused, actions still shown), two pethidine questions (G007), two crisis disclosures (G063), two scope questions (G059, G060), two off topic questions (refused), five identifier tests (redacted before logging), and two analgesia questions answered from the plan first.

The verifier was tested by corrupting 1,153 verified blind sentences:

| Corruption | Tried | Caught |
| --- | --- | --- |
| A dose inserted | 1,153 | 100% |
| An avoided agent recommended | 1,153 | 100% |
| A number changed | 439 | 98.0% |
| Citations removed | 1,153 | 100% |
| Cited to the wrong card | 337 | 99.4% |

Changed numbers escape when the new number happens to appear elsewhere in the cited evidence; wrong cards escape when the wrong card shares enough words with the sentence.

## Deterioration model

See `docs/model_card.md`. Blind AUROC 0.756 and AUPRC 0.135 (base rate 3.6%), against 0.749 and 0.122 for logistic regression and 0.574 and 0.045 for the saturation rule. At the threshold fixed on development data, 79.8% of blind episodes were alerted a median of 24.2 hours before diagnosis, with 46.3% of admissions without acute chest syndrome also alerted. Sensitivity was 84.3% in the severe genotypes and 59.0% in HbSC and HbS beta plus.

## Equity audit

| Slice | Pain like attendances | Median minutes | Within 30 min | Within 60 min | Intervals covering the true effect |
| --- | --- | --- | --- | --- | --- |
| Development | 107,658 | 45 | 25.9% | 66.0% | 8 of 8 |
| Held out sites | 28,951 | 44 | 26.9% | 67.6% | 8 of 8 |
| 2025 | 27,056 | 46 | 24.8% | 65.2% | 7 of 8 |

The one miss is crowding in 2025 (estimate 0.446, interval 0.413 to 0.480, true 0.48), which is what a 95% interval should do about once in twenty. The audit also found every pethidine administration (765 in development, at sites C, D and F, all non specialist) and estimated that making every existing plan visible at arrival would raise the share treated within 30 minutes from 25.9% to 28.7% in development and from 26.9% to 31.2% at the held out sites.

## Roadmap

1. Make the deterioration model rely more on trends: features relative to each patient's own admission course, and a sequence model over the observation series, compared on the same frozen sets with a second blind run.
2. Replace the lexical support check with an entailment model trained on perturbed sentences, keeping the rule checks for doses and avoided agents.
3. Add paraphrase training data for the ranker from clinicians, and report retrieval with clinician judged relevance.
4. Run the pipeline on a credentialed real dataset (for example the sickle cell admissions in a critical care database) with a fresh blind split.
