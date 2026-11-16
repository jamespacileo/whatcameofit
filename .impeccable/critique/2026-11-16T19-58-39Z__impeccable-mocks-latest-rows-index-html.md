---
target: latest rows mock
total_score: 23
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 3
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/impeccable-knowledge-card-fdab75/.impeccable/mocks/latest-rows/index.html"
target_fingerprint: "sha256:14968b9d6d793bbc9dfd886a2ea4d7a0d625257c8feeb7b715a3e5bf7069c936"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/impeccable-knowledge-card-fdab75/.impeccable/mocks/latest-rows/index.html
timestamp: 2026-11-16T19-58-39Z
slug: impeccable-mocks-latest-rows-index-html
---
Method: dual-agent (A: design review · B: detector + browser)

## Design Health Score
| # | Heuristic | Score | Key Issue |
|---|---|---|---|
| 1 | Visibility of System Status | 3 | No row says when status was set or whether it moved |
| 2 | Match System / Real World | 2 | Record kind "Trial registered." beside status "Phase 3 trial" reads as contradiction |
| 3 | User Control and Freedom | 3 | Pop lingers, covers next row's status |
| 4 | Consistency and Standards | 2 | "Phase 3" (B) vs "Phase 3 trial"; boxed vs unboxed status by row kind |
| 5 | Error Prevention | 2 | Registered and Phase 1 hues indistinguishable |
| 6 | Recognition Rather Than Recall | 1 | 14-symbol key; scrolls away on phone |
| 7 | Flexibility and Efficiency | 2 | Hover-first; touch has no route to pop |
| 8 | Aesthetic and Minimalist Design | 3 | B, C lean; A drawer repeats claim line |
| 9 | Error Recovery | 2 | No off-path / missing-value states drawn |
| 10 | Help and Documentation | 3 | Caveat link good but trapped in role=tooltip |
| **Total** | | **23/40** | **Acceptable, significant gaps** |

## Priority Issues
- [P0] Ladder implies progress/verdict; cannot draw failed/terminated/retracted. FDA-rejection row shows near-full ladder.
- [P1] Colour per status contradicts DESIGN.md; Phase 1 label 4.39:1 light fails AA.
- [P1] Two vocabularies in record rows (event kind uses status words).
- [P1] Hover tooltip only route to path + caveat link; focusable div, no role.
- [P2] Phone: claim/indication truncated (A, B), absent (D); toggles 22.8px < 24px; outlet tile "X" 4.0:1.

## Detector
CLI: 0 findings (rows JS-rendered). Overlay: 7 — 4 low-contrast outlet tile (#e5462a), 3 line-length on mock intro copy (false positive for product). Duplicate ids for aria-controls across variants.
