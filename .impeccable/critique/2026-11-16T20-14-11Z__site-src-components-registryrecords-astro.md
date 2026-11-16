---
target: registry records section
total_score: 21
max_score: 36
na_heuristics: 9
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/registry-records-variants-15b5ae/site/src/components/RegistryRecords.astro"
target_fingerprint: "sha256:31d6d40dbd15a3998bec28200110b59900fced823cb4bab58a3c8fe26d7009ed"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/registry-records-variants-15b5ae/site/src/components/RegistryRecords.astro
timestamp: 2026-11-16T20-14-11Z
slug: site-src-components-registryrecords-astro
---
Method: dual-agent (A: design review · B: detector + browser)

## Design Health Score
| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 2 | Folded heading and section chip carry no count, unlike every neighbour |
| 2 | Match system / real world | 2 | "Tests" lists every registry intervention, comparators and procedures included |
| 3 | User control and freedom | 3 | Folds and anchors well; no cap on long groups |
| 4 | Consistency and standards | 2 | Source hidden in screen-reader text while Trials shows "(at ClinicalTrials.gov)"; naming drifts (digest / chip / heading); pill colour differs from DESIGN.md |
| 5 | Error prevention | 2 | Phase 3 "Under way" rows under "Read as this treatment for this condition" read like counted trials |
| 6 | Recognition rather than recall | 2 | "Not counted in the status" said once at top; nothing per group |
| 7 | Flexibility and efficiency | 3 | Two clear paths per row |
| 8 | Aesthetic and minimalist design | 3 | Calm; every title bold and underlined, so long titles form a wall of links |
| 9 | Error recovery | n/a | Read-only list |
| 10 | Help and documentation | 2 | Nothing explains a reading, or why a record read as this claim is only possible |
| **Total** | | **21/36** | **Acceptable (58%)** |

## Priority issues
1. [P1] "Tests" over-claims: comparators and procedures (Pembrolizumab, Computed Tomography) labelled as tested. Fix: relabel "Named in the record", or split by role if the record carries arm roles. /impeccable clarify
2. [P1] "Possible" invisible at row level; rows look like counted trials, nearing "trial as treatment option". Fix: per-group note saying why it is not counted (score below the sure band), lighter title weight for candidates. /impeccable clarify + layout
3. [P2] No count on folded heading or section chip; ", 5 possible" in the digest not linked. Fix: FoldHead note + chip count + link. /impeccable polish
4. [P2] Registry source only in hidden lower-case text; NCT link 17px tall at 375px (below 24px WCAG 2.5.8). Fix: "NCT… at ClinicalTrials.gov" in sight, as Trials does; enlarge target. /impeccable adapt
5. [P3] Group heading accessible name reads "condition5 records". Fix: hidden separator before count. /impeccable polish

## Minor
Pill uses --tint, DESIGN.md says tag blue. UNREAD_HEADING is pipeline jargon. Not-read row has no title slot and looks broken. Tight gap between group heading and first rule. Papers reuses class "matched".

Detector: CLI 0 findings on component and page; overlay 3 line-length hits, all outside the section. Contrast 7.5:1 meta, 16.5:1 body.
