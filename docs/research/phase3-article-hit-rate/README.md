# Phase 3 trials: how many have news coverage

A sample taken on 2026-11-14 to size a registry-first backfill: start from a trial, look for the news that reported it. It informed the change `openspec/changes/backfill-work-ledger`.

## Registry sizes on the day

| Registry | Slice | Count |
| --- | --- | --- |
| ClinicalTrials.gov | all studies | 611,771 |
| ClinicalTrials.gov | interventional, drug or biological | 224,043 |
| ClinicalTrials.gov | phase 2 or 3, drug or biological | 117,839 |
| ClinicalTrials.gov | phase 3, drug or biological (the sampling frame) | 43,320 |
| EU CTIS | all trials | 12,847 |
| EU Clinical Trials Register (EudraCT, closed to new trials) | all trials | 44,416 |

## Method

- **Sample:** 200 trials drawn uniformly at random (seed 20261114) from the 43,320 phase 3 interventional trials of a drug or biological.
- **Search:** up to two web searches per trial for the intervention and the indication, judged from result titles and outlets only. No article was opened.
- **Levels:** `news` (a general, health or clinical trade outlet reports the intervention for the indication), `press_only` (only company releases or newswire copies), `none`.
- **`about_trial`:** the best article is about that trial, not only the same intervention and indication.

## Result

173 of the 200 trials were searched. The other 27 were not: the search allowance of 200 calls ran out.

| Measure | Trials | Rate | 95% interval |
| --- | --- | --- | --- |
| A news article on the intervention for the indication | 53 of 173 | 31% | 24 to 38% |
| A news article or a press release | 57 of 173 | 33% | 26 to 40% |
| A news article about that trial | 28 of 173 | 16% | 11 to 22% |

By lead sponsor: industry 40 of 110 (36%), other 12 of 54 (22%).

## Limits

- 146 of the 173 searched trials had one search, not two, so the rates are likely low.
- Levels were judged from titles and outlets. `about_trial` is a best guess.
- Most `news` results were clinical trade press (healio.com, onclive.com and similar). General news outlets were rare among the best results, and the share was not measured.
- Counting onclive, mdedge, biospace and healio as news is a judgement.
- The search tool covers the United States only.
- An attempt to use the GDELT live interface failed: it refused every request from this address with "too many requests".

## Files

- `sample.json`: the 200 trials with the registry fields used (title, status, start date, sponsor class, phases, conditions, interventions), re-read from ClinicalTrials.gov on 2026-11-14.
- `results.json`: one row per trial in the same order. `searched` is false for the 27 that were not reached; their other fields are empty. `best` holds a title, an outlet domain and an address. No article text is stored.
