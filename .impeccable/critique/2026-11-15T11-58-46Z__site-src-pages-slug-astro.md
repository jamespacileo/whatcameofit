---
target: built claim page
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/openspec-knowledge-cards-94195e/site/src/pages/[slug].astro"
target_fingerprint: "sha256:d1a0d123d639e2febee7a3e48ffd91b3aa9a7563029bae0a696bba636a6e7217"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/openspec-knowledge-cards-94195e/site/src/pages/[slug].astro
timestamp: 2026-11-15T11-58-46Z
slug: site-src-pages-slug-astro
---
Method: dual-agent (A: design review · B: detector + browser overlay)

Target: the built claim page in the page frame (change page-frame), on three published claims at 375, 900 and 1280 pixels wide, from the local preview.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Narrowing the timetable is told only to screen readers; the visible note still says "13 records" |
| 2 | Match system / real world | 3 | "Record" means two things; "4 and 17" has no units |
| 3 | User control and freedom | 3 | No open-all; fold state lost on reload |
| 4 | Consistency and standards | 2 | Four disclosure idioms; Follow appears three times |
| 5 | Error prevention | 3 | Whole-row overlay on trial rows blocks selecting cell text |
| 6 | Recognition rather than recall | 3 | Basis diamond on 12 of 13 records: the preview reads a snapshot made before the narrowed rule |
| 7 | Flexibility and efficiency | 2 | Find-in-page misses folded sections |
| 8 | Aesthetic and minimalist design | 2 | "View trial details here" 12 to 14 times; pages 6,645 to 8,930px at 1280 |
| 9 | Error recovery | 1 | No way to report an error as served locally: no corrections address is set there |
| 10 | Help and documentation | 3 | Nothing says a trial row opens |
| **Total** | | **25/40** | **Acceptable (63%)** |

## Design Specificity Verdict

Grounded in the product: the band pairs the outlet's headline with a status card that marks a place, and the copy carries it. The three-column frame is the generic part and takes room from the content on desktop. Detector: CLI clean; in-page, `.take-why` notes run 81 to 93 characters a line, the bridge sentence leaves one word on its last line, and the outlet's domain is 2.1:1 on the navy band.

## Priority Issues

- **[P1] "The record in brief" collapses between 1157 and about 1300px wide.** The answer column is 7px at 1160 and 26px at 1180. Cause: the question column's fixed 17rem (`.brief summary`) inside the narrower sheet. Fix: `minmax(8rem, 17rem)`, or stack by container width. Command: /impeccable adapt
- **[P1] Desktop is tighter than tablet.** The sheet is 832px wide at 900 but 558 to 670px at 1160 to 1280; the 165px action column holds three pills; trial dates and ids split mid-word. Fix: move the actions into the band or the sheet's head, give the sheet that width, never break dates and ids. Command: /impeccable layout
- **[P2] A trial reached by a link is not marked.** `.trial:target` no longer matches `.trial-group`. Command: /impeccable polish
- **[P2] The outlet's domain fails contrast on the band.** `--muted` on navy, 2.1:1. Command: /impeccable polish
- **[P2] Repetition.** "View trial details here" under every registry line; the same headline twice in a band; near-identical promises from one report. Command: /impeccable distill

## Persona Red Flags

- Jordan: only a 24px chevron says a trial row opens; "Recorded 13", "3 registry records matched" and "No record yet" on one site.
- Casey: an opened trial is 1,134 to 1,699px with no close at its end; each folded heading costs 100px; the sticky chip row takes 65px.
- Sam: 17 to 19 tab stops after the skip link before the sheet; the trial button is named only "135 people"; focus stays on the body after a jump.

## Minor Observations

- The lede runs about 90 characters a line at 900 wide.
- The fold note is outside the button, so 196px of a 670px line is clickable.
- Desktop pills are 31px tall.
- Print is sound in source and has not been seen on paper.

## Questions to Consider

- If 900px reads better than 1280px, what is the left list buying that a chip row does not?
- Should the Promised column exist only for years that have both a promise and a record?
