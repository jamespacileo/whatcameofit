# Design

## Context

See proposal.md for why. What shapes the approach:

- The mocks in `.impeccable/mocks/examine/` are hand-written HTML with their own `mock.css` and `mock.js`. They are the visual and behavioural reference, checked at 375, 900 and 1280 pixels wide. They are not source: nothing in `site/` reads them.
- `site/src/pages/[slug].astro` is 1,233 lines and renders every section inline, with `h2.bar` headings carrying the ids other pages and tests link to (`timetable`, `trials`, `papers`, `others`, `pass-on`). The topic page is 80 lines over `ClaimTable.astro`, which already offers `StageFilter` and `Pager`.
- `site/src/lib/timetable.ts` builds the timetable oldest first and flags each event with `explains` from `claim.status.explained_by`.
- `pipeline/src/thenwhat/status/rules.py` names every event of each deciding trial as explaining a trial status. The spec's scenario for a Phase 2 claim names only the registered and started events, so code and spec already disagree; this change settles it in the spec's favour and extends it to "Trial registered".
- Existing requirements the frame must keep: every row and section present with scripting off and in print; the unchecked notice follows the status panel; the status panel links to the reminders; the promised year in the status panel leads to its year in the timetable; a long list of trials opens with five; no article text; no verdict wording.
- Other changes in flight touch the claim page (`plain-claim-page` not started, `knowledge-cards` and `visible-content-lookup` nearly done).

## Goals / Non-Goals

**Goals:**

- The frame is built once, as components the claim page and topic page share.
- First paint is correct without waiting for script: no section flashes open and then folds.
- One source for each number the page states more than once.
- The status rule change is a pure-function change with its own tests, landed before the site reads it.

**Non-Goals:**

- No change to the home page, to status wording or glosses, or to the export's shape.
- No new client-side framework. Behaviour stays in small scripts beside the components, as today.
- The mock's markup is not copied wholesale. Where the site already has a component for a thing (`StageTrack`, `BasisMark`, `PromiseText`, `Pager`, `SharePill`, `FollowOffer`), the component is kept and restyled.

## Decisions

### 1. Three layout components: band, frame, folding section

`Band.astro` (slots for the main column and the side card), `Frame.astro` (slots for the section list, the actions and the sheet) and `FoldSection.astro` (props: id, title, count note, how it starts on a wide screen and on a phone). `Base.astro` gains a named slot rendered between the masthead and `<main>` for the band, so the band can run the full width while `<main>` keeps its width.

Alternative: restyle the existing markup in place with CSS alone. Rejected: the status panel has to move from the content into the band, and the source order of the actions has to change, neither of which CSS can do.

### 2. A fold is a heading holding a button, and its first state is CSS

Markup: `<h2><button aria-expanded aria-controls>…</button></h2>` followed by the body. The server renders every body present and unhidden. A one-line script in the document head adds a class to `<html>`; with that class, CSS hides a body whose section is declared as starting folded (on any width, or only below the phone breakpoint) until the section carries an explicit open or closed state. The fold script then only writes that explicit state on a press, on a link into the section, before print and after print.

Why: first paint is right with no flash, scripting off leaves everything open, and print has a CSS path that does not depend on the print events.

Alternatives: `<details>/<summary>` puts the heading inside a summary, where assistive technology drops its heading role, and cannot hold the "All claims" link beside it. `hidden="until-found"` keeps the body's padding as a gap and is unevenly supported. Folding from script after load flashes on a long page.

### 3. Timetable order, gaps and counts live in `timetable.ts`

The library returns years newest first, each with its promises and records, the gaps between them, and one `{ promises, records }` pair. The section list, the heading note, the narrowing controls and the screen-reader message all read that pair. The narrowing script recounts from the rendered entries' kinds and never holds its own totals.

Alternative: reverse the list in the template. Rejected: the mocks' second critique found four different totals on one page because each label was written by hand.

### 4. Tables are grids with table roles

The trials table and the claim tables use the mock's structure: a grid whose head row carries column-header roles and whose rows carry row, row-header and cell roles; a trial row is a row group holding the row and its opened detail. Below the phone breakpoint the head row is hidden and each cell shows its own label.

Alternative: a real `<table>` restyled as blocks on a phone. Rejected: changing a table's display drops its semantics in some browsers, and a row that opens needs a second row spanning every column.

