---
target: "home page, mobile view: visual hierarchy, layout and space use"
total_score: 26
max_score: 40
na_heuristics: 
p0_count: 0
p1_count: 3
target_identity: "file:/Users/jay/Projects/worktrees/thenwhat/claude-home-mocks/site/src/pages/index.astro"
target_fingerprint: "sha256:74e84e97a71216e3f1aaf493688af12922fd3e097dfde6ca84732a16dbe60c27"
target_path: /Users/jay/Projects/worktrees/thenwhat/claude-home-mocks/site/src/pages/index.astro
timestamp: 2026-11-17T12-56-55Z
slug: site-src-pages-index-astro
---
Method: dual-agent (A: independent design review · B: detector + browser evidence). Target: home page at 375x812. Focus asked for: visual hierarchy, layout and space use on the mobile view.

## Design health score

| # | Heuristic | Score | Key issue |
|---|---|---|---|
| 1 | Visibility of system status | 3 | Day headings not sticky; inside Thursday's 4,087px group nothing says which day you are in |
| 2 | Match with real world | 3 | First feed item is "Registry record NCT07937852" |
| 3 | User control and freedom | 3 | Filter pill scrolls away; about 5,000px back from row 15 |
| 4 | Consistency and standards | 2 | Three status lockups, two headline styles on one page |
| 5 | Error prevention | 3 | Outlet link (leaves site) and headline link (claim page) both unmarked |
| 6 | Recognition over recall | 3 | Track is six unlabelled dots until the row is opened |
| 7 | Flexibility and efficiency | 2 | 2.2 rows per screen; a week is 8.7 screens |
| 8 | Aesthetic and minimalist | 2 | "Status now" printed 19 times; title repeats status in 6 of 10 record rows |
| 9 | Error recovery | 2 | Search failure says "type a name in the box above", which is what just failed |
| 10 | Help and documentation | 3 | Nothing on the first phone screen says what the site is |
| **Total** | | **26/40** | **Acceptable** |

## Design specificity verdict

Review: the Latest list is authored for this product (serif quoted headline is the outlet's words, sans is the record's). The opening band and the lower half are category-typical. On a phone the band hides the lede, the try chips and "970 claims tracked".

Detector: source scan clean (0 findings, 11 files), but .astro files get regex rules only, so that is an undercount. URL scan failed: "page has more than 30000 elements". Browser overlay reported 1 finding (skipped-heading, h2 to h4), a false positive: that h4 sits in a hidden block.

## Overall impression

Rows read well one at a time. As a feed on a phone they are too tall and too repetitive. Biggest win: from 2.2 to about 4 rows per screen.

## What's working

- Filter pill: one 112x47 control, no height cost, renames itself when used, state in the URL; panel fits (340x253).
- Two voices: hanging-quote serif headline over the sans claim line.
- Opened row: explains a headline beside a status without a verdict.

## Priority issues

- [P1] Rows too tall for a feed. Report rows average 286px, record rows 382px; 19 rows are 6,932px. The status panel is 99px, 35-46% of a report row. Fix: on a phone make the panel one line of about 48px (status, track, chevron); move the counts into the opened detail; clamp the attached "Newest report" quote. Target 190px or less for a report, 240px or less for a record. Command: /impeccable adapt
- [P1] One trial repeated as five full rows. NCT07933549 appears 5 times on Thursday 12 November (about 2,000px), each "Trial registered" for a different claim; Thursday alone is 5 screens. Fix: one row per record with its claims as compact sub-lines; cap a day at about 5 rows with "Show more"; sticky day heading. Command: /impeccable shape
- [P1] Record rows have no single lead. Three near-equal lines: event title 19px/650, quoted report 18.4px serif, status 18.4px/700 blue. In 6 of 10 record rows title and status say the same thing. Fix: when the event's stage equals the status, merge them; keep both only when they differ; drop the quoted report to 15-16px. Command: /impeccable distill
- [P2] First screen spends 60% before the list. Masthead 128px plus band 361px; first row starts at y=623, its status panel at y=871, below the fold. Fix: one-row masthead (about 64px); button inside the field; spend about 40px on the try chips or the claim count. Command: /impeccable layout
- [P2] Small tap targets and unmarked links. 17 "See the N trials on record" links are 23.5px tall, 4px from the next; "Clear filters" is 23px. Headline and outlet name are both plain ink. Fix: detail links as 44px rows; a leaving-site mark on the outlet. Command: /impeccable harden

## Persona red flags

- Casey (one-handed, distracted): typing is the only way to ask, try chips hidden on phone; a week is 8.7 screens; filter unreachable mid-list.
- Jordan (first-timer): no statement of purpose on the first screen; first item is a registry id; the quoted headline does not look tappable.
- Alex (journalist checking an old story): no dense view; five rows for one trial; no jump between days.

## Minor observations

- Record top line is 31px or 57px depending on whether the topic wraps.
- Panel is 68px without counts, 99px with.
- 14 font sizes, neighbours under 1px apart.
- Quote marks are 3.78:1 against white; decorative, softened at the operator's request.
- Day heading wraps to two lines when counts are long.
- "Every headline and claim, as lists" repeats the same headlines 7,000px later in another style (2,634px).
- 195,000 DOM nodes (1,709 rows built, 19 shown); the overlay scan froze the page for 90 s.
- Page is 12,728px, 15.7 screens.

## Questions to consider

- If the status is the answer, why is it last in every row and absent from the first screen?
- Does a phone need both "Latest" and the second list of the same headlines?
- Does someone who remembers one headline want registry records as full rows, or one line per day?
