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
- **Search:** up to two web searches per trial for the intervention and the indication, the second worded differently from the first, judged from result titles and outlets only. No article was opened.
- **Levels:** `news` (a general, health or clinical trade outlet reports the intervention for the indication), `press_only` (only company releases or newswire copies), `none`.
- **`about_trial`:** the best article is about that trial, not only the same intervention and indication.

## Result

All 200 trials were searched, in two passes on 2026-11-14. The first pass reached 173 trials, most with one search, and found news for 53 (31%). The second pass searched the 27 trials not reached and gave a second, differently worded search to those where the first found no news.

| Measure | Trials | Rate | 95% interval |
| --- | --- | --- | --- |
| A news article on the intervention for the indication | 104 of 200 | 52% | 45 to 59% |
| A news article or a press release | 108 of 200 | 54% | 47 to 61% |
| A news article about that trial | 40 of 200 | 20% | 15 to 26% |

The second search mattered: 35 trials moved to `news` on it. A single search undercounts by a wide margin.

| Slice | Trials with news | Rate |
| --- | --- | --- |
| Lead sponsor: industry | 82 of 126 | 65% |
| Lead sponsor: other | 19 of 65 | 29% |
| Started before 2010 | 34 of 61 | 56% |
| Started 2010 to 2016 | 30 of 54 | 56% |
| Started 2017 to 2022 | 27 of 49 | 55% |
| Started 2023 or later | 13 of 36 | 36% |

### Which outlets

The best article found for each of the 104 trials, by the outlet kinds in `pipeline/src/thenwhat/backfill/outlet_kinds.py`:

| Outlet kind | Trials |
| --- | --- |
| Health or clinical trade press | 84 |
| General news | 11 |
| On no list | 9 |

So about one trial in twenty had a general news outlet as its best result (11 of 200); the rest of the coverage found was trade and specialist press. This counts one article per trial, the one the searcher judged best, so a trial whose best result was a trade article may also have general coverage that was not recorded. The outlet list was extended with the trade titles this sample turned up.

## Limits

- Levels were judged from result titles, outlets and the search tool's own summaries. No article was opened. `about_trial` is a best guess, and several were matched to the trial by sponsor or indication only.
- About half of the `news` results are about the intervention for the indication in general, or about another trial of it, not about the sampled trial.
- Some `news` results are trade titles that often repost company announcements (BioSpace, news-medical.net, PharmaTimes, Ophthalmology Times). Where the title was the company's own announcement it was counted as `press_only`.
- 53 trials had one search only, mostly those where the first search found news.
- "None" means not seen in one or two searches, not that no coverage exists. Results were often crowded with registry mirror pages.
- The search tool covers the United States only.
- An attempt to use the GDELT live interface failed: it refused every request from this address with "too many requests".

## Files

- `sample.json`: the 200 trials with the registry fields used (title, status, start date, sponsor class, phases, conditions, interventions), re-read from ClinicalTrials.gov on 2026-11-14.
- `results.json`: one row per trial in the same order, after both passes. `searches` is how many searches the trial had. `best` holds a title, an outlet domain and an address. No article text is stored.
