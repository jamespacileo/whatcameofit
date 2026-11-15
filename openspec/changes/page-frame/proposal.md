# Proposal

## Why

A claim page today is one white column, 60rem wide, with up to fourteen sections and no way to find one. On a desktop screen the page for the wrist-worn nerve stimulation device is about 8,800px tall, and its status starts 380px down. Research-summary sites such as Examine put the answer level with the title, keep a list of sections in view and let every section fold. Mocks of that frame on our own tokens and wording were built, critiqued twice and corrected (`.impeccable/mocks/examine/`, critiques in `.impeccable/critique/`); the operator chose the deep navy band on 14 Nov 2026 and approved building the frame on 15 Nov 2026.

The second critique also found that the basis marker sits on 12 of 13 timetable entries for a claim whose status is "Trial registered", so it marks nearly everything. The status rules name every event of a deciding trial as explaining the status, where the spec's own scenario names only the registered and started events.

## What Changes

- Claim and topic pages open with a full-width navy band under the masthead. On a claim page it holds the breadcrumb, the title, the report followed and the status panel as a card at the right, so the status is level with the title. On a topic page it holds the title, the summary sentence and the count of claims at each status.
- A claim page lists its sections beside the content on a wide screen, with the count each holds and the section in view marked. On a narrow screen the list is one row of chips that stays at the top.
- Every section of a claim page folds from its heading. Papers, organisations and background start folded. On a phone only the record in brief and the timetable start open, and the band keeps only the breadcrumb, title and status card.
- The timetable reads newest first as a line by year. A year with a promise carries the promise beside what was recorded in it; a stretch with no record is shown as a gap. It can be narrowed to one kind of entry, and promises and records are counted apart on every label, never as one total.
- Trials read across as one table (people, compared with, design, state, results); a row opens for the registry's detail. Match scores of papers and background terms move into the grey notes line, worded "Match to this claim".
- A topic page lists its sibling topics beside the claims, lets the claims be narrowed by a typed word as well as by status, and says so when nothing matches.
- Follow, share, check again later and report an error sit in one column of actions on a wide screen and come before the content for a keyboard. Every page gets a skip link.
- A printed claim page shows every section open, every entry of the timetable, and each source's address after its link.
- **BREAKING** for readers of `explained_by` in the export: a status's explanation lists only the events that decide it (each standing trial's registration for "Trial registered"; the registration and start of the trials at the furthest phase for a phase status). Fewer event ids are listed; the field's shape is unchanged.

Out of scope: the home page (the live page's four lists, narrowing and since-your-last-visit line are ahead of the home mock, which is kept only as a sketch); the claim page's title (change `plain-claim-page` proposes the intervention name as the title and is not yet applied; this frame works with either); the approved-claims, year, source, method and guide pages; cards, feeds, `lookup.json`, the embed and the extension; any new wording for statuses.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-publishing`: claim and topic pages take the band, the section list, folding sections, the newest-first timetable, the trials table, the topic word filter, the actions column, the skip link and the print rules; the status explanation on the page marks only the deciding events.
- `status-derivation`: the explanation of a status lists only the events that decide it.

## Impact

- `pipeline/src/thenwhat/status/rules.py` and its tests: which events explain "Trial registered" and each phase status. `site/data/seed-export.json` is regenerated; `site/export.schema.json` is unchanged.
- `site/src/pages/[slug].astro`, `site/src/pages/topic/[vertical].astro`, `site/src/layouts/`: the frame. New components for the band, the section list, a folding section and the actions column; `Trial.astro`, `ClaimTable.astro`, `StageFilter.astro`, `Paper.astro`, `Background.astro` and `Statements.astro` change.
- `site/src/lib/timetable.ts`: newest-first order, gaps, counts of promises and records kept apart.
- `site/src/styles/global.css`: band, ground, sheet, section list, folds, timeline, table, print. One new token for the ground behind the sheet.
- `site/tests/site.test.mjs`: a test per new scenario; tests that read the status panel's place, the timetable's order or a trial entry's markup are updated.
- `DESIGN.md`: the navy band joins the masthead and footer as an allowed solid navy block; page width 78rem with side columns; timetable order; trials as table rows; the ground token. `GLOSSARY.md` if a new term reaches site copy.
- Other readers of `explained_by`: the "Why this status" note on the claim page lists fewer events. `lookup.json`, the extension and the open-data file are checked for use of the field.
- No new dependency, no personal data, no network call at build or in the reader's browser.
