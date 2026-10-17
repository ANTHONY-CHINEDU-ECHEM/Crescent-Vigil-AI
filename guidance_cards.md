# Guidance cards

Each card paraphrases one recommendation or finding from a published source. Cards are written in plain words, never copied, and carry the phases of an attendance when they apply and the clinical situations they cover. Numbers that are local choices rather than published recommendations are marked as local protocol parameters and live in `crescent_vigil/config.py`.

Phases: arrival (0 to 30 minutes), early (30 minutes to 2 hours), ward (2 to 24 hours), late (24 to 72 hours), discharge, any.

Sources:
S1  NICE CG143. Sickle cell disease: managing acute painful episodes in hospital. National Institute for Health and Care Excellence, 2012.
S2  Yawn BP, Buchanan GR, Afenyi Annan AN, et al. Management of sickle cell disease: summary of the 2014 evidence based report by expert panel members (NHLBI). JAMA 2014.
S3  Brandow AM, Carroll CP, Creary S, et al. American Society of Hematology 2020 guidelines for sickle cell disease: management of acute and chronic pain. Blood Advances 2020.
S4  Howard J, Hart N, Roberts Harewood M, et al. Guideline on the management of acute chest syndrome in sickle cell disease. British Journal of Haematology 2015.
S5  Sickle Cell Society. Standards for the clinical care of adults with sickle cell disease in the UK, second edition, 2018.
S6  National Confidential Enquiry into Patient Outcome and Death. A Sickle Crisis? 2008.
S7  All Party Parliamentary Group on Sickle Cell and Thalassaemia. No One's Listening: an inquiry into the avoidable deaths and failures of care for sickle cell patients in secondary care, 2021.
S8  NICE NG51. Suspected sepsis: recognition, diagnosis and early management. 2016, updated 2024.
S9  Davis BA, Allard S, Qureshi A, et al. Guidelines on red cell transfusion in sickle cell disease. Part II: indications for transfusion. British Journal of Haematology 2017.
S10 DeBaun MR, Jordan LC, King AA, et al. American Society of Hematology 2020 guidelines for sickle cell disease: prevention, diagnosis, and treatment of cerebrovascular disease in children and adults. Blood Advances 2020.

---

## G001 Analgesia within 30 minutes of presentation
source: S1
phase: arrival
situations: pain
entities: analgesia, door to analgesia, target, 30 minutes

Give the first dose of analgesia within 30 minutes of the person arriving at hospital. Treat an acute painful episode as a medical emergency from the moment of presentation, not from the moment a doctor first sees the patient.

## G002 One hour standard in the ASH guideline
source: S3
phase: arrival, early
situations: pain
entities: analgesia, door to analgesia, target, one hour, 60 minutes

The ASH 2020 pain guideline recommends rapid assessment and administration of analgesia within one hour of arrival at the emergency department, followed by frequent reassessment. Where a national target is stricter, as the 30 minute NICE target is in England, the stricter target governs local practice.

## G003 Individualised care plans come first
source: S3, S5
phase: arrival, early
situations: pain, plan
entities: care plan, individualised, agent, route, dose

When a patient has an individualised pain plan, use the agent, route and dose written in that signed plan rather than a generic protocol. Plans are written by the specialist team who know the patient's previous responses, and following them shortens the time to effective relief.

## G004 Ask what has already been taken
source: S1
phase: arrival
situations: pain
entities: analgesia taken at home, history, assessment

Ask what analgesia the person has already taken for this episode, including when and how much, before choosing the first dose. Most people try their own analgesia at home before coming to hospital.

## G005 Believe and assess the pain
source: S1, S7
phase: arrival, any
situations: pain, equity
entities: pain score, assessment, trust, stigma

Assess pain with a validated score and accept the person's own report of how severe it is. The parliamentary inquiry found that patients were often disbelieved, labelled as drug seeking and left waiting, and that these attitudes contributed to avoidable harm.

## G006 Strong opioid for severe pain
source: S1
phase: arrival
situations: pain
entities: strong opioid, severe pain, morphine, diamorphine, bolus

Offer a bolus of a strong opioid, such as morphine or diamorphine, to people with severe pain and to those with moderate pain who have not had relief from weaker analgesia. The exact dose and route come from the individual plan or the prescriber, not from this system.

## G007 Never use pethidine
source: S1
phase: any
situations: pain, safety
entities: pethidine, avoid, contraindicated

Do not use pethidine to treat an acute painful sickle cell episode. Its metabolite accumulates and can cause seizures, and safer strong opioids are available.

