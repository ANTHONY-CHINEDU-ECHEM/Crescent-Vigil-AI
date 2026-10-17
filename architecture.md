# Architecture

Crescent Vigil AI is built in layers. Each layer reads only the outputs of the layer before it, and every output is written to disk so any step can be rerun on its own.

```
calibrated generator, fixed seed                                  make data
        ▼
synthetic tables: sites, patients, care plans, attendances,
events, four hourly observations, ward bloods, ground truth
        ▼
frozen and hashed evaluation sets: scenarios with gold actions,   make freeze
held out clinician questions, split identifiers
        ▼
event store (DuckDB) and snapshot replay                          make db
        ▼
guidance cards, retrieval index, ranker fitted on development     make index
questions
        ▼
deterioration models fitted on development attendances            make train
        ▼
copilot state machine, equity audit                               make audit
        ▼
development evaluation, then one blind run                        make evaluate, make evaluate_blind
        ▼
FastAPI service, Svelte interface, browser engine with parity     make serve, make bundle web artifact
```

## The synthetic cohort

`crescent_vigil/synth/generate.py` writes eight tables from one seed. Patients have a genotype, steady state haemoglobin and oxygen saturation, foetal haemoglobin, hydroxyurea use, previous acute chest syndrome, asthma and renal impairment. About half have a signed individual plan that names a first line agent and route, adjuncts, agents to avoid and notes; plans never contain a dose. Attendances follow a seasonal Poisson process scaled by each patient's propensity to attend. Each attendance has arrival observations and bloods, a triage category, a crowding index, whether the plan was visible in the department record, a door to analgesia time drawn from a documented log linear model, reassessment, disposition, acute chest syndrome at arrival or after admission, and four hourly ward observations with a prodrome before acute chest syndrome and realistic confounders (transient desaturation, opioid related low respiratory rate, other infections).

The parameters the generator used are written to `ground_truth.json`. The equity audit is judged on whether it recovers them.

## Splits

The blind set is defined in `config.py` before any data exists: every attendance at sites G and H (new hospitals and therefore new patients) and every 2025 attendance at sites A to F (a later period). `make freeze` samples 800 development and 800 blind scenarios (an attendance and a minute), computes gold actions with the reference decision table in `eval/gold.py`, splits the held out questions, and records SHA256 hashes in `data/eval/FROZEN.json`. The blind evaluation refuses to run if any frozen file has changed and appends every run to `data/eval/blind_runs.json`.

## Snapshot replay

`timeline/store.py` replays an attendance up to a minute. Results become visible when they are reported, not when the sample is taken: triage observations at minute 6, arrival bloods at minute 60, ward bloods one hour after sampling. Outcomes that have not happened are never included. A test asserts this on random attendances.

## Retrieval

`retrieval/index.py` scores every passage with seven features: BM25F over title, entities and body; the reciprocal BM25F rank; cosine similarity in a latent semantic space (TF IDF and a truncated SVD fitted on the cards); whether the passage applies to the current phase of the attendance; overlap between the passage's situations and the situations implied by the question and the live record; how many of the passage's entity phrases the question names; and title overlap. A logistic ranker fitted on development questions weighs them. Both sides of the index are canonicalised with the same synonym list (`knowledge/synonyms.json`).

## The copilot

`agent/copilot.py` is a state machine with eight nodes: guard, situate, assess risk, plan actions, ground actions, answer question, verify, audit. The engine (`agent/engine.py`) turns the snapshot into actions with record facts attached. Grounding retrieves a guidance card for each action. The patient's plan passages are cited for analgesia actions and answer analgesia questions before any guidance. The verifier (`agent/verifier.py`) checks every sentence; failures are dropped, and a dropped action is replaced by a notice to check with haematology. The audit log is append only and hash chained.

## Deterioration models

`models/features.py` builds 46 features for every (admission, observation hour) pair from the tables, and the same features from a live snapshot; a test asserts the two agree. `models/acs.py` fits a histogram gradient boosted tree ensemble as a discrete time hazard model for diagnosis within 24 hours, chooses settings by patient grouped cross validation, calibrates with an isotonic map fitted to out of fold predictions and fixes the alert threshold on development data. Baselines are logistic regression on the same features and a saturation rule.

## The browser engine

`web/src/engine` is a TypeScript port of the snapshot replay, the engine, the guard, the retrieval features and ranker, the verifier, the tree ensemble with its calibration and the feature builder. `make bundle` exports the data it needs and a parity fixture of Python outputs; `npx vitest run` requires the TypeScript engine to reproduce every action, card, sentence, citation, flag, redaction and risk estimate. Number formatting follows Python's rounding of exact ties so the sentences match character for character.
