# Crescent Vigil AI

<p align="center">
<img width="783" height="820" alt="image" src="https://github.com/user-attachments/assets/680e9b6a-c160-47e3-a1c3-0601ea45ff2b" />
</p>

SOURCE: https://pmc.ncbi.nlm.nih.gov/articles/PMC8454100/

**Time critical decision support for sickle cell vaso occlusive crises: a care plan first retrieval copilot whose every sentence is cited and verified, an acute chest syndrome deterioration model, and an analgesia equity audit, built on a calibrated synthetic emergency department cohort and scored once against a frozen blind set of two unseen hospitals and a later year.**

<p align="center">
<img width="1440" height="1620" alt="bedside" src="https://github.com/user-attachments/assets/e12698cc-6c27-4cda-8ba0-555827882505" />
</p>

## Project brief

A painful vaso occlusive crisis is the most common reason a person with sickle cell disease comes to hospital, and the first hour decides a great deal. NICE asks for analgesia within 30 minutes of arrival, reassessment every 30 minutes until the pain is controlled, and close monitoring because opioids depress breathing and because acute chest syndrome, the leading cause of death in adults with the disease, often develops one to three days into an admission that began as "just pain". The national enquiry A Sickle Crisis? and the parliamentary inquiry No One's Listening both found the same failures again and again: long waits for pain relief, patients disbelieved or labelled as drug seeking, individual care plans that the emergency department could not see, inadequate monitoring after opioids, and deterioration recognised late.

Crescent Vigil AI is built around those failures. At any minute of an attendance it replays the record exactly as a clinician could have seen it, shows what is due and what is overdue against the clock, puts the patient's own signed care plan ahead of generic guidance, raises red flags for sepsis, falling saturation, low respiratory rate, stroke, priapism and acute anaemia, estimates the chance of acute chest syndrome over the next 24 hours, and answers free text questions. Every sentence it shows cites the record, the plan, a previous attendance, the model or one of 64 guidance cards that paraphrase NICE, ASH, BSH, NHLBI and UK standards, and every sentence is verified before it is shown: it must cite something that exists, its words and numbers must appear in what it cites, it must not recommend an agent the plan or guidance says to avoid, and it must never contain a dose. Doses always come from the signed plan or the prescriber. Alongside the copilot, an equity audit measures door to analgesia across plan visibility, attendance frequency, time of arrival, sex, age and site.

No open, patient level dataset of sickle cell emergency attendances exists, so the platform is fed by a generator calibrated to published distributions: 16,000 adults, 178,235 attendances across eight hospitals over five years, 881,152 timeline events, 1,755,128 four hourly ward observation sets and 302,215 ward blood results. Every effect the generator injects is recorded, which turns the audit into a test: it must recover delays that are known to be there. The evaluation was designed first. Before any index, model or copilot existed, 1,600 scenarios with gold actions and 174 clinician style questions were frozen and hashed; the blind half covers two hospitals whose patients the models never saw and every 2025 attendance elsewhere, and it was scored exactly once. The whole engine also runs in the browser: a TypeScript port of the replay, retrieval, verifier, model and copilot reproduces the Python outputs on a 400 case parity fixture, so the demo needs no server.

## What it does

| Workspace | What a clinician or reviewer can do |
| --- | --- |
| Bedside | Pick an attendance, scrub or play the timeline minute by minute, and watch the due and overdue actions, red flags, the patient's plan, the latest observations and bloods, the deterioration risk and its drivers change; ask a question and read an answer whose every sentence cites its source |
| Equity audit | Compare door to analgesia across plan visibility, attendance frequency, arrival time, sex, age and site; see adjusted effects against the injected truth, and what would change if every plan were visible |
| Deterioration model | ROC, precision and recall, calibration, the alert trade off, warning time, subgroup results, failure analysis and feature importance on the blind set |
| Evaluation | The frozen protocol, every blind metric for the copilot, retrieval, safety probes and the verifier, and the retrieval misses |
| Guidance | Search the 64 cards with the same ranker the copilot uses and see the seven features behind each score |
| Audit log | Every copilot run, stored after redaction, with flags, overdue steps and risk |

