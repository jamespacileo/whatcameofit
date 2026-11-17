---
target: mobile landing + claim page, after fix pass
total_score: 25
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/jay/Projects/worktrees/thenwhat/feat-mobile-claim-page/site/src/pages/[slug].astro"
target_fingerprint: "sha256:86c3c4622c293031e6711ef893b7ebbb6664ef23a88b2ba211f92f5134506dde"
target_path: /Users/jay/Projects/worktrees/thenwhat/feat-mobile-claim-page/site/src/pages/[slug].astro
timestamp: 2026-11-17T17-38-30Z
slug: site-src-pages-slug-astro
---
Method: dual-agent (A: recritique-a · B: recritique-b)

Target: mobile (375x812), landing and claim page, branch `feat/mobile-claim-page` after the clarify, optimize, adapt and harden pass. Dev server, published export. Not checked: real device, screen reader, 200% zoom, production transfer sizes, scripting off in a browser.

## Design Health Score: 25/40 (Acceptable)

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Open filter panel hides the result it changed |
| 2 | Match system / real world | 2 | H1 "EU approves erenumab…" unquoted, 300px above "Phase 3 trial" and "No approval is listed here" |
| 3 | User control and freedom | 3 | Filter panel has no Done; status panel fixed after this assessment |
| 4 | Consistency and standards | 2 | "newest first" labels an oldest-first list; Filter button swaps its name for a value |
| 5 | Error prevention | 3 | Enter on a plain word in the lookup leads to a dead end on dev |
| 6 | Recognition rather than recall | 3 | No way back to the lookup after 12 viewports of landing |
| 7 | Flexibility and efficiency | 2 | Pager bottom-only; 10 rows cost 3 viewports |
| 8 | Aesthetic and minimalist design | 2 | Landing lists everything three ways; answer panel stacks nine items |
| 9 | Error recovery | 2 | "Search is not available right now": no cause, circular remedy |
| 10 | Help and documentation | 3 | Help in context; status panel cramped before its fix |

Cognitive load: 4 of 8 fail (chunking, one thing at a time, minimal choices, working memory). Was 5 of 8.

## Design Specificity Verdict

LLM assessment: claim page authored; landing half authored (hero and Latest cards specific, lists below interchangeable).

Deterministic scan: CLI over 39 files, zero findings. In-browser: 7 `hard-offset-shadow` on `/` (gutter mask the colour of the page on sticky day heads: false positive), 1 `nested-cards` per claim page (digest on a full-width band: false positive).

Measured: landing 5,278 elements on arrival (was 197,607), 12.6 viewports, 0 targets under 24px. Claim page 6.1 viewports, status label at y=481. No overflow at 375 or 320. Contrast: 0 failures dark; light: 26 on `/`, all the decorative opening quote glyph at 3.78:1. Headings in order. No console errors. One data request on load of `/`.

## What changed since the last run

- Landing: 197,607 → 5,278 elements; rows load on demand.
- Claim page: byline under title; approval sentence in the status card; status panel shows 3 of 44 records with a way to the rest and a Close control; panel set at the foot of a phone's screen after this run found it 109px off screen.
- Already on main before this pass: timetable summary (page 19.3 → 6.1 viewports), approval answer wording in the brief, masthead trim.

## Priority Issues

- [P1] Title still reads as the site's own claim. `h1.title` sets the outlet's headline unquoted above "Phase 3 trial". The bridge sentence explains, but the first 500px still give two answers. Fix: quote or hedge the H1, or lead with intervention and indication and put the headline in the quoted report line. Operator decision. Command: /impeccable clarify.
- [P1] First "Next" loads a whole list: `/rows/headlines.txt` is 8.0 MB raw on dev and the page goes 5,278 → 45,767 elements. The old cost, deferred to the first press. Fix: files per page of rows, or per span. Command: /impeccable optimize.
- [P1] "See the posted results" link cannot be pressed: 0 of 296 sampled points reach it; `button.fact-open::after` covers it (`dl.fact-sheet`). Not introduced by this pass. Command: /impeccable harden.
- [P2] Answer panel overloaded: nine stacked items, one sentence with seven numbers. Fix: move the trial-state counts to the record in brief, which repeats them. Command: /impeccable distill.
- [P2] Lookup and filter dead ends: failure message tells the reader to type in the box they just used (`Lookup.astro:1229`); filter panel covers its results and its trigger truncates to "No trial record fo…". Command: /impeccable clarify.
- [P3] "newest first" over an oldest-first milestone list; milestone links, `button.text-control` and `a.brief-term` 21–24px tall; opening quote glyph 3.78:1 in light. Command: /impeccable polish.

## Persona Red Flags

- Casey: pager only after three viewports; 21–24px links in dense rows; 10 chips in a side-scrolling strip.
- Jordan: approved in the title, Phase 3 in the panel; "Place 5 of 6", "5 possible" before any explanation; Latest, Headlines and Claims look like one list.
- Sam: status panel is `role="note"`, unlabelled, focus not moved in; filter popover has no role or label; a dozen summaries share one name.

## Minor Observations

- Landing Claims tab shows a "…approved…" headline beside "Phase 3 trial": the same contradiction in list form.
- Thin proportion bars under "28 of 49 trials" read close to the meters the direction refuses.
- Outlet icons fetched by script, some three times.
- Claim page ends flat: no closing restatement of status and last-checked day.

## Questions to Consider

1. Should a claim whose own reports say "approved" get a track that stops at Phase 3, or a panel that says approval is not confirmable here?
2. Does a phone need the five tabbed lists, or are lookup, Latest and topics the whole landing?
3. Could a "No trial record found" page be two screens long?
