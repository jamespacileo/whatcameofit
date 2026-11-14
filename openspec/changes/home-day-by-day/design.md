# Design

## Context

See `proposal.md` for why. The working mock is `.impeccable/mocks/frontpage/mix-days.html` (preview: the `mocks` entry in `.claude/launch.json`, then `/frontpage/mix-days.html`). It is built from the published export of 13 Nov 2026 and is the visual reference for this change, except where a decision below departs from it.

What the home page is today (`site/src/pages/index.astro`, 35 KB):

- A full-width opening band with the lookup, then Following, the tally, the since line, the status path with the topic choice, four tabbed tables (Headlines, Status changes, Promises, No signal), Keep up, the anniversaries block, topics, years and two closing sections.
- Every row of every table is in the page as built. Scripts hide rows by setting `data-out-*` and `data-later` attributes: narrowing by status and topic, paging ten at a time, and the since line's narrowing all work this way.
- Reader state (`site/src/lib/returning.ts`): the day of the last visit and the followed claims, kept in the browser only.
- On a phone the band ends at 585 px and the first headline row starts at 784 px of 812 (measured on the live site on 2026-11-14), so there is no spare room above the first row.

Constraints that shape the approach:

- The site is static and built from one export. The page cannot know the reader's date at build time, and the export's `last_checked_at` can be null.
- `claim.trials` is optional in the export (older exports lack it).
- The site owns all wording, and a build fails on verdict wording (`assertNeutral` in `status.ts`, `assertNoOutcomeVerdict` in `trial-facts.ts`).
- DESIGN.md: pale amber means "promised" and nothing else; no colour for a status; a colour is named once in a key; nothing moves on scroll.
- The headline pressed on the home page is carried to the claim page by a view-transition name (`followedNameFor`), which must be unique on a page.

## Goals / Non-Goals

**Goals:**

- One list model, built by a pure function, that every part of the page reads: headings, rows, counts, the row of seven days.
- The new rows join the page's existing mechanisms (attributes set by script, everything in the page as built) instead of adding a second way to filter and page.
- No sentence on a row that the build cannot check.

**Non-Goals:**

- No change to the export, the pipeline or `site/export.schema.json`.
- No Follow control on a row. The mock draws one; following stays on the claim page, where it is explained and confirmed.
- No change to the four tabbed lists beyond where they stand.
- No client framework and no fetch: the list is static markup.

## Decisions

### 1. Page order

Band (lookup), Following, the dated head with the row of seven days, the kind controls, the status path and topic choice, the day-by-day list with its "earlier" control, then a heading and under it the since line, the four tabs and their lists, then the rest of the page as now. The tally line moves to sit with the dated head.

*Alternative considered:* the day-by-day list as a fifth, first tab. The operator chose to keep the four lists and move them down; a tab would also hide the new list from a reader with scripting off behind three others.

### 2. The page is dated by the last check, not by the reader's clock

The dated head, the seven days, the fortnight of day headings and the "one older claim" all take their day from the export's `last_checked_at`. The reader's own date is used for two things only, both in script: the words "Today" and "Yesterday" on a heading, and the last-visit line. A page built yesterday therefore names yesterday as the day of the last check and says nothing is "today".

When `last_checked_at` is null the head and the list are not built and the four lists follow the lookup. `generated_at` is not used in its place: a build day is not a check day.

*Alternative considered:* compute headings in the browser from the reader's date. It would make the static page and the scripted page disagree, and would show "Today" over a day the registries were not read.

### 3. One pure module builds the list

A new module in `site/src/lib` takes the published claims and the day of the last check and returns: the headings in order (kind: day, week or year; its date; its rows), the rows (kind: report, record or promise; its date; the claim; what it shows), the promises still to come, the seven days with their report counts, and the older claim for the day. No database, network or clock: the day is passed in. It reads `recentReports` for reports, the claim's events for records, `latestPromise` for promises and `changesOf` to decide which record row says "Changed".

Rules it holds:

- Report rows: one per claim per day; a claim's reports of one day are merged, the first title (by the order `recentReports` already uses) quoted, every outlet named.
- Record rows: events dated in the ninety days up to the day of the last check, of every exported event type. A record dated on a day `changesOf` gives a change for that claim says "Changed"; with several records that day, the first in the list's order.
- Promise rows: the claim's latest dated promise, as the Promises list uses. After the last check: the "to come" set. On or before: under its date's heading.
- Headings: days for the fourteen days up to the last check (the seven of the row always present, even empty), ISO weeks (Monday) for the rest of that year, years before.
- The older claim: claims first reported before the year of the last check, ordered by first-reported date then slug; index = day of the year modulo their number.

This is the test seam: the module is tested against `site/tests/fixture-export.json` with a fixed day. The page gets one success test per behaviour from the built HTML, as the other page tests do.

*Alternative considered:* build the groups in `index.astro`. The page is already 35 KB with three scripts; grouping rules there could not be tested without a build.

### 4. Row sentences are templates with their own guard

A second small module holds the five sentence templates and the order of preference from the spec. Each template takes counts, years and site labels only. At module load every template is rendered with sample values and passed through `assertNeutral`, `assertNoOutcomeVerdict` and one new check for words that characterise an interval or a count (for example "still", "only", "just", "yet", "finally", "despite", "already", "at last", "overdue", "late", "kept", "delayed"); a failure fails the build and names the sentence.

