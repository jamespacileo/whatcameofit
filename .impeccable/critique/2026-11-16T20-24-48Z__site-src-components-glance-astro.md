---
target: At a glance section
total_score: 26
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/at-glance-section-variants-e35890/site/src/components/Glance.astro"
target_fingerprint: "sha256:7f0e41bba97be87bbbaa4dfa87ab8fced083b30c02664269c937e7624583cf22"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/at-glance-section-variants-e35890/site/src/components/Glance.astro
timestamp: 2026-11-16T20-24-48Z
slug: site-src-components-glance-astro
---
Method: dual-agent (A: design review · B: detector + browser evidence)

## Design Health Score
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | Row reached from band: tint only, no ring |
| 2 | Match System / Real World | 2 | "Term match: by exact name" under "Antibody" scores the drug record, not the word |
| 3 | User Control and Freedom | 4 | Native details, nothing traps |
| 4 | Consistency and Standards | 3 | Score wording now one; row shape varies with data |
| 5 | Error Prevention | 3 | Kind card's 94% only inside the disclosure |
| 6 | Recognition Rather Than Recall | 3 | Arrow's meaning spoken only to screen readers |
| 7 | Flexibility and Efficiency | 3 | Band links to rows; whole summary is target |
| 8 | Aesthetic and Minimalist Design | 2 | Open card repeats the summary's score; dense grey line on phone |
| 9 | Error Recovery | n/a | No input or error states |
| 10 | Help and Documentation | 3 | "Term match" explained only in the closing note |
| **Total** | | **26/36** | **Good (72%)** |

## Design Specificity Verdict
LLM: fits the product; ruled ledger, quoted attributed words, provenance per row. Weak spot: the grey line on a phone.
Deterministic: source scan 0. URL scans and overlay: line-length on p.lede and a details paragraph, text-overflow on th.year: all outside the section. Contrast 7.49:1 grey, 9.93:1 blue; summaries 47–68px on phone; no overflow; card copy of cut definition aria-hidden as intended.

## Priority Issues
- [P1] Kind of molecule row: "Term match: by exact name" reads as matching "Antibody"; kind card's own score hidden. Fix: say what was matched ("Drug record: by exact name") and add the kind card's score. → clarify
- [P1] Grey line on phone: link alone on line 1, dots, 2–3 grey lines. Fix: below 40rem, link on its own line, provenance and score on one line beneath. → adapt
- [P2] Open card repeats summary's score as its head, and a cut definition's first lines. Fix: card head "Why it matched" inside a row; hide row's cut quote while open. → distill
- [P2] "Term match" unexplained where met. Fix: link it to the method anchor or one short line above rows. → clarify
- [P2] Summary text runs together at joins ("Lung canceris filed there asLung Neoplasms"). Fix: explicit spaces around hidden text. → harden

## Persona Red Flags
Jordan: bare arrow may read as a diagnosis change; "Term match: high, 100%" beside Obesity read as evidence strength.
Sam: long summary names; missing spaces at hidden-span joins; band-reached row has no ring.
Casey: section 1–1.5 screens; open card ~725px; card in row narrows definition to ~30 cpl.

## Minor Observations
- Facts label "Evidence when first reported" wraps; values misalign at 375px.
- Mechanism line in grey under "Antibody" can read as another name.
- Card-less Treatment row bare with no word on why.

## Questions to Consider
- Should the summary be the explanation ("Matched to Lung Neoplasms, 98%") rather than a door to one?
- Should At a glance collapse to the facts strip plus one line per term?