## Live demo

The demo runs entirely in the browser from an embedded bundle of 271 attendances (eleven teaching cases chosen from the blind set and 260 evaluation scenarios), with no server and no network calls after loading apart from fonts.

**[Open Crescent Vigil AI](https://claude.ai/artifact/6pDNkdghw7knNrWJiibk88)**

To run the full service with all 178,235 attendances, see Running it below.

## Screenshots

<p align="center">
<img width="1440" height="1889" alt="deterioration_case" src="https://github.com/user-attachments/assets/cc5e9093-344c-470f-9356-9f30ec5ba913" />
</p>

**Acute chest syndrome developing on day two.** A blind teaching case 26 hours into the admission. The model estimates a 12% chance of acute chest syndrome in the next 24 hours against a 6% threshold and explains which features drive it; a haemoglobin fall of 6 g/dL below steady state raises a red flag; the question about falling saturation is answered from two cited cards. The synthetic outcome is revealed under the timeline: diagnosis at 30.6 hours.

<p align="center">
<img width="1440" height="1642" alt="dose_request" src="https://github.com/user-attachments/assets/76fa1ea3-33f5-4beb-a4be-77fc526f4669" />
</p>

**A dose question.** The plan names morphine by the intravenous route. Asked for a dose, the copilot cites card G062 and the plan, says the dose is as written in the signed plan and gives no number. First analgesia is flagged overdue at 40 minutes.

<p align="center">
<img width="1440" height="1939" alt="equity" src="https://github.com/user-attachments/assets/5e02d631-07cc-445f-ab61-0161f53aece4" />
</p>

**Equity audit.** In development data, patients whose plan was visible waited a median of 37 minutes against 51; frequent attenders waited 55 against 41. The forest plot sets every adjusted estimate beside the value the generator injected.

<p align="center">
<img width="1440" height="2572" alt="model" src="https://github.com/user-attachments/assets/1e0673ab-bccd-4969-b621-fd2b391ec08e" />
</p>

**Deterioration model.** Blind discrimination, calibration, the alert trade off, warning time, subgroups and a failure analysis.

<p align="center">
<img width="1440" height="2802" alt="evaluation" src="https://github.com/user-attachments/assets/989d3a5d-544c-4e66-aa00-e38afd4f87d4" />
</p>

**Evaluation.** The single blind run with the frozen hash, copilot metrics, retrieval methods and ablations, verifier tests and all 25 safety probes.

<p align="center">
<img width="1440" height="5673" alt="library" src="https://github.com/user-attachments/assets/d481e5c3-0698-4ab6-895c-db745c23f21b" />
</p>

**Guidance.** A search for falling saturation on the ward at minute 1,500 ranks the card on falling saturation first and shows its seven feature values.

DARK THEME

<p align="center">
<img width="1440" height="1000" alt="dark" src="https://github.com/user-attachments/assets/073996df-3fae-4bb0-a850-a2b5c92ea260" />
</p>

PHONE

<p align="center">
<img width="390" height="844" alt="mobile" src="https://github.com/user-attachments/assets/61c8123a-c973-47c3-9be3-a7d94a22f8e5" />
</p>

## Results

### Blind set, scored once

1,600 scenarios, gold actions and 174 questions were frozen and hashed at 09:26:58 UTC on 17 October 2026 (SHA256 `2e54d11f…`), before any index, model or copilot existed. The blind half was scored once at 10:06:55 UTC the same day.

| Copilot, 800 blind scenarios | Result |
| --- | --- |
| Actions, precision and recall | 100% and 100% (2,288 actions) |
| Red flags, precision and recall | 100% and 100% (285) |
| Overdue steps found | 130 of 130 |
| Actions cited to an acceptable guidance card | 2,288 of 2,288 |
| Plan agent and route stated correctly | 56 of 56 |
| Sentences verified | 2,345 of 2,345 |
| Avoided agents recommended, doses shown | 0 and 0 |
| Safety probes passed | 25 of 25 |

The gold actions come from a decision table written from the same guidance as the engine, so this measures faithful implementation on new hospitals and a later year, not clinical validity. Two real bugs were caught this way on development data before the blind run; see [docs/evaluation.md](docs/evaluation.md).

| Deterioration, blind (567,535 observation sets, base rate 3.6%) | AUROC | AUPRC | Brier |
| --- | --- | --- | --- |
| **Gradient boosted hazard model (the product)** | **0.756** | **0.135** | **0.0333** |
| Logistic regression, same features | 0.749 | 0.122 | 0.0336 |
| Saturation rule (below 94% or 3 points under baseline) | 0.574 | 0.045 | |

<p align="center">
<img width="1402" height="498" alt="model_discrimination" src="https://github.com/user-attachments/assets/ce6bc9a5-c2a0-4d7f-90bb-1f54d31b9487" />
</p>

At the alert threshold fixed on development data, the model alerted 79.8% of 3,579 blind episodes a median of 24.2 hours before diagnosis. The saturation rule caught 58.3%. Calibration follows the diagonal across every decile.

<p align="center">
<img width="1200" height="488" alt="alerts" src="https://github.com/user-attachments/assets/f816dd36-4bcf-4adc-953b-ea42ae0b9e09" />
</p>

| Retrieval, 58 blind questions | Hit@1 | Recall@3 | MRR | nDCG@10 |
| --- | --- | --- | --- | --- |
| BM25F alone | 0.707 | 0.767 | 0.792 | 0.803 |
| Latent semantic alone | 0.672 | 0.802 | 0.776 | 0.789 |
| **Learned ranker** | **0.759** | **0.819** | **0.823** | **0.838** |
| Learned ranker without the situation feature | 0.724 | 0.784 | 0.804 | 0.814 |

<p align="center">
<img width="1391" height="556" alt="copilot_quality" src="https://github.com/user-attachments/assets/239cac62-7b9d-474f-8eb9-6055b2ac2857" />
</p>

### Where it fails

| Failure | Evidence |
| --- | --- |
| The alert burden is high | At 80% of episodes caught, 46.3% of admissions without acute chest syndrome are also alerted: 110 alerts per 100 patient days |
| The model leans on baseline risk | Missed episodes were in lower risk patients (63.6% severe genotype against 86.8% of caught episodes; median risk at the first ward observation 1.2% against 2.8%); false alerts were the mirror image (81.3% severe genotype against 59.3%). Missed episodes were not diagnosed earlier than caught ones |
| Milder genotypes are under alerted | Sensitivity 84.3% in HbSS, HbS beta zero and HbSD but 59.0% in HbSC and HbS beta plus |
| Retrieval drops on unseen phrasing | Hit@1 0.836 in development cross validation, 0.759 on blind questions; 14 misses, five with the right card second or third |
| The verifier checks words, not meaning | It caught 98.0% of changed numbers and 99.4% of wrong citations, but a wrong citation that shares enough words passes |
| The admission model adds little | Blind AUROC 0.665; logistic regression did slightly better in development |

The model failure analysis reads the stored blind predictions and does not score the blind set again. The roadmap is in [docs/evaluation.md](docs/evaluation.md).

<p align="center">
<img width="999" height="488" alt="risk_trajectories" src="https://github.com/user-attachments/assets/2c310fbd-e5f9-47ca-b11f-8c0f2fafc121" />
</p>

### Equity audit

| Slice | Pain like attendances | Median wait | Within 30 min | Effects recovered |
| --- | --- | --- | --- | --- |
| Development sites, 2021 to 2024 | 107,658 | 45 min | 25.9% | 8 of 8 |
| Held out sites G and H | 28,951 | 44 min | 26.9% | 8 of 8 |
| Sites A to F in 2025 | 27,056 | 46 min | 24.8% | 7 of 8 |

<p align="center">
<img width="1200" height="488" alt="door_to_analgesia" src="https://github.com/user-attachments/assets/d588be68-05a7-49e9-9da4-4a055e1105a8" />
</p>

<p align="center">
<img width="1421" height="528" alt="effect_recovery" src="https://github.com/user-attachments/assets/778b018d-ee86-468f-acc9-9e36e9101793" />
</p>

The adjusted regression recovers 23 of 24 injected effects within their 95% intervals; the miss is crowding in 2025 (estimate 0.446, interval 0.413 to 0.480, true 0.48). The audit also found all 765 pethidine administrations in development data, every one at a non specialist site with no plan visible, and estimates that making every existing plan visible at arrival would raise the share treated within 30 minutes from 25.9% to 28.7%, and from 26.9% to 31.2% at the held out sites.

### Components

| Component | Result |
| --- | --- |
| Snapshot replay | no future event, observation or result visible; asserted on random attendances |
| Training and live features | identical for every feature on 25 sampled admissions at every observation hour |
| Browser engine | reproduces actions, cards, sentences, citations, flags, redactions and risk (to within one part in a billion) on 400 parity cases, 125 of them with a risk estimate |
| Verifier, blind corruptions | doses 100%, avoided agents 100%, citations removed 100%, wrong card 99.4%, changed numbers 98.0% |
| Development cross validation | ranker hit@1 0.836, nDCG@10 0.902; model AUROC 0.764, AUPRC 0.136 |

## Architecture

```
calibrated generator, fixed seed                                 make data
        ▼
sites, patients, care plans, attendances, events,
ward observations, ward bloods, injected ground truth
        ▼
frozen and hashed scenarios, gold actions and questions          make freeze
        ▼
event store and snapshot replay                                   make db
        ▼
guidance cards, retrieval index, ranker on development questions  make index
        ▼
deterioration models on development attendances                   make train
        ▼
copilot state machine and equity audit                            make audit
        ▼
development evaluation, then one blind run                        make evaluate, make evaluate_blind
        ▼
FastAPI service and Svelte interface; the interface also runs alone in the browser
```

The copilot is a state machine of eight nodes (guard, situate, assess risk, plan actions, ground actions, answer question, verify, audit), each timed and shown in the interface. See [docs/architecture.md](docs/architecture.md).

## Data foundation

| Table | Rows | Used for |
| --- | --- | --- |
| Patients | 16,000 | genotype, steady state haemoglobin and saturation, foetal haemoglobin, hydroxyurea, previous acute chest syndrome, asthma, renal impairment |
| Care plans | 8,473 | first line agent and route, adjuncts, agents to avoid, intolerances, notes, review cycle; never a dose |
| Attendances | 178,235 | arrival observations and bloods, triage, crowding, plan visibility, door to analgesia, reassessment, disposition, outcomes |
| Events | 881,152 | the event sourced timeline in minutes from arrival |
| Ward observations | 1,755,128 | four hourly for 72 hours after admission, with a prodrome before acute chest syndrome and realistic confounders |
| Ward bloods | 302,215 | haemoglobin, platelets, white cells, CRP and LDH at 24 and 48 hours |
| Guidance cards | 64 | paraphrases of ten published sources, each tagged by phase, situation and entities |
| Held out questions | 174 | written as a clinician types them, with the cards that answer them |

Every table is listed with its SHA256 in `data/synthetic/MANIFEST.json`, and every injected effect is in `data/synthetic/ground_truth.json`. See [docs/data_card.md](docs/data_card.md) and [docs/guidance_method.md](docs/guidance_method.md).

## Methods

| Area | Method |
| --- | --- |
| Generator | seasonal Poisson attendances scaled by a lognormal propensity; log linear door to analgesia with eight documented effects, site random effects and residual noise; latent logistic risk of acute chest syndrome with gamma distributed onset, a saturation and respiratory rate prodrome, and confounders (transient desaturation, opioid related low respiratory rate, other infections) |
| Snapshot | results visible from the time they are reported: triage observations at minute 6, arrival bloods at minute 60, ward bloods an hour after sampling |
| Engine | clock actions against the 30 minute target and plan reassessment interval; plan first analgesia; red flags for fever, saturation below 94% or 3 points under baseline, respiratory rate of 24 or more or 10 or less, neurological symptoms, priapism, chest presentation and a haemoglobin fall of 2 g/dL |
| Retrieval | synonym canonicalisation; BM25F over title, entities and body; latent semantic similarity; phase, situation, entity and title features; logistic ranker fitted on development questions |
| Grounding | each action cites its record facts, its plan section where relevant, and the top guidance card for its query |
| Verifier | citation existence, lexical support of at least 40%, numeric support, clause scoped negation for avoided agents, plan agent consistency, dose pattern |
| Guard | redaction of NHS numbers, names, dates, phone numbers, emails, postcodes and hospital numbers before anything is logged; fixed paths for dose requests, override attempts, crisis disclosures, out of scope populations and off topic questions |
| Deterioration | histogram gradient boosted discrete time hazard model over 46 features; settings by patient grouped cross validation; isotonic calibration on out of fold predictions; alert threshold fixed at 80% of development episodes |
| Equity | Kaplan Meier curves of time to analgesia; log linear regression with site fixed effects and robust errors; parameter recovery against the injected truth; counterfactual plan visibility |
| Audit | append only, hash chained log of every run |
| Browser | TypeScript port of every runtime component with Python style rounding, checked by a 400 case parity fixture; gzip bundle decompressed with DecompressionStream |

## Running it

Requirements: Python 3.11 or later, Node 20 or later, about 2 GB of free disk and 4 GB of memory.

```
pip install .
pip install pytest
make all          # generate, freeze, load, index, train, audit, evaluate on development data, draw figures
make test         # 15 Python tests, then the TypeScript unit and parity tests
make serve        # API and interface on http://localhost:8000
```

The frozen sets and the blind run log ship with the repository. `make evaluate_blind` scores the blind set again and appends a timestamp to `data/eval/blind_runs.json`, so any later run is visible. To rebuild the browser demo:

```
make bundle web   # export the bundle and parity fixture, build web/dist
make artifact     # single self contained page in web/dist_single
```

With Docker, `docker compose up` serves the API and interface on port 8000. An optional local language model writer for free text answers, verified like everything else, is described in [docs/deployment.md](docs/deployment.md). The API is documented in [docs/api.md](docs/api.md).

## Repository layout

| Path | Contents |
| --- | --- |
| `crescent_vigil/synth` | calibrated generator and its injected ground truth |
| `crescent_vigil/timeline` | DuckDB event store and snapshot replay |
| `crescent_vigil/knowledge` | guidance card parser, plan and history passages |
| `crescent_vigil/retrieval` | tokeniser, BM25F, latent semantic space, context features, ranker |
| `crescent_vigil/agent` | guard, engine, verifier, copilot state machine, audit chain |
| `crescent_vigil/models` | person period features and the deterioration models |
| `crescent_vigil/equity` | the analgesia equity audit |
| `crescent_vigil/eval` | frozen splits, gold decision table, probes, evaluation, post hoc analysis, figures |
| `crescent_vigil/api` | FastAPI service |
| `crescent_vigil/export` | browser bundle and parity fixture |
| `knowledge` | 64 guidance cards, synonym rules, held out questions |
| `web` | Svelte and TypeScript interface with the browser engine and its tests |
| `data` | synthetic tables, frozen evaluation sets and run log, index, exported models |
| `reports` | evaluation summary, equity audit, model curves, blind predictions, figures |
| `docs` | architecture, data card, guidance method, model card, evaluation, safety, API, deployment, screenshots |
| `tests` | Python tests for the data, snapshots, features, guard, verifier, audit chain, copilot, retrieval and API |

## Intended use and limitations

Crescent Vigil AI is a research and teaching tool. It shows how a time aware, care plan first, verified copilot could support emergency and ward staff, and how an audit can measure delays in pain relief. It is not a medical device and must not be used to make or delay decisions about real patients.

1. Every patient is synthetic. The generator is calibrated to published figures, but results describe how well the software recovers structure the generator put there, not how it would perform on real records.
2. Scenario agreement is with a decision table written from the same guidance, so it measures implementation, not clinical validity.
3. The guidance cards paraphrase published guidance at a point in time, were written by one author and have not been reviewed by a haematologist; children and pregnancy are out of scope.
4. The deterioration model leans on baseline risk, alerts often, and under alerts in milder genotypes.
5. The verifier checks that words and numbers are supported, not that meaning is.
6. The audit can recover injected effects; on real data it would show associations, not causes. Ethnicity is not modelled because almost every patient shares African or Caribbean ancestry.

## Documentation

| Document | Contents |
| --- | --- |
| [docs/architecture.md](docs/architecture.md) | layers, make targets and data flow |
| [docs/data_card.md](docs/data_card.md) | why the data are synthetic, every table, every generator parameter, splits and known issues |
| [docs/guidance_method.md](docs/guidance_method.md) | how the 64 cards and 174 questions were written |
| [docs/model_card.md](docs/model_card.md) | every learned component, its data, results and failure modes |
| [docs/evaluation.md](docs/evaluation.md) | protocol, full results, failures and roadmap |
| [docs/safety.md](docs/safety.md) | what the system never does, the guard, the audit chain and known gaps |
| [docs/api.md](docs/api.md) | API endpoints and response format |
| [docs/deployment.md](docs/deployment.md) | local, Docker, optional language model writer and static hosting |

## Licence

The code is released under the MIT licence; see [LICENSE](LICENSE). The synthetic data are generated by this repository and released under the same terms. The guidance cards paraphrase the sources below and do not reproduce their text.

## References

1. National Institute for Health and Care Excellence. Sickle cell disease: managing acute painful episodes in hospital (CG143). 2012.
2. Yawn BP, Buchanan GR, Afenyi Annan AN, et al. Management of sickle cell disease: summary of the 2014 evidence based report by expert panel members. JAMA 2014.
3. Brandow AM, Carroll CP, Creary S, et al. American Society of Hematology 2020 guidelines for sickle cell disease: management of acute and chronic pain. Blood Advances 2020.
4. Howard J, Hart N, Roberts Harewood M, et al. Guideline on the management of acute chest syndrome in sickle cell disease. British Journal of Haematology 2015.
5. Sickle Cell Society. Standards for the clinical care of adults with sickle cell disease in the UK, second edition. 2018.
6. National Confidential Enquiry into Patient Outcome and Death. A Sickle Crisis? 2008.
7. All Party Parliamentary Group on Sickle Cell and Thalassaemia. No One's Listening: an inquiry into the avoidable deaths and failures of care for sickle cell patients in secondary care. 2021.
8. National Institute for Health and Care Excellence. Suspected sepsis: recognition, diagnosis and early management (NG51). 2016, updated 2024.
9. Davis BA, Allard S, Qureshi A, et al. Guidelines on red cell transfusion in sickle cell disease. Part II: indications for transfusion. British Journal of Haematology 2017.
10. DeBaun MR, Jordan LC, King AA, et al. American Society of Hematology 2020 guidelines for sickle cell disease: prevention, diagnosis, and treatment of cerebrovascular disease in children and adults. Blood Advances 2020.
11. Vichinsky EP, Neumayr LD, Earles AN, et al. Causes and outcomes of the acute chest syndrome in sickle cell disease. New England Journal of Medicine 2000.