## G008 Paracetamol as an adjunct
source: S1
phase: arrival, early, ward
situations: pain
entities: paracetamol, adjunct

Offer regular paracetamol alongside opioid analgesia unless it is contraindicated. Adjuncts reduce the total opioid needed.

## G009 NSAIDs as an adjunct unless contraindicated
source: S1
phase: arrival, early, ward
situations: pain, renal
entities: NSAID, ibuprofen, adjunct, renal impairment, contraindication

Offer a non steroidal anti inflammatory drug as an adjunct unless it is contraindicated, for example by renal impairment. Check the individual plan, which records kidney problems and other cautions.

## G010 Reassess pain every 30 minutes until relief
source: S1
phase: arrival, early
situations: pain, monitoring
entities: reassessment, 30 minutes, pain score, sedation

Reassess pain every 30 minutes until satisfactory relief is reached, and then at least every four hours. Each reassessment records the pain score, sedation level and vital signs.

## G011 Monitoring after opioids
source: S1
phase: arrival, early, ward
situations: pain, monitoring, hypoventilation
entities: respiratory rate, sedation, oxygen saturation, vital signs, monitoring

After giving opioids, monitor pain, sedation, vital signs, respiratory rate and oxygen saturation every 30 minutes until pain is controlled and the patient is stable, then at least every four hours. Escalate if sedation deepens or the respiratory rate falls.

## G012 Opioid related respiratory depression
source: S1, S6
phase: early, ward, late
situations: hypoventilation, safety
entities: respiratory rate, low, sedation, naloxone, opioid toxicity

A low respiratory rate or increasing sedation after opioids suggests opioid toxicity and needs immediate review, including whether to hold further doses and whether naloxone is needed under the local opioid safety policy. The national enquiry found inadequate monitoring of patients receiving opioids.

## G013 Second dose and escalation
source: S1, S3
phase: early
situations: pain
entities: second dose, escalation, inadequate relief, specialist

If pain is not controlled after the first dose, give further doses in line with the individual plan and involve the haematology team early. Do not wait for the next routine review when a patient remains in severe pain.

## G014 Ketamine as a specialist adjunct
source: S3
phase: ward
situations: pain, refractory
entities: ketamine, adjunct, refractory pain, specialist

For pain that remains refractory to opioids, the ASH guideline suggests a low dose ketamine infusion as an adjunct, used only with specialist input and in a setting able to monitor it.

## G015 Inform haematology on admission
source: S5
phase: early, ward
situations: plan, admission
entities: haematology, specialist team, admission, inform

Tell the specialist haematology team when a person with sickle cell disease is admitted. Specialist review within the first day improves the management of pain and complications.

## G016 Hydration
source: S2
phase: early, ward
situations: pain, fluids
entities: hydration, fluids, oral, intravenous, fluid overload

Encourage oral fluids and give intravenous fluids only if the patient cannot drink enough, watching for fluid overload, which can worsen breathing problems.

## G017 Do not transfuse uncomplicated pain
source: S2, S9
phase: any
situations: pain, transfusion
entities: transfusion, uncomplicated, vaso occlusive, not indicated

Blood transfusion is not indicated for an uncomplicated painful episode. Consider transfusion only for specific complications, such as acute chest syndrome, stroke or severe acute anaemia, after discussion with haematology.

## G018 Incentive spirometry while awake
source: S2, S4
phase: ward, late
situations: pain, prevention, chest
entities: incentive spirometry, prevention, acute chest syndrome, chest pain, back pain

Encourage incentive spirometry while awake for patients admitted with a painful episode, particularly with chest or back pain. Regular deep breathing reduces the risk of developing acute chest syndrome.

## G019 Acute chest syndrome definition
source: S4
phase: any
situations: chest
entities: acute chest syndrome, definition, new infiltrate, chest X ray, fever, respiratory symptoms

Acute chest syndrome is an acute illness with fever or respiratory symptoms together with a new pulmonary infiltrate on a chest X ray. It often develops during an admission for pain rather than at presentation.

## G020 Acute chest syndrome often develops after admission
source: S4, S2
phase: ward, late
situations: chest, deterioration
entities: acute chest syndrome, after admission, 24 to 72 hours, vigilance

Many episodes of acute chest syndrome start one to three days after admission for a painful episode. Keep watching for new chest pain, cough, fever, a rising respiratory rate or falling oxygen saturation throughout the stay.

