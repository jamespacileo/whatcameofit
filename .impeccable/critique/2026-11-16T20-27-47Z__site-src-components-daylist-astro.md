---
target: latest and search rows (shipped)
total_score: 27
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/impeccable-knowledge-card-fdab75/site/src/components/DayList.astro"
target_fingerprint: "sha256:7d14770428603f290ab7d39600eb04f9aac434d01e80888bfa16b71ed1049e0f"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/impeccable-knowledge-card-fdab75/site/src/components/DayList.astro
timestamp: 2026-11-16T20-27-47Z
slug: site-src-components-daylist-astro
---
Method: dual-agent (A: design review · B: detector + browser). Target: shipped Latest/search rows (PR #253).

| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | "Changed" rows (7 of 1,161) barely differ from the rest |
| 2 | Match System / Real World | 2 | Record item "Trial registered" vs status "Phase 3 trial"; trial_registered meaning contradicts "All 3 have started" |
| 3 | User Control and Freedom | 3 | No collapse-all |
| 4 | Consistency and Standards | 2 | Search: topic pill, no button, no label, status before headline in DOM |
| 5 | Error Prevention | 3 | Headline link and status button are distinct targets |
| 6 | Recognition Rather Than Recall | 3 | Unlabelled dots in column must be counted |
| 7 | Flexibility and Efficiency | 2 | No collapse-all, no "changed only" filter |
| 8 | Aesthetic and Minimalist Design | 2 | Repeats: "Was/Now" + label; "No trial record found" + "0 trials"; no-signal twice |
| 9 | Error Recovery | 3 | Little to recover from |
| 10 | Help and Documentation | 4 | Guide link and "Why this claim is here" |
| **Total** | | **27/40** | **Good, with fixable gaps** |

Priority issues:
- [P1] Button accessible name ~200 chars, run together ("On record nowPhase 3 trial…"), action last. Fix: aria-label "Phase 3 trial. More on X"; sentences via aria-describedby.
- [P1] Vocabulary clash in registry rows and trial_registered meaning.
- [P1] Status card (166×~171px of a 505px row) outweighs headline; 43% say "Phase 3 trial"; "Changed" not distinct; "On record now" repeated per row.
- [P2] Off-path track hollow dots 1.2:1, invisible and implies a position; drop path, keep square/words; drop "0 trials".
- [P2] Search: hit-now before hit-main in DOM, CSS order hack, no label/button.

Detector: CLI 0 findings. Overlay 9: 5 stragglers + 1 unbalanced heading (headline/claim wrap), 2 line-length ~89-97ch, 1 skipped heading h2→h4. Contrast all ≥6.85. Record id links 22px tall (spacing exception). Ids unique, aria-controls valid, closed drawers inert. No overflow at 375px.
