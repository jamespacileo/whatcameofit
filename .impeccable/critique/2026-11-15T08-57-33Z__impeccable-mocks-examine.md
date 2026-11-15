---
target: examine pattern mocks
total_score: 23
max_score: 36
na_heuristics: 5
p0_count: 0
p1_count: 2
target_identity: "file:/Users/jay/Projects/products/thenwhat/.claude/worktrees/openspec-knowledge-cards-94195e/.impeccable/mocks/examine"
timestamp: 2026-11-15T08-57-33Z
slug: impeccable-mocks-examine
---
Method: dual-agent (A: design review · B: detector + browser overlay)

Target: the four mocks in `.impeccable/mocks/examine/` (claim, claim with promise, topic, home), after the fixes in a64ca76.

## Design Health Score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 2 | The promise page gives four totals for one list (21 / 19 / 18 / 17) |
| 2 | Match system / real world | 3 | "Basis of status" and "Off the path" unexplained |
| 3 | User control and freedom | 3 | No open-all; a timeline filter would carry into print |
| 4 | Consistency and standards | 2 | Jump pills and chip strip both show at 769 to 1088px; the two claim pages differ |
| 5 | Error prevention | n/a | Read-only pages |
| 6 | Recognition rather than recall | 3 | Timeline key sits under a list 2,144 to 3,636px tall on a phone |
| 7 | Flexibility and efficiency | 2 | No skip link: 24 tab stops before the article |
| 8 | Aesthetic and minimalist design | 2 | The claim is stated three times before any record; a disclaimer on every section |
| 9 | Error recovery | 3 | Empty state works; its text names "word and status" when only a word was typed |
| 10 | Help and documentation | 3 | Help links well placed, all `href="#"` |
| **Total** | | **23/36** | **Acceptable (64%)** |

## Design Specificity Verdict

Mostly specific: one marked place on a six-place path, the promised/recorded pair, dotted gap rows, answers on the question line. The borrowed frame is the generic part (empty left column in the band, icon rail, three equal columns on home). Detector: 5 CLI findings, all false positives. In-page scan: 5 `line-length` findings on claim pages, overstated (lines run 72 to 87 characters) and 4 real stragglers.

## Priority Issues

- **[P1] The band still pushes the record below the first screen.** Sheet starts 1,171px (claim) and 1,180px (promise) in an 812px window; first section heading at 1,661px; topic's first row at 1,347px. Fix: on a phone keep crumbs, title and card in the band; move the quoted headline and Follow/Share into the sheet; drop jump pills wherever the strip or side list shows; cut the topic lede sentence that repeats the card. Command: /impeccable adapt
- **[P1] Totals disagree on the promise page.** 21 (pill, chip), 4 promises and 17 records (heading), 19 (All tab), 18 (screen-reader message); "Promises with a date 2" shows one block; year labels are not recounted under a filter. Fix: one counting rule used everywhere; recount year labels; give undated promises a tab or hide them with the rest. Command: /impeccable clarify
- **[P2] Keyboard and screen-reader path.** No skip link; white focus ring on white inside the status card and on home's Look up button; the status is a paragraph, not a heading; Follow and Share come after all content. Fix: skip link; blue ring inside white surfaces; "Where it stands" as a heading; rail before the article in source. Command: /impeccable harden
- **[P2] The timeline is too long on a phone and the basis diamond marks nearly everything.** 117px per registry entry; diamond on 12 of 13 entries. Fix: date and event on one line with the id inline; diamond only on the events the status rule used, or one sentence under the status. Command: /impeccable distill
- **[P2] Print falls short of DESIGN.md.** No source address after links; masthead nav and breadcrumb print; diamond and masthead mark vanish without backgrounds; an active timeline filter is not reset; folds open only through script. Command: /impeccable harden

## Persona Red Flags

- Jordan: "Basis of status", "Off the path", "Match to this claim: High, 98%" unexplained where met; "no trial in people on record" and "No trial record found" read alike; topic lede ends "2 are at other statuses".
- Casey: the "3" link in the status card is 10x19px; claim-name links on topic are 21px tall; home topic links 25px; topic status chips scroll 1,019px sideways with no fade.
- Sam: no skip link; invisible ring in the status card; status not a heading. Good: fold buttons in headings, pressed states, live messages, hidden kind prefixes.

## Minor Observations

- 768px gets the phone layout; the status card stretches to 692px.
- Topic desktop rows 147 to 244px tall; DESIGN.md asks for a two-line clamp.
- The same promise is listed twice from one outlet and date.
- "In a year" unclear alone; home tabs unwired; home lookup placeholder cut off on a phone.

## Questions to Consider

- Would the status card at the top of the white sheet do the band's job at half the height?
- Could promised/recorded be the page's organising idea, with the timeline first?
- One sentence under the status instead of a disclaimer per section?
