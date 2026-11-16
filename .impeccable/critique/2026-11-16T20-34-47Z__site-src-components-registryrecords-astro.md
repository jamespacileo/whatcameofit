---
target: registry records section
total_score: 23
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 3
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/registry-records-variants-15b5ae/site/src/components/RegistryRecords.astro"
target_fingerprint: "sha256:3da5144ecd2373a8209dd54279cc2b9105c17a7baf19b490fbb1f430ed26a0d3"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/registry-records-variants-15b5ae/site/src/components/RegistryRecords.astro
timestamp: 2026-11-16T20-34-47Z
slug: site-src-components-registryrecords-astro
---
Method: dual-agent (A: design review · B: detector + browser)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | System status | 3 | "Details not read" sits in the state slot and reads like a trial state |
| 2 | Real world | 2 | The note does not name the cut-off, so 79% under "this treatment for this condition" looks arbitrary |
| 3 | Control | 3 | Fold and "The other N of M" work |
| 4 | Consistency | 2 | Trials use "View trial details here" and lead with size; records link the title and carry no size; chip vs heading name |
| 5 | Error prevention | 2 | A possible record links to the same trial page as a counted one |
| 6 | Recognition | 3 | "Possible match:" on every row |
| 7 | Flexibility | 2 | Each row about one phone screen tall |
| 8 | Minimalist | 3 | Count pill is the brightest mark; two intro paragraphs overlap |
| 9 | Error recovery | n/a | Read-only |
| 10 | Help | 3 | "How a match is scored" in place |
| **Total** | | **23/36** | **Acceptable (64%)** |

Priority: [P1] note ambiguous, no cut-off; [P1] "not counted" twice when matched + possible; [P1] two routes to one trial page, candidate framing lost there; [P2] no size in record rows; [P2] not-read state in state slot, chip/heading names differ.
Detector: CLI 0; overlay 1 straggler ("v8") in registry condition data. Contrast 7.5:1 and 16.5:1; no overflow.
