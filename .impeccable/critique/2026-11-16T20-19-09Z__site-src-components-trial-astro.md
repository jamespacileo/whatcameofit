---
target: Trials on record section
total_score: 22
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/section-variants-mockup-6165ab/site/src/components/Trial.astro"
target_fingerprint: "sha256:6d35c8ee33f63c9ae2e11d98cce585c95479a4250db80a5e6aa6c48031a7b57e"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/section-variants-mockup-6165ab/site/src/components/Trial.astro
timestamp: 2026-11-16T20-19-09Z
slug: site-src-components-trial-astro
---
Method: dual-agent (A: design review · B: detector + browser)

## Design Health Score
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | Phase heads count trials and posted results; on a phone the heading scrolls away across ~10 tall cards |
| 2 | Match System / Real World | 2 | Main measure shows registry jargon (TEAEs, "PFS assessed by IRRC per RECIST v1.1"); "Another treatment" says little |
| 3 | User Control and Freedom | 3 | Rows open/close, hash links open rows; no open/close all |
| 4 | Consistency and Standards | 2 | DESIGN.md "Trial entry" bullet still describes the old entry; column head visible on first table only |
| 5 | Error Prevention | 3 | Careful, verdict-free wording |
| 6 | Recognition Rather Than Recall | 2 | Later phase tables have no visible column names |
| 7 | Flexibility and Efficiency | 2 | No way to narrow to posted results or finished; 50+ rows on large claims |
| 8 | Aesthetic and Minimalist Design | 2 | Fold says the measure 3 times; design, sponsor, match score twice each |
| 9 | Error Recovery | n/a | Static read section |
| 10 | Help and Documentation | 3 | "What a phase is" link, intro note |
| **Total** | | **22/36** | **Acceptable (61%)** |

## Design Specificity Verdict
Mostly authored: "None named in the record", model-read note "checked against the record", score-is-about-the-match note, no status colour, no verdicts. Table mechanics are generic; the fold is a generic stacked dt/dd list.
Detector: 0 findings in Trial.astro and [slug].astro. Overlay: 3 line-length findings, all outside the trials section (p.lede, p.glance-note, footer sources paragraph).

## Priority Issues
- [P1] Registry jargon is the headline of each row (Main measure). Fix: plain short noun from the reading plus registry words in grey, or an acronym map (OS, PFS, ORR, pCR, TEAE). clarify.
- [P1] "Compared with" cannot say what the comparison was, or whether the claim's treatment is the tested arm (montelukast NCT00394355 tests mometasone). Export carries comparator codes only; naming arms needs a pipeline/export change. clarify (+ pipeline).
- [P2] Fold repeats itself (~900px per trial at desktop): measure x3, design x2, sponsor x2, match score x2. distill.
- [P2] Context lost in long phases: head on first table only, phase heading not sticky, phone cards ~250px. layout.
- [P2] Phase heading reads joined to assistive tech and copy ("Phase 34 trials"); "Phase 2 and Phase 1/Phase 2" reads like a typo. polish/clarify.

## Persona Red Flags
- Jordan: acronyms; "Another treatment"; "planned" only cue a trial is unfinished; Phase 4 first with no hint it means after approval.
- Sam: open control named only "420 people"; div ARIA table with aria-colspan detail row; headers removed from a11y tree below 40rem; heading text joined.
- Casey: section folded by default on phone; trial ID links 19.5px tall (all 15); ~50 cards on big claims with no jump between phases.

## Minor Observations
- "Results posted" at 600 competes with State.
- Result group names are raw registry codes.
- 4-line intro note repeats on every claim.
- DESIGN.md:95 "Trial entry" bullet stale against :94.

## Questions to Consider
- Should "has posted results" outrank phase as the first grouping?
- Is the measure column there to tell trials apart or to tell the reader what was measured?
- Would one sentence per phase serve the phone better than ten cards?