## G021 Falling oxygen saturation
source: S4
phase: early, ward, late
situations: chest, deterioration
entities: oxygen saturation, falling, baseline, chest X ray, review

A fall in oxygen saturation from the patient's usual level is an early warning of acute chest syndrome. Review the patient promptly, examine the chest and consider a chest X ray and blood gases.

## G022 Chest symptoms at presentation
source: S4
phase: arrival
situations: chest
entities: chest pain, breathlessness, cough, chest X ray, presentation

Patients presenting with chest pain, breathlessness or cough need a chest X ray and oxygen saturation assessment early, and the haematology team should be told, because acute chest syndrome may already be present.

## G023 Treating acute chest syndrome
source: S2, S4
phase: any
situations: chest, treatment
entities: antibiotics, cephalosporin, macrolide, oxygen, analgesia, treatment

Treat acute chest syndrome with antibiotics that cover common and atypical organisms, such as an intravenous cephalosporin with a macrolide, supplemental oxygen to the target set by the treating team, careful analgesia and incentive spirometry.

## G024 Transfusion in acute chest syndrome
source: S4, S9
phase: any
situations: chest, transfusion
entities: transfusion, exchange transfusion, simple transfusion, severe, deterioration

Transfusion is an important treatment for acute chest syndrome. Simple transfusion is used for moderate illness and exchange transfusion for severe or worsening illness, decided with the haematology team.

## G025 Escalation to critical care
source: S4
phase: ward, late
situations: chest, deterioration, critical care
entities: critical care, escalation, hypoxia, respiratory failure, outreach

Involve critical care early when acute chest syndrome is progressing, oxygen needs are rising or the patient is tiring. Early escalation is safer than rescue after respiratory failure.

## G026 Opioids and acute chest syndrome
source: S4, S6
phase: ward, late
situations: chest, hypoventilation
entities: opioid, hypoventilation, sedation, acute chest syndrome, balance

Adequate analgesia helps breathing by reducing splinting, but excessive opioid sedation causes hypoventilation, which can contribute to acute chest syndrome. Balance pain relief against sedation and keep monitoring the respiratory rate.

## G027 Fever is an emergency
source: S2
phase: arrival, any
situations: fever, infection
entities: fever, 38.5, blood culture, antibiotics, urgent

People with sickle cell disease and a temperature of 38.5 degrees or above need urgent evaluation, including a full blood count, reticulocyte count and blood cultures, and prompt parenteral antibiotics, because reduced splenic function raises the risk of serious infection.

## G028 Local fever flag
source: local protocol parameter
phase: any
situations: fever, infection
entities: fever, 38.0, local threshold, sepsis screen

This service flags a temperature of 38.0 degrees or above for a sepsis screen, which is lower than the 38.5 degree threshold in the NHLBI report. The local threshold is a configuration setting and can be changed in the protocol file.

## G029 Sepsis recognition
source: S8
phase: arrival, early, ward
situations: fever, infection, sepsis
entities: sepsis, risk stratification, antibiotics, lactate, senior review

Use structured sepsis risk assessment for anyone with suspected infection, and give antibiotics within the time set by the risk level. People with sickle cell disease have functional hyposplenism and are at higher risk.

## G030 Neurological symptoms
source: S2, S10
phase: any
situations: neuro, stroke
entities: stroke, neurological deficit, weakness, speech, imaging, emergency

New weakness, speech disturbance, severe headache, seizure or reduced consciousness may be a stroke and need emergency assessment, urgent brain imaging and immediate haematology involvement.

## G031 Exchange transfusion for acute stroke
source: S2, S10
phase: any
situations: neuro, stroke, transfusion
entities: exchange transfusion, stroke, urgent, haematology

For acute stroke in sickle cell disease, urgent exchange transfusion is the standard treatment, arranged with haematology alongside the usual stroke pathway.

## G032 Priapism
source: S2
phase: arrival, any
situations: priapism
entities: priapism, four hours, urology, aspiration, emergency

Priapism lasting four hours or more needs urgent urology review for aspiration and irrigation, with analgesia and haematology involvement. Ask about the duration at triage because delay increases the risk of lasting damage.

## G033 Acute anaemia
source: S9, S2
phase: any
situations: anaemia, abdominal
entities: haemoglobin, fall, steady state, reticulocytes, transfusion

A haemoglobin well below the patient's steady state needs explanation. Check the reticulocyte count: a low count suggests a transient red cell aplasia, and a high count with an enlarging spleen suggests splenic sequestration.

