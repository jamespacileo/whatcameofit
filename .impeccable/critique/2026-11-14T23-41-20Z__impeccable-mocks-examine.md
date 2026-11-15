---
target: examine pattern mocks
total_score: 21
max_score: 36
na_heuristics: 5
p0_count: 0
p1_count: 3
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/openspec-knowledge-cards-94195e/.impeccable/mocks/examine"
timestamp: 2026-11-14T23-41-20Z
slug: impeccable-mocks-examine
---
Method: dual-agent (A: design review · B: detector + browser overlay)

Target: the four mocks in `.impeccable/mocks/examine/` (claim, claim with promise, topic, home).

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | On a phone the current chip in the sticky strip scrolls out of view |
| 2 | Match system / real world | 2 | "Trial registered, place 2 of 6" sits above three finished trials with posted results |
| 3 | User control and freedom | 3 | A pressed status filter has no visible "clear"; no open-all for sections |
| 4 | Consistency and standards | 2 | Share and "Check again later" appear three times each; the left column means two things |
| 5 | Error prevention | n/a | Read-only pages |
| 6 | Recognition rather than recall | 3 | Timeline rows show day and month only |
| 7 | Flexibility and efficiency | 2 | No sort; outside link to #papers lands on a folded section |
| 8 | Aesthetic and minimalist design | 2 | Five grey disclaimer notes; basis diamond on 12 of 12 registry rows |
| 9 | Error recovery | 1 | Empty filter result has no message or reset |
| 10 | Help and documentation | 3 | "It happened" and "Off the path" unexplained |
| **Total** | | **21/36** | **Acceptable (58%)** |

## Design Specificity Verdict

Skeleton is Examine's (band, status card, sticky list, folding sections); content inside is ours (promise pair, gap rows, answers on the line). Detector: 5 CLI `cramped-padding` findings, all false positives. In-page scan: 5 real `line-length` findings on the claim pages (66ch measures 94 to 98 characters in Figtree) and 2 width-dependent stragglers.

## Priority Issues

- **[P1] The band buries the content on a phone.** Sheet starts 1,304px down (1,462px with three reports); six jump pills duplicate a nine-chip sticky strip 1,685px wide with no fade. Fix: drop band pills under 48rem; one report plus "2 more"; fade the strip and keep the current chip in view. Command: /impeccable adapt
- **[P1] The status reads as contradicted by the records.** "No trial with a phase has started" above three finished trials; the explaining sentence was demoted to small grey type. Fix: set it at the meaning line's weight, directly under it. Command: /impeccable clarify
- **[P1] Topic filters fail quietly.** On a phone a pressed status changes rows 760px below; no empty state; no visible clear. Fix: move the status filter into the bar above the table; add "No claim matches" with "Show all". Command: /impeccable harden
- **[P2] Match scores sit where Examine puts grades.** Right-aligned "High match · 100%" beside paper titles reads as a rating. Fix: move into the grey notes line as "Match to this claim: 98%". Command: /impeccable clarify
- **[P2] Folding and table markup lose structure for assistive tech and print.** Heading inside summary; link inside summary; trial cells without column names; missing datetime; silent filtering; folded sections do not print. Fix: heading outside the summary with a button; table roles; live region; open folds in print. Command: /impeccable harden

## Persona Red Flags

- Jordan: "Place 2 of 6"; diamond on every row; "Off the path"; "It happened"; "Very likely in the report · 91%".
- Casey: masthead links 32px, breadcrumb links 23px; 23 of 96 targets under 24px; promise cell in a half column; hover-only rail tooltips.
- Sam (from markup): heading navigation may skip folded sections; trial cells without column names; disabled filter skipped silently; no announcement on filtering.

## Minor Observations

- Six of nine sections open by default; phone page 9,432px.
- Share and "Check again later" three times per claim page.
- Use about 46ch or rem for a 66-character measure.
- No mock for failed, terminated, retracted, no-signal or zero-trial claims.
- Home tabs switch nothing; promise band 702px tall at 1280x900.
- Live summaries state results in the site's own voice; attribute to the report.

## Questions to Consider

- If six of nine sections open by default, what is folding buying?
- On a phone, should the page end after "The record in brief"?
- Does the status card need to be a card?
