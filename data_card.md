# Data card

## Why the data are synthetic

No open, patient level dataset of sickle cell emergency attendances exists. Critical care databases such as MIMIC require credentialed access and contain few sickle cell admissions; UK hospital data cannot be published. Crescent Vigil AI is therefore fed from a generator whose parameters are set from published distributions and stated openly, so that every design choice can be inspected and every result reproduced from one seed.

The consequence is stated plainly throughout the project: results describe how well the software recovers structure that the generator put there. They do not estimate how it would perform on real records.

## Tables

| Table | Rows | Contents |
| --- | --- | --- |
| `sites` | 8 | synthetic departments, specialist centre flag, plan visibility rate, crowding baseline |
| `patients` | 16,000 | genotype, steady state haemoglobin and saturation, foetal haemoglobin, hydroxyurea, previous acute chest syndrome, asthma, renal impairment |
| `care_plans` | 8,473 | first line agent and route, adjuncts, agents to avoid, intolerance, notes, review cycle; no doses |
| `attendances` | 178,235 | arrival observations and bloods, triage, crowding, plan visibility, door to analgesia, reassessment, disposition, outcomes, split |
| `events` | 881,152 | event sourced timeline in minutes from arrival |
| `obs` | 1,755,128 | four hourly ward observations for 72 hours after admission |
| `labs` | 302,215 | bloods at admission, 24 and 48 hours |
| `ground_truth.json` | | every injected effect, for parameter recovery |

Exact counts and SHA256 hashes are in `data/synthetic/MANIFEST.json`.

## How the main quantities are generated

**Genotype.** HbSS 62%, HbSC 25%, HbS beta zero 6%, HbS beta plus 5%, other 2%, close to the mix reported for adults in UK specialist centres.

**Steady state values.** Haemoglobin around 8.4 g/dL for HbSS and HbS beta zero and around 11 g/dL for HbSC; baseline saturation lower in the severe genotypes. Hydroxyurea in about half of patients with severe genotypes, raising foetal haemoglobin.

**Attendances.** A seasonal Poisson process, about 20% busier in winter, scaled by a lognormal attendance propensity. This gives the long tail of frequent attenders seen in practice: a third of attendances come from people with five or more attendances in the previous year.

**Presentation.** Pain 82%, chest symptoms 6.5%, fever 5%, abdominal pain 2.6%, neurological symptoms 1.2%, priapism 0.6% of male attendances, other 2%.

**Door to analgesia.** Log normal with a median of about 44 minutes, so roughly a quarter of patients receive analgesia within the NICE target of 30 minutes, in keeping with national audit findings that most patients wait longer than the target. Effects on log minutes (the audit must recover these):

| Effect | Value | Ratio |
| --- | --- | --- |
| crowding index, per unit above 0.6 | 0.48 | 1.62 |
| triage category 2 | −0.26 | 0.77 |
| triage category 1 | −0.45 | 0.64 |
| individual plan visible | −0.34 | 0.71 |
| frequent attender | 0.30 | 1.35 |
| night arrival | 0.13 | 1.14 |
| female | 0.08 | 1.08 |
| age 50 and over | −0.04 | 0.96 |

A random effect per site (standard deviation 0.10) and residual noise (0.55) complete the model. 2.8% of patients with pain leave before analgesia. Pethidine is given in 2.5% of attendances at non specialist sites when no plan is visible, a deviation the audit should find.

**Acute chest syndrome.** 36% of chest presentations already have it at arrival. After admission, a latent logistic model sets each admission's risk from genotype, previous episodes, asthma, hydroxyurea, foetal haemoglobin, white cells, haemoglobin fall, opioid intensity, incentive spirometry, fever and saturation gap; the intercept gives about 9% of admissions, within the range reported for adults admitted with a painful crisis. Onset follows a gamma distribution peaking between one and three days after admission, as the BSH guideline describes, and diagnosis follows onset by three to ten hours. In the hours before onset, saturation drifts down and respiratory rate up; after onset both move faster and temperature and heart rate rise, with platelets falling and white cells, CRP and LDH rising in ward bloods. Confounders are added to admissions without acute chest syndrome: transient desaturation (10%), an opioid related low respiratory rate (4.5%) and other infections with fever (7%).

## Evaluation splits

| Split | Definition | Attendances |
| --- | --- | --- |
| Development | sites A to F, 2021 to 2024 | 117,254 |
| Blind, sites | every attendance at sites G and H | 31,590 |
| Blind, period | sites A to F in 2025 | 29,391 |

Patients attend their home site, so the blind sites contain only patients the models never saw.

## Known issues

1. The generator's own structure defines the gold standard for the deterioration model, so performance is optimistic relative to real data, where onset is unobserved and diagnosis is noisy.
2. Door to analgesia is a single number per attendance; real records have missing and inconsistent timestamps.
3. Plans are simplified to an agent, a route, adjuncts and cautions.
4. Ethnicity is not modelled because almost every patient with sickle cell disease in the UK shares African or Caribbean ancestry; the audit examines attendance frequency, plan access, time of arrival, sex, age and site instead.
5. There are no children; the guidance cards and thresholds are for adults.
