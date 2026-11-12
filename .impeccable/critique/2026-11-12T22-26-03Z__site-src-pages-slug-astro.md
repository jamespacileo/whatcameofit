---
target: site after navy, icon and fixes
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/site/src/pages/[slug].astro"
target_fingerprint: "sha256:7ff62c2ce9763b900a27d5565b8fc00915add479de18e074847782c7239ebd69"
target_path: /Users/jay/Projects/products/thenwhat/site/src/pages/[slug].astro
timestamp: 2026-11-12T22-26-03Z
slug: site-src-pages-slug-astro
---
Method: dual-agent (A: design review, B: detector + overlay)

## Design health: 28/40 (Good)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | System status | 3 | Tracked answer slow on dev server |
| 2 | Real-world match | 3 | Track names only its two ends; "Evidence then", "Basis of status" |
| 3 | Control and freedom | 3 | Hover-opened popover covers the meaning sentence |
| 4 | Consistency | 2 | Nav "Search" vs button "Look up"; headline link target differs between home and claim page |
| 5 | Error prevention | 3 | Short links and posts caught with exact guidance |
| 6 | Recognition | 3 | Small tracks have no legend below six claims |
| 7 | Efficiency | 3 | No lookup from a claim page |
| 8 | Minimalism | 3 | "Statuses set most recently" shows one batch date |
| 9 | Error recovery | 2 | Lookup failure and untracked messages name topic pages with no link |
| 10 | Help | 3 | Method page reachable only from the sub-headline and footer |

## Specificity verdict

Authored, not interchangeable. Weak spots: the icon appears on no page; home below the box is two generic tables. Deterministic scan: 0 findings (CLI and overlay on three pages).

## Priority issues

- [P1] Lookup dead ends (site/src/pages/index.astro): untracked and failure messages are plain text with no next action. Fix: link the topic pages and offer a search by treatment name. Command: /impeccable harden
- [P1] Phone target sizes: source, archived-copy and outlet links 18px tall; embed summary 26px. Fix: block padding. Command: /impeccable adapt
- [P2] Two adjacent links per headline row on home; outlet link leaves the site with no arrow. Command: /impeccable clarify
- [P2] Phone tables compute to display:block with no ARIA roles; unverified with a screen reader. Command: /impeccable audit
- [P3] Word search cannot be judged in dev (index built only at build). Command: /impeccable audit

## Minor

Nav navy vs ink is two dark navies; "Search" nav item leads home; outlet letter tile reads as a radio button; embed has no max width; no apple-touch-icon; "that old" in the no-signal popover is awkward; "2025 human trials by 2025" repeats the year.