The existing rule that a claim with more than five trials shows five is kept: the remaining rows sit in a second row group that the existing control opens.

### 5. The topic word filter joins the status filter and the pager

One narrowing state (status, word) is applied to the whole list, then paged, as the existing requirement for narrowing by status already demands. Both are recorded in the page's address, as the home page already records typed search words. The empty message replaces the table and names what was typed.

### 6. The explanation is narrowed in the status rules, not on the site

`derive` returns, for a trial status, only each deciding trial's registered event and, for a phase status, the event that shows it started. The site keeps marking exactly what `explained_by` lists.

Alternative: keep the pipeline as it is and have the site choose which listed events to mark. Rejected: the site would be deciding what explains a status, which belongs to the rules, and other readers of the export would still get the long list.

`site/data/seed-export.json` is regenerated. The schema does not change. `open-data.ts` and `for/researchers.astro` describe the field and are checked for wording that says "every event of the trial".

### 7. Breakpoints

The frame needs two: one below which the side columns give way (the section list becomes the row of chips, the actions join the band), and the site's existing phone breakpoint for the short band and phone folding. The second reuses the site's existing value, not the mock's. The first is new and is recorded in DESIGN.md.

### 8. Order of work

Three pull requests, each leaving `make check` green: the status rule and regenerated seed export; the frame on the claim page; the topic page, print and DESIGN.md. The first is independent of the others.

### 9. Found while building

- The site already had a pale band (`.band`) on the home, about, extension and audience pages, and `Base.astro` already had the band slot, the skip link and the id on `<main>`. The operator decided on 15 Nov 2026 that claim and topic pages take the navy band and the other pages keep the pale one: pale for a page's task, navy for a record's status. DESIGN.md records both.
- The folding heading is one component, `FoldHead.astro`, put in place of each section's `h2`. Everything after it in its section is the fold's body, hidden by a sibling rule, so no section needed a wrapper and the components that own their heading (`RecordBrief`, `Statements`, `Organisations`, `Background`) changed by one line each. This replaces the `FoldSection` wrapper named in decision 1. Its script is `src/scripts/folds.ts`, loaded by the base layout, so that no section's markup holds a script.
- The timetable stays the site's table (year, promised on amber, recorded), reversed to newest first, with the controls that narrow it. The operator chose this over the mock's line with dots on 15 Nov 2026: the table already sets a promise beside its record and names a gap.
- The topic page already had a status filter (`StageFilter`: the path with a count at each place). The word filter and the nothing-matches message were added to it, so one component owns the narrowing; the band carries the summary sentence and no separate card of counts, which would have said the same numbers a third time. On a topic page neither pick is written to the address, as before; decision 5's "recorded in the address" applies to the home page only.
- The actions keep their words (Follow, Share, Check again later, Report an error) beside their icons, in place of the mock's icon-only column: the first critique found the icon-only column unexplained without hover.

## Risks / Trade-offs

- [The claim page template is being restructured while three other changes touch it] → Land the status rule first; rebase the frame work on main immediately before starting and keep it to one pull request for the claim page.
- [Tests in `site/tests/site.test.mjs` read the current markup] → Keep the section ids and the status panel's class names where possible; update the tests that read position or order in the same commit as the markup they read.
- [Folded content and search] → Folded bodies stay in the built page, so the search index and find-in-page on a wide screen still reach them. Find-in-page will not open a folded section; accepted.
- [The band is still tall on a phone: about 910 to 965 pixels before the content in the mocks] → The requirement sets 1,000 pixels as the limit and the status in the first screen. Cutting further means dropping the status card's fact rows on a phone, which is left as an open question.
- [Fewer events marked as the basis may read as less evidence] → The "Why this status" note lists the same events the marks show, and the trials table still shows every trial.
- [Navy band on every claim page changes the site's look more than any change so far] → DESIGN.md is updated in the same pull request, and the band uses the footer's navy and existing on-navy colours only.

## Migration Plan

No data migration. The export's shape is unchanged; a site built from an older export still builds and simply marks more events. Deploy through `make deploy` from main after the operator merges. Rollback is reverting the pull request; the status rule can be reverted on its own.

## Open Questions

- Should the home page take the band later, and should year, source and approved-claims pages take the frame? Neither changes this work.
- On a phone, should the status card drop its four fact rows to bring the content higher? The requirement as written is met without it.
