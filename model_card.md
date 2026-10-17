# Model card

Crescent Vigil AI contains four learned components. All were fitted on development data only (sites A to F, 2021 to 2024) and scored once on the frozen blind set (sites G and H, and sites A to F in 2025).

## 1. Rolling acute chest syndrome model

| Item | Detail |
| --- | --- |
| Task | at each four hourly ward observation set, the probability that acute chest syndrome is diagnosed within the next 24 hours |
| Unit | one row per admission and observation hour, stopping at diagnosis or discharge; 1,092,237 development rows from 74,035 admissions, 6,762 with acute chest syndrome |
| Inputs | 24 features known at admission (genotype, foetal haemoglobin, hydroxyurea, previous episodes, asthma, renal impairment, presentation, arrival observations and bloods) and 22 that change on the ward (saturation and its gap from baseline, eight hour changes, lowest saturation, respiratory and heart rate, temperature and its maximum, pain, cumulative and recent opioid load, share of incentive spirometry done, changes in ward bloods once reported) |
| Learner | histogram gradient boosted trees, 600 trees, 31 leaves, learning rate 0.03, L2 penalty 3, minimum leaf 80 |
| Selection | three settings compared by AUPRC under five fold patient grouped cross validation |
| Calibration | isotonic map fitted to out of fold predictions |
| Alert threshold | 5.8%, the highest threshold that alerts 80% of development episodes before diagnosis |
| Baselines | logistic regression on the same features; a rule that fires when saturation is below 94% or at least three points below the patient's baseline |

### Results

| Data | Model | AUROC | AUPRC | Brier |
| --- | --- | --- | --- | --- |
| Development, cross validated | gradient boosted | 0.764 | 0.136 | 0.0327 |
| Development, cross validated | logistic regression | 0.756 | 0.123 | 0.0330 |
| Development, cross validated | saturation rule | 0.569 | 0.043 | |
| Blind, all | gradient boosted | 0.756 | 0.135 | 0.0333 |
| Blind, all | logistic regression | 0.749 | 0.122 | 0.0336 |
| Blind, all | saturation rule | 0.574 | 0.045 | |
| Blind, held out sites | gradient boosted | 0.755 | 0.136 | 0.0331 |
| Blind, 2025 | gradient boosted | 0.758 | 0.133 | 0.0335 |

The base rate is 3.6% of observation sets. Calibration on the blind set follows the diagonal across deciles from 0.2% to 12%.

At the frozen threshold the model alerted 79.8% of 3,579 blind episodes, a median of 24.2 hours before diagnosis (interquartile range 11.8 to 38.0), while alerting on 46.3% of admissions without acute chest syndrome: 110 alerts per 100 patient days. The saturation rule caught 58.3% of episodes and alerted on 52.3% of admissions without one.

### Behaviour and failure modes

Permutation importance ranks cumulative opioid load, opioid in the last eight hours, saturation below baseline, previous episodes, temperature and genotype highest. A post hoc analysis of the stored blind predictions (`reports/post_hoc_failures.json`) shows that the model leans on baseline risk: missed episodes were in lower risk patients (63.6% severe genotype against 86.8% of caught episodes; median risk at the first ward observation 1.2% against 2.8%), and false alerts were in higher risk patients (81.3% severe genotype against 59.3% of quiet admissions; higher peak opioid load). Missed episodes were not diagnosed earlier than caught ones. Sensitivity at the frozen threshold was 84.3% in HbSS, HbS beta zero and HbSD but 59.0% in HbSC and HbS beta plus.

## 2. Admission model

The same learner on the 24 admission features, predicting acute chest syndrome within 72 hours. Development AUROC 0.675, blind 0.665. Logistic regression did slightly better in development (0.681), so this model adds little and is reported, not used for alerts.

## 3. Retrieval ranker

Logistic regression over seven retrieval features, fitted on 116 development questions with class balancing. Question grouped cross validation on development: hit@1 0.836, nDCG@10 0.902. Blind, 58 questions: hit@1 0.759, recall@3 0.819, MRR 0.823, nDCG@10 0.838, against 0.707, 0.767, 0.792 and 0.803 for BM25F alone. Removing the situation feature cost the most (hit@1 0.724).

## 4. Equity audit regression

Ordinary least squares on log minutes to first analgesia with site fixed effects and heteroskedasticity robust errors. Not a predictive model; it is judged on recovering the injected effects (23 of 24 intervals across the three slices contain the true value).

## Intended use

Research and teaching. Not for clinical use. The models have only seen synthetic data.

## Ethical considerations

A deterioration alert that leans on baseline risk will alert more often for people with severe disease and less often for milder genotypes. In real use that could mean alert fatigue for one group and false reassurance for another; the subgroup table makes this visible and it would need addressing before any clinical study. The equity audit is designed to measure delays in care, not to profile patients; it reports groups, never individuals.