## G034 Local haemoglobin flag
source: local protocol parameter
phase: any
situations: anaemia
entities: haemoglobin, 2 g/dL, steady state, local threshold

This service flags a haemoglobin 2 g/dL or more below the recorded steady state. The value is a configuration setting, chosen to match common UK hospital protocols.

## G035 Splenic sequestration
source: S2
phase: any
situations: abdominal, anaemia
entities: splenic sequestration, enlarging spleen, left upper quadrant pain, transfusion, emergency

Acute splenic sequestration presents with a rapidly enlarging spleen and a sharp fall in haemoglobin and can cause shock. It is more common in children and in people with HbSC or HbS beta thalassaemia, and needs urgent haematology input.

## G036 Abdominal pain
source: S2
phase: arrival, early
situations: abdominal
entities: abdominal pain, surgical causes, gallstones, sequestration, assessment

Abdominal pain may be a painful episode but can also be gallstones, sequestration, infection or a surgical emergency. Examine carefully and seek a surgical opinion when the picture does not fit an ordinary crisis.

## G037 Haematology review within one day
source: S5
phase: ward
situations: admission, plan
entities: specialist review, haematology, within 24 hours

Every adult admitted with sickle cell disease should be reviewed by a specialist haematology team, ideally within the first day, and the team should be able to see the individual care plan.

## G038 Plans must be accessible
source: S5, S7
phase: arrival
situations: plan, equity
entities: care plan, access, electronic record, emergency department

Individual care plans only help if emergency staff can see them. The national standards and the parliamentary inquiry both call for plans that are available in the emergency department record at the time of arrival.

## G039 Review plans regularly
source: S5
phase: any
situations: plan
entities: care plan review, annual, out of date

Individual plans should be reviewed regularly, at least yearly, so that the recorded agent, route and cautions reflect the patient's current needs. An out of date plan should still be read but checked with haematology.

## G040 Local plan review flag
source: local protocol parameter
phase: any
situations: plan
entities: care plan review, 12 months, stale

This service marks a plan as due for review when it was last reviewed more than 12 months ago. The plan is still shown first; the flag prompts a check with haematology.

## G041 Delays and stigma
source: S7
phase: any
situations: equity
entities: delay, stigma, drug seeking, frequent attender, avoidable harm

The parliamentary inquiry reported long waits for pain relief and repeated assumptions that patients were drug seeking, particularly for people who attend often. Frequent attendance reflects disease severity and should never lower the priority of pain relief.

## G042 National enquiry findings
source: S6
phase: any
situations: equity, monitoring
entities: national enquiry, monitoring, opioid, deaths, care quality

The national enquiry into deaths of people with sickle cell disease found delays in analgesia, inadequate monitoring after opioids and failures to recognise deterioration, and recommended better observation and earlier specialist involvement.

## G043 Communication and partnership
source: S5, S7
phase: any
situations: equity, communication
entities: communication, patient expertise, involvement, respect

People with sickle cell disease often know their condition well. Involve them in decisions about their analgesia and listen to what has worked before.

## G044 Observations four hourly when stable
source: S1
phase: ward, late
situations: monitoring
entities: observations, four hourly, stable

Once pain is controlled and the patient is stable, continue observations at least every four hours, including oxygen saturation and respiratory rate, for the rest of the admission.

## G045 Early warning scores
source: S8
phase: early, ward, late
situations: deterioration, monitoring
entities: early warning score, escalation, deterioration

Use the hospital's early warning score with every set of observations and follow the escalation policy, while remembering that the patient's own baseline oxygen saturation may be lower than the general population.

## G046 Baseline oxygen saturation
source: S4
phase: any
situations: chest, monitoring
entities: baseline, oxygen saturation, steady state, comparison

Some people with sickle cell disease have a lower steady state oxygen saturation. Compare readings with the patient's own baseline as well as with fixed thresholds.

## G047 Chest X ray when chest signs appear
source: S4
phase: ward, late
situations: chest
entities: chest X ray, new signs, crackles, reduced air entry

When new chest signs, cough or falling saturation appear during an admission, arrange a chest X ray promptly. Clinical signs can lag behind the radiological changes.

## G048 Blood tests at presentation
source: S2, S1
phase: arrival, early
situations: pain, assessment
entities: full blood count, reticulocyte count, blood tests, baseline comparison

At presentation take a full blood count and reticulocyte count and compare them with the patient's steady state values. Do not delay analgesia while waiting for results.

