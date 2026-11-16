---
target: registry records section
total_score: 22
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/registry-records-variants-15b5ae/site/src/components/RegistryRecords.astro"
target_fingerprint: "sha256:b91082ddab9567f49d94432e3d90c5eb419217d3434120574af9ce12e3e86df6"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/registry-records-variants-15b5ae/site/src/components/RegistryRecords.astro
timestamp: 2026-11-16T20-22-12Z
slug: site-src-components-registryrecords-astro
---
Method: dual-agent (A: design review · B: detector + browser)

## Design Health Score
| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | System status | 3 | Counts agree in digest, chip, fold note, pill; chip label "Registry records" vs heading "Possible registry records" |
| 2 | Real world | 2 | "Read as this treatment for this condition" under "Possible" reads as a contradiction; the reason it is not counted is not given |
| 3 | Control | 3 | No cap on long groups (5 rows = 1,819px on a phone) |
| 4 | Consistency | 2 | Trials above use a different identity line (size first, "(at ClinicalTrials.gov)") |
| 5 | Error prevention | 2 | Possible rows still look like counted trials; weight 500 vs 600 is not visible |
| 6 | Recognition | 3 | Not-counted note now under each group |
| 7 | Flexibility | 3 | Two paths per row |
| 8 | Minimalist | 2 | "Not counted" said three times near the top; long titles dominate |
| 9 | Error recovery | n/a | Read-only list |
| 10 | Help | 2 | No link from a reading or score to the guide |
| **Total** | | **22/36** | **Acceptable (61%)** |

## Priority issues
1. [P1] Match note wrapped onto its own line after a trailing "·" (fixed in this pass: the note is now a line of its own by design).
2. [P1] A possible row still looks like a counted trial: lead the candidate's line with a word ("Possible match") or the match note, mute untouched titles.
3. [P2] Two grammars for a trial on one page (Trials vs registry records): one shared identity line.
4. [P2] "Not counted" said three times and the reason never given: one note with the reason (score below the sure band), linked to the guide.
5. [P3] No cap on long groups: "The other N of M" as Papers does.

Detector: CLI 0 findings; overlay 1 straggler in a registry condition list (registry data), 3 line-length findings outside the section. Contrast 7.5:1; source link 33px at 375px; counts reconcile.
