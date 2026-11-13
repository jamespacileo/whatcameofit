---
target: site design, UX and branding
total_score: 28
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/site/src/pages/[slug].astro"
target_fingerprint: "sha256:e9c9ba9da81e38ac28aea70d231f2c2433ef62333f1db05affa8203607c5a367"
target_path: /Users/jay/Projects/products/thenwhat/site/src/pages/[slug].astro
timestamp: 2026-11-12T20-09-45Z
slug: site-src-pages-slug-astro
---
Method: dual-agent (A: design review, B: detector + overlay)

## Design health: 28/40 (Good)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | System status | 3 | "Copied" is a label swap only and is not announced |
| 2 | Real-world match | 3 | "Basis of status", "Evidence then", "Preclinical only" are registry language |
| 3 | Control and freedom | 3 | Lookup answer has no visible clear |
| 4 | Consistency | 3 | Three underline meanings; middle nav label changes with topic count |
| 5 | Error prevention | 3 | Short links refused early with a reason |
| 6 | Recognition | 2 | Four unnamed middle places on the track; record detail hides behind a dotted underline |
| 7 | Flexibility | 2 | No "more in this topic", no next claim |
| 8 | Minimalist | 3 | Empty amber column on desktop is a slab of colour meaning nothing |
| 9 | Error recovery | 3 | 404 is plain but flat |
| 10 | Help | 3 | "How a status is set" link is orphaned under the table |

## Specificity verdict

Half authored, half interchangeable. Authored: amber promise beside record, quiet year gaps, position-only track, the wordmark whose question-mark dot is the stage marker, the link-preview card, the voice. Interchangeable: home, topic, It happened, Anniversaries, 404.

Deterministic scan: 0 findings. CLI clean over pages, components, layouts; overlay clean on /, /phase-claim, /topics.

## Overall

Trustworthy and calm, too calm to travel. The link-preview card is the sharpest thing in the product and is more pointed than the page it represents. Biggest opportunity: make the page and the lookup as pointed as the card.

## Working

1. The digest panel answers in one second, at 375px without scrolling.
2. Copy is exact everywhere, especially lookup refusals and the no-signal popover.
3. The phone timetable: an amber promise block above "Recorded: No record".

## Priority issues

- [P1] Lookup answer under-delivers (site/src/pages/index.astro:234). Fix: render as a mini digest (blue status label, stage track, no-signal note, "See the records"); scroll to it on a phone. Command: /impeccable delight
- [P1] A cold arrival is never told what the site is. Fix: one muted line above the claim title linking to how-it-works. Command: /impeccable clarify
- [P2] The promise-versus-record moment is not staged on desktop (site/src/pages/[slug].astro:260). Fix: tint only cells holding a promise; "No record" in full ink beside a promise. Command: /impeccable layout
- [P2] The claim page trails off (site/src/pages/[slug].astro:393). Fix: "Other claims in <topic>", then Pass it on with the square card as a thumbnail. Command: /impeccable delight
- [P3] Small targets: Share and pass-on pills are 31px tall; Share is top-right. Fix: 44px under 40rem. Command: /impeccable adapt

## Persona red flags

- Jordan: no orientation; "Preclinical only" explained only behind a 32px info button; "Basis of status" is jargon.
- Casey: Share top-right; pass-on tools 1,700px down; lookup does not scroll to its answer.
- Sam: popover panel has no role or label (site/src/components/Pop.astro); record kind spoken only for news reports; "Copied" silent; index-table track omits the place name.

## Minor

- "2025: No record" after a 2024 approval reads oddly.
- Share sentence prints localhost:4321 (site config).
- Embed at wide widths is a full-bleed strip; cap near 440px.
- Nav "Search" means home. Outlet letter tiles look like checkboxes.
- Not reviewed: word search (index exists only after build), "Report an error", the "Copied" state.

## Viral, motion and humour ideas

Guardrail: jokes aim at headlines and time, never illness or a topic.

Viral: promise on amber in the card; Share pill as "Reply with the record"; year pages as "Class of 2019" with one honest count; a scoreboard line on It happened; a daily "Reported on this day" card; a tagline such as "Five years away, five years later."

Motion: the wordmark's dot drops into the lookup answer's track; the hook draws while a lookup waits; a dot lands beside "Copied"; the card thumbnail lifts on hover. No scroll motion, no loops.

Deadpan: 404 as "Status: no page record found. Last checked: just now."; empty search "No record found. We say that a lot."; extension "Not tracked yet. Nobody has asked us what came of this one."; footer "We'll check again."

Skip: confetti on approvals, birthday candles, puns on a condition name.

## Questions to consider

1. Should the claim page open with the outlet's quoted headline, as the card does?
2. Is "Statuses set most recently" on the home page for readers or for the operator?
3. Could the track name its current place under the dot in place of the two end labels?
