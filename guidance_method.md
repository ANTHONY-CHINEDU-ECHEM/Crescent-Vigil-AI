# How the guidance corpus was written

The copilot cites 64 guidance cards in `knowledge/guidance_cards.md`. Each card states one recommendation or finding in plain words, with:

* `source`: one or more of ten published sources, listed at the top of the file;
* `phase`: when in an attendance the card applies (arrival, early, ward, late, discharge or any);
* `situations`: the clinical situations it covers (pain, chest, fever, plan, equity and so on);
* `entities`: the terms a clinician would use when asking about it.

## Rules followed

1. **Paraphrase, never copy.** No sentence reproduces a source's wording. Cards describe what a source recommends, not how it says it.
2. **One idea per card.** Retrieval works better and citations are more precise when a card makes one point.
3. **No doses.** Where a source gives doses, the card names the class of drug and points to the individual plan or the prescriber.
4. **Local choices are labelled.** Thresholds that differ between sources or are set locally (the 38.0 degree fever flag, the 2 g/dL haemoglobin fall, the 12 month plan review flag, the alert threshold) are cards whose source is `local protocol parameter`, and the value lives in `config.py`. Where sources differ, both views are stated: card G001 gives the NICE 30 minute target and card G002 the ASH one hour standard, and says the stricter target governs practice in England.
5. **Scope is explicit.** Cards G059 and G060 say that children and pregnancy are outside the pathway, and the guard routes such questions to them.

## Sources

| Code | Source |
| --- | --- |
| S1 | NICE CG143, sickle cell disease: managing acute painful episodes in hospital (2012) |
| S2 | NHLBI expert panel report, summarised in JAMA (2014) |
| S3 | ASH 2020 guidelines: management of acute and chronic pain |
| S4 | BSH guideline on the management of acute chest syndrome (2015) |
| S5 | Sickle Cell Society, standards for the clinical care of adults with sickle cell disease in the UK (2018) |
| S6 | NCEPOD, A Sickle Crisis? (2008) |
| S7 | APPG on Sickle Cell and Thalassaemia, No One's Listening (2021) |
| S8 | NICE NG51, suspected sepsis (2016, updated 2024) |
| S9 | BSH guidelines on red cell transfusion in sickle cell disease, part II (2017) |
| S10 | ASH 2020 guidelines: cerebrovascular disease |

## Held out questions

`knowledge/eval_questions.txt` holds 174 questions written the way a busy clinician types: short, informal, sometimes with abbreviations (sats, ACS, IV, NEWS). Each lists the card or cards that answer it and, where timing matters, the minute since arrival. For every card the first two questions are development questions and the third is blind. None are indexed.

## Limitations

The cards reflect the sources as published; guidance changes and a clinical deployment would need a named owner to keep them current. Cards were written by one author and have not been reviewed by a haematologist.