## G049 Do not delay analgesia for tests
source: S1
phase: arrival
situations: pain
entities: delay, tests, analgesia first

Do not delay the first dose of analgesia while waiting for investigations, a doctor's review or a bed. Analgesia can be started from a patient group direction or nurse led protocol where available.

## G050 Nurse initiated analgesia
source: S3, S5
phase: arrival
situations: pain, equity
entities: nurse initiated, protocol, patient group direction, faster

Nurse initiated analgesia under an agreed protocol shortens the time to the first dose, especially when the department is crowded.

## G051 Crowding and delays
source: S7
phase: arrival
situations: equity
entities: crowding, delay, priority, emergency department

Department crowding is a major cause of delayed pain relief. A painful sickle cell episode should be prioritised at triage regardless of how busy the department is.

## G052 Discharge planning
source: S1, S5
phase: discharge
situations: discharge
entities: discharge, analgesia supply, follow up, return advice

Before discharge, make sure pain is controlled on oral analgesia, the patient has a supply and clear advice on when to return, and that the specialist team is informed for follow up.

## G053 Hydroxyurea review
source: S2
phase: discharge
situations: discharge, prevention
entities: hydroxyurea, frequent crises, specialist review

People with frequent painful episodes or previous acute chest syndrome should be offered review for hydroxyurea by the specialist team, as it reduces crises and chest syndrome.

## G054 Learning from each admission
source: S5
phase: discharge
situations: plan, discharge
entities: care plan update, learning, admission review

After each admission, update the individual plan with what worked and what did not, so the next attendance starts from better information.

## G055 Pain that does not fit
source: S1
phase: early, ward
situations: pain, assessment
entities: atypical pain, alternative diagnosis, red flags

If the pain is different from the patient's usual crises, or does not respond as expected, look for another cause, including acute chest syndrome, infection, avascular necrosis, sequestration or a surgical problem.

## G056 Avascular necrosis
source: S2
phase: ward
situations: pain
entities: avascular necrosis, hip, shoulder, persistent pain, imaging

Persistent hip or shoulder pain may be avascular necrosis rather than a typical crisis and needs imaging and specialist review when it does not settle.

## G057 Pain relief and breathing
source: S4
phase: ward
situations: chest, pain
entities: splinting, chest wall pain, breathing, analgesia

Good analgesia for chest wall and back pain helps prevent splinting and shallow breathing, which lower the risk of acute chest syndrome.

## G058 Hypoxia and oxygen
source: S4
phase: any
situations: chest, oxygen
entities: oxygen, hypoxia, target saturation, treating team

Give supplemental oxygen when saturation is below the target set for the patient, and investigate why. Do not use oxygen to mask a deterioration without finding its cause.

## G059 Children are different
source: S2
phase: any
situations: scope
entities: children, paediatric, scope

This service is designed for adult emergency departments. Children with sickle cell disease follow paediatric pathways with different thresholds for fever, sequestration and stroke.

## G060 Pregnancy
source: S5
phase: any
situations: scope, pregnancy
entities: pregnancy, obstetric, haematology, joint care

Pregnant women with sickle cell disease presenting in pain need joint obstetric and haematology care. The general pathway in this service does not replace that.

## G061 Deterioration model alerts
source: local protocol parameter
phase: ward, late
situations: deterioration, chest
entities: deterioration model, alert, acute chest syndrome, 24 hours, review

The Crescent Vigil deterioration model estimates the chance that acute chest syndrome will be diagnosed in the next 24 hours. An alert prompts a bedside review and a check of the chest, oxygen saturation and respiratory rate; it never replaces clinical judgement.

## G062 What the system will not do
source: local protocol parameter
phase: any
situations: safety, scope
entities: dose, prescribing, limits, clinician responsibility

This system does not calculate or suggest drug doses, does not prescribe and does not replace the clinician. Doses always come from the signed individual plan or the responsible prescriber.

## G063 Safeguarding and mental health
source: S5
phase: any
situations: safety, crisis
entities: mental health, distress, self harm, safeguarding, liaison psychiatry

If a patient expresses thoughts of self harm or appears in crisis, follow the hospital's mental health and safeguarding pathway and involve the liaison psychiatry team, while continuing to treat pain.

## G064 Respecting refusal and preferences
source: S5
phase: any
situations: communication
entities: preferences, consent, route, needle phobia, venous access

Respect the patient's stated preferences about route, for example subcutaneous rather than intravenous when venous access is difficult, which is often recorded in the plan.