- The regulator sentence shows the event's own summary and date, as the claim page's timetable does. It is a record's words, not the site's, and is not passed through the checks.
- The trial-count sentence uses the same counting the claim page uses for "Trials on record". When the export carries no `trials` for the claim the sentence is left out: no count is derived another way.
- "Completed" is a registry state; "with results posted" is the existing event label. Neither says how a trial turned out.

The evidence stage and the status come from `EVIDENCE_STAGES`, `STATUS_LABELS` and `STATUS_GLOSSES` unchanged.

### 5. Three grounds, one key

White for a report, the panel blue for a record, pale amber for a promise. The kind controls carry a small swatch of each and are the only key (DESIGN.md: say it once). Each row also says its kind in a small grey label, so the ground is never the only signal. In a report row the "on record now" cell is on the panel blue, which is the same meaning: blue is where the record speaks.

DESIGN.md gains one line under Colour: in a list, the panel blue is also the ground of a registry record. Nothing else takes it there.

### 6. Controls reuse the page's attribute mechanism

Each row carries `data-status`, `data-topic`, `data-on` and a new `data-kind`. The kind controls set `data-out-kind`; the existing narrowing script sets `data-out-status` and `data-out-topic` on these rows as it does on table rows (its scope already is the page's feed element, which is widened to hold the new list). A heading hides when all its rows are out, and its count line is rewritten from the rows left. The kind pick is a new address parameter beside `status` and `topic`.

On a wide screen the topic choice is drawn as the side column's list of topics with counts, pressed to narrow; on a phone it stays the select behind "Narrow these lists". Both drive the same parameter.

*Alternative considered:* re-render the list in script from JSON, as the mock does. It would put the rows in the page twice or not at all with scripting off.

### 7. Opening on the fortnight

Week and year headings carry `data-later` and are revealed a batch of eight headings at a time by one control under the list that states how many rows remain. Without scripting, and in print, nothing is hidden. An address fragment naming a heading reveals the list as far as that heading before the browser scrolls to it; the seven days link to their headings by fragment.

### 8. Last-visit line

`returning.ts` gains one pure function: given the dates of the rows in view and the kept visit, the index the line goes before, or none. The script inserts the line and removes it again when a kind or a narrowing leaves nothing dated in the span above it. It uses the same kept value and the same span as the since line, so the two never disagree. On a wide screen the side column holds one sentence with the counts and a link to the line.

The since line itself is unchanged and moves down with the four lists, whose rows keep their "New" tags.

### 9. Phone

Order on a phone: band, dated head (the day as one line; the sentence under it is not drawn), the seven days, the kind controls without counts in one row, "Narrow these lists", the first heading, its rows. The line for promises to come is drawn after the first heading's rows. The side column is not drawn; the last-visit line needs no link to it.

To make room, the opening band's lede is not drawn below the breakpoint (the title and the field's label say what the page is). With the band at about 400 px this puts the first row near 680 px. A page test measures it at 375 by 812 and fails over 812.

*Alternative considered:* keep the lede and drop the seven days on a phone. The seven days are what make the page look different from one visit to the next.

### 10. The carried headline

The view-transition name moves from the Headlines table's rows to the day-by-day list's report rows, so each name is on the page once. A merged row carries the name of its first report. The older claim's row carries none, because its report has a row of its own further down.

### 11. Weight

Every row is in the page as built: about a hundred report rows and a few dozen others on today's export. The compressed size of the home page is measured before and after on a build from the published export and written into DESIGN.md beside the claim page's figure. Outlet icons are already content-versioned files, so a repeated icon costs one address per row.

## Risks / Trade-offs

- [A stale build looks dated] The head names the last check plainly; if the pipeline stops, the day stops. → That is the honest reading, and the footer already says the same. No mitigation beyond running the pipeline daily.
- [The first row misses the phone's first screen] The budget is about 130 px. → The page test measures it; the order in decision 9 is fixed, so the lever left is the head's spacing.
- [Sentences read as a verdict] "14 years before this report" is a count, but a reader may take it as a comment. → Templates state counts and dates only, the guard bans interval adjectives, and the operator reads every template before it ships (a task).
- [Two things say "since your last visit"] The line in the new list and the since line above the tabs. → Same value, same span, tested together.
- [Record rows are few] About a dozen in ninety days today, so most headings hold reports only. → The kind control shows them alone; the count will grow with the number of claims.
- [Home page weight grows] → Measured and recorded (decision 11); the reveal control does not reduce bytes, only what is shown.
- [The older claim appears twice in the page] Once after the day of the last check, once under its own year. → The first is said to be picked by the date; only the second carries the transition name.

## Migration Plan

One deploy of the static site. No data migration. Rollback is a revert of the site commit; the export and every other page are untouched. Addresses that name a tab, a status, a topic or a page of a tabbed list keep working, because those parameters do not change.

## Open Questions

- The wording of the heading over the four tabbed lists, and of the control that shows earlier headings. Both are the site's own words and are settled in the task that writes them.
- Whether the batch of eight headings is the right step once the list is seen with real scrolling on a phone.
