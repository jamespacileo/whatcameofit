---
target: mockup boards A-E (skimmable claim page ideas)
total_score: 21
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 3
target_identity: "url:https://claude.ai/artifact/YPJVB4nTa7UHypiH9E2huE"
timestamp: 2026-11-14T20-23-42Z
slug: claude-ai-artifact-ypjvb4nta7uhypih9e2hue
---
Method: dual-agent (A: design review · B: detector + browser evidence). Target: mockup boards A–E on the design canvas. Neither agent saw the rendered canvas (sign-in wall); both worked from source. No overlay.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of status | 3 | "Trial registered, Place 2 of 6" sits above "3 trials, all completed, results posted" |
| 2 | Match real world | 2 | "sham", "quadruple-blind", "YGTSS-R", "p < 0.02", "Rule ·", unitless −7.13 |
| 3 | User control | 2 | Filter chips lack "show all"; phone bar has no way back up |
| 4 | Consistency | 2 | Status gloss differs A vs C; dark pill is a jump link in A and a selected filter in D; dashed border now means unchecked, promised and "limits" |
| 5 | Error prevention | 2 | Numbers without scale invite misreading; static chips look pressable |
| 6 | Recognition | 3 | Counts on section links work |
| 7 | Flexibility | 2 | D pages 84 claims four at a time |
| 8 | Minimalist | 2 | "3 trials" about six times on A; "not a verdict, not advice" on four boards |
| 9 | Error recovery | 1 | No empty state drawn: 0 trials, no note passing its check, filter with no match |
| 10 | Help | 3 | Links for phase and p value; none for sham or blinded |
| **Total** | | **21/40** | **Acceptable** |

## Design specificity verdict

Mixed. C's "Quick answers" and E's per-note source line are authored for this product. A's and E's two-column solid/hollow blocks are pros/cons cards. B's 30px result tiles are dashboard hero metrics. B and D spread about 25 tint chips where DESIGN.md keeps tint for the topic chip. D swaps the index table for generic cards and loses the amber promise column.

Detector: 2 findings, both `cramped-padding` on Main.dc.html and Phone.dc.html at line 0 (unlocated); likely false positives, the masthead centres text by flex. Trials, Home and Notes clean. Contrast passes everywhere (lowest 6.40:1).

## Priority issues

- **[P0] Polarity headings are a verdict (E; A's "Review style").** A null result would move a note to "limits", so the columns grade the treatment; −7.13 under "strengthens" with p < 0.02 reads "it works"; "Why to be careful" is advice. Fix: one list grouped by kind of fact ("How the trials were set up", "What was posted", "What the records do not cover"); the results note leaves any valenced group. If polarity stays, it needs an ADR and a symmetric rule. Command: /impeccable shape
- **[P1] Results amplified without scale (B, E).** 30px figures outrank the 27px status; no scale range or direction. Fix: body-size tabular rows with the scale's range and what a fall means. Command: /impeccable quieter
- **[P1] "Not on record" holds things on record (A).** "Two trials were small", "one had no comparison group"; "small" judges; with 0 trials the left box is empty. Fix: absences only, sizes as numbers, draw the 0-trial and approved cases. Command: /impeccable harden
- **[P1] Three summary systems (A, C, E).** Digest, At a glance, Quick answers and Notes tell the same facts; 5 of 8 cognitive-load checks fail. Fix: ship one; C's rows at every width with E's source line on demand. Command: /impeccable distill
- **[P2] "Read by a model" only on the limits side (E).** Caveats look like guesses; a bare score reads as a rating of the trial. Fix: the existing "Very likely in the record · 92%" disclosure, source type at equal weight on every note. Command: /impeccable clarify

## Persona red flags

- Jordan (first-timer): cannot tell "Rule" from "Read by a model"; "Place 2 of 6" conflicts with completed trials; presses B's chips and nothing happens.
- Casey (phone): sticky bar may collide with Safari's toolbar; Follow, Share and masthead links missing on C; quick answers do not link to the trials.
- Relative of a patient: reads "strengthens" plus p < 0.02 as "ask the doctor for this"; bold "21 of 27 planned to continue" reads as endorsement; C ends on the anecdote; bold "No trial has run since March 2023" lands as "abandoned".

## Minor observations

- "39 people in each group, of 135" hides three groups (117 analysed); "200 enrolled in all" sums across trials.
- D cards 3–4 lose the quoted outlet title; "Show claims with… No trial found" does not parse.
- "Earliest paper" and "From an institution" tags rank papers.
- A drops the unchecked notice and the latest-record date.
- The inline "How one note is made" strip belongs in a popover.
- Semantics: no ul/li/dl, no aria-current or aria-pressed, D tabs are spans, Trials and Notes lack an h1, 12px labels on C, several desktop links under 24px tall.

## Questions to consider

- If every note lost its column, would the block still be worth reading?
- Why does a claim with three completed trials and posted results still read "Trial registered"?
- Would you publish the −7.13 note if the figures were reversed?
