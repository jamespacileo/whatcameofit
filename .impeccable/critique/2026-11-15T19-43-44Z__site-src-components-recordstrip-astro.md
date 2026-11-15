---
target: record strip
total_score: 16
max_score: 32
na_heuristics: 3,9
p0_count: 1
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/article-component-variants-ef048f/site/src/components/RecordStrip.astro"
target_fingerprint: "sha256:e46bf168ac498133657de8688ca9e69dc1356c3b421a26893cdeb00cc9009c45"
target_path: /Users/jay/Projects/products/thenwhat/.claude/worktrees/article-component-variants-ef048f/site/src/components/RecordStrip.astro
timestamp: 2026-11-15T19-43-44Z
slug: site-src-components-recordstrip-astro
---
# Critique: record strip (home Latest row, index tables)
Method: dual-agent. Score 16/32 (h3, h9 n/a). Detector: 0 static findings; overlay 3 off-target (line-length x2, h2->h4 skip).
## Priority issues
- P0 Shared 2005->last-check axis empties strip: 47% of marks in right 10%, 646/672 gaps <1px, 49/100 Latest strips are only a report ring on 0 trials. Fix: per-claim axis, claim page only.
- P1 Competes with answer in row: third ink band between headline and foot (+22px +0.8rem). Fix: remove from Latest row.
- P1 Duplicates counts text ("3 trials · 3 with results posted"). Fix: counts stay as words, drawing goes.
- P2 Widths vary in DayList (224/380/387px) via flex:1 1 9rem (global.css:4744), breaking shared-scale premise.
- P2 Key costs 116px desktop / 144px mobile before first headline; 6 symbols > working memory; scrolls away by row 3.
## Recommendation
Not "hide by default": row-more is always open on touch/<34rem, so mobile keeps cost, and the empty axis stays. Remove from Latest row, keep counts sentence; move strip to claim page with per-claim axis and this report's day marked; index tables optional fixed 11rem with 3-mark key.
