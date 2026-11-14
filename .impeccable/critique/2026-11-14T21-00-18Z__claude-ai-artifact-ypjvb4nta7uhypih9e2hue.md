---
target: mockup boards F-H v2 (the record in brief, six questions)
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "url:https://claude.ai/artifact/YPJVB4nTa7UHypiH9E2huE"
timestamp: 2026-11-14T21-00-18Z
slug: claude-ai-artifact-ypjvb4nta7uhypih9e2hue
closed: true
---
Method: dual-agent (A: design review · B: detector + browser evidence). Target: boards F, G, H, second versions ("The record in brief", six fixed questions in two groups). Both assessments saw the boards rendered from a local server. Overlay ran on all three.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of status | 3 | Two dates, two verbs: "Record read 13 Nov", "Registries last checked 14 Nov" |
| 2 | Match real world | 3 | "phase", "posted", "regulator" unexplained; "since" is false here |
| 3 | User control | 3 | Native disclosure works; no open-all |
| 4 | Consistency | 2 | Boards disagree on default-open rows, link form and digest content; a third confidence vocabulary on the page |
| 5 | Error prevention | 2 | "1 of 3", "No trial with a phase has started" and "since" invite wrong readings |
| 6 | Recognition | 3 | "The largest trial" is never named in the closed rows |
| 7 | Flexibility | 2 | No per-row anchors; the results link is buried in an opened panel |
| 8 | Minimalist | 3 | The provenance sentence is heavy |
| 9 | Error recovery | 3 | The withheld-reading fallback is honest and clear |
| 10 | Help | 3 | "How an answer is made" only at the foot |
| **Total** | | **27/40** | **Acceptable** |

## Design specificity verdict

Authored for this product, not a stock FAQ: the answer sits in the summary, places are fixed, absence is worded "None on record", and every opened answer names its record. The generic residue is the shell (chevron rows, panels in the digest's tint). The weakness is wording, where three lines break the product's exactness.

Detector: `flat-type-hierarchy` advisory on all three files (desktop 17/18/22/27, largest step 1.23; phone 16/17/20/23, 1.18; target 1.25). `cramped-padding` on Brief and BriefPhone did not reproduce in the overlay and has no line; false positive. Measured clean: no result values or "p <" in any page; phone targets all 44px or more; no overflow at 390 or 320; 27 of 27 disclosures toggle and the chevron turns; focus ring 3px navy; lowest contrast 6.85:1; no dead links.

## Priority issues

- **[P1] "What has been recorded since" is false (all boards).** Results are from Jun 2026 and the last completion Mar 2023; the news report is Nov 2026. Fix: "Where the records stand now". Command: /impeccable clarify
- **[P1] The digest bridge still reads as a contradiction (F, G).** "No trial with a phase has started" beside three finished trials with results. Fix: "3 trials are on record and all have finished. The registry gives none a phase." Command: /impeccable clarify
- **[P1] Row 2 overstates the records (F).** "Yes, in 1 of 3 trials" implies two had no comparison; NCT04731714 is randomised and triple-blind. "Nobody taking part… was told who had which" cannot hold for a no-device group. Fix: "Stated in 1 of 3 records"; opened text limited to what the record states. Command: /impeccable clarify
- **[P2] A date breaks across lines** ("5 Mar / 2023") on all boards, against DESIGN.md. Fix: non-breaking dates; widen the answer column. Command: /impeccable layout
- **[P2] Rows that open to nothing.** Phone rows 1, 2, 4, 5, 6; desktop 4 to 6; 14 of 15 on the states board. Fix: draw every opened panel, or no chevron where nothing opens. Command: /impeccable harden

## Persona red flags

- Jordan (first-timer): "regulator", "posted to the registry", "phase" undefined; "very likely · [SCORE]%" of what?
- Casey (phone): presses "Approved by a regulator?" and gets nothing; the results link needs a press, then a scroll.
- Relative of a patient: "135 people in the largest" with no result; the section closes on "None on record" twice, with the only route to results inside row 3.

## Minor observations

- The live page already says "not yet been checked by a person" above; the intro repeats it, and the boards omit that notice and the follow offer.
- "A score of symptoms" drops "change in".
- "Read by a model from those words": "those" has no clear antecedent.
- No-trial state: the second group is a single "None on record" row.
- The approved answer names no regulator.
- The facts row on F lacks "Records of studies".
- Desktop shows two rows open, phone one; the spec implies closed.
- Group names are barely larger than body text.

## Questions to consider

- With three named papers on record, is "Published in a journal?" the missing row a lay reader would recognise?
- If results are posted, why is the brief's only route to them inside row 3?
- Should "Yes," lead any answer, given it makes Yes/None a scoreboard?
