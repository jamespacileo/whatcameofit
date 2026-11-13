---
target: site design, UX and branding (re-run)
total_score: 29
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/site/src/pages/[slug].astro"
target_fingerprint: "sha256:679f6e3f0da11fedd889ee89991fcf4155a2682dc397e397807341e8a65d4e57"
target_path: /Users/jay/Projects/products/thenwhat/site/src/pages/[slug].astro
timestamp: 2026-11-12T21-35-49Z
slug: site-src-pages-slug-astro
---
Method: dual-agent (A: design review, B: detector + overlay). The review was interrupted and resumed; it saw every page at 1280 and only the claim and home pages at 375.

## Design health: 29/40 (Good)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | System status | 3 | "Last checked" is only in the footer |
| 2 | Real-world match | 3 | "Preclinical only" and "Basis of status" need the popover; middle track places unnamed |
| 3 | Control and freedom | 3 | No way back to the lookup answer except browser back |
| 4 | Consistency | 2 | A quoted blue headline goes to the claim page on home and to the outlet in the timetable |
| 5 | Error prevention | 3 | Short-link refusal is exemplary |
| 6 | Recognition | 3 | The key scrolls away on a phone |
| 7 | Flexibility | 3 | No filter on long timetables |
| 8 | Minimalist | 3 | The digest is half empty at 1280 with a one-line summary |
| 9 | Error recovery | 3 | An untracked answer has no next step unless a suggest address is configured |
| 10 | Help | 3 | The method page promises a report-an-error link that renders only when an address is set |

## Specificity verdict

Authored, not interchangeable: amber meaning only "promised", the unfilled stage track, the quoted headline against the status, the question mark whose dot is the marker.

Deterministic scan: CLI clean. Overlay: one finding on every page, the footer sentence leaves "ours." alone on its last line at 1220px (site/src/layouts/Base.astro:160).

## Overall

The peak is now on the page: the row with a promise on amber beside "No record". The card still tells the story faster than the page's first screen.

## Working

1. Promise beside record, amber held to one meaning on page, tables and card.
2. Lookup answers are honest about certainty.
3. The phone claim page puts status, track, note and summary in the first screen.

## Priority issues

- [P1] A pasted article address is written into the page URL as ?q= (site/src/pages/index.astro, submit handler), so a reload or a shared link sends it to the host. Fix: keep ?q= for typed words only. Command: /impeccable harden
- [P1] The promise is absent from the first panel; on a phone it is about 1,300px below the status. Fix: the latest dated promise as an amber fact in the digest, linking to its row. Command: /impeccable layout
- [P2] Phone targets under 44px beyond the pills: info button 32, no-signal note 30, chip 29, record triggers 26, nav 33, footer links 24. Command: /impeccable adapt
- [P2] The same-looking headline link has two destinations. Fix: mark outbound links consistently. Command: /impeccable clarify
- [P3] The claim page ends on the embed disclosure, and the card thumbnail at 162px is illegible. Command: /impeccable polish

## Persona red flags

- Jordan: "Preclinical only" is the first big thing read and its meaning is behind a 32px icon.
- Casey: small targets; the lookup answer's headline is not a link.
- Sam: "Other claims in <topic>" is announced twice (heading and caption); "Source" repeats as link text; popover triggers reported no aria-expanded.

## Minor

- The Share pill changes width on "Link copied".
- Fixture outlet tiles are solid blue squares.
- Unverified: the status popover looked translucent at 375 in a background tab.
- Is "It happened" a verdict by omission?
