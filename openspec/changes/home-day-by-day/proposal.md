# Proposal

## Why

The home page answers a reader who arrives with a headline, and gives little to a reader who arrives with none. Its lists are tables of titles and status labels: nothing in a row says what the records add, so scrolling teaches nothing, and the page looks the same on Thursday as it did on Monday. The operator asked on 2026-11-14 for the page under the lookup to be worth scrolling and worth opening a few times a week, chose "Day by day" from eight working mocks (`.impeccable/mocks/frontpage/directions.html`, the chosen one is `mix-days.html`), and asked for the four tabbed lists to stay, lower on the page.

## What Changes

- Under the lookup, the home page gains one list of everything dated for published claims, newest first, under dated headings: a heading per day for a fortnight, per week for the rest of the year, per year before that.
- The list holds three kinds of row, each said in words and told apart by ground: a news report (white), a registry record (pale blue), a promised date (pale amber, as everywhere). Controls above the list show one kind alone and are also the key to the three grounds.
- A news report's row sets the outlet's quoted title beside the record: the evidence stage when first reported, the status now with its place on the path, and at most two sentences built by fixed rules from the claim's records (a regulator's decision, the year of the first registered trial when it is years before the report, how many trials are on record and how many have posted results, that nothing is dated since the first report).
- A registry record's row names the report it belongs to, and says "Changed" with the status before and after when the claim's status changed that day.
- The page is dated: above the list it names the day the registries were last checked and shows the seven days up to it, each leading to its heading. It never presents a later day as checked.
- Promised dates still to come are offered with the list behind one line. The day of the last check always has a heading; after its own rows it shows one claim first reported in an earlier year, picked by the date.
- A reader who has been before sees one line across the list at their last visit, in place of a "New" tag on every row.
- The status path and the topic choice stay above the list and narrow it, as they narrow the four tabbed lists today.
- The four tabbed lists (Headlines, Status changes, Promises, No signal), with their since line, move under the day-by-day list and behave as they do now.
- On a phone the opening band is shortened so that the first row of the day-by-day list starts on the first screen.

Not in this change: no export or pipeline change (every number comes from fields already published), no Follow control on a home page row, no email, no change to the anniversaries block, the topic list or any other page.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-publishing`: the home page gains the day-by-day list and its dated head, row kinds, row sentences, last-visit line and reveal of earlier headings; the requirements for the four orders, paging, narrowing, the since line, the phone's controls and the phone's first screen change to place the tabbed lists under the new list and to make the new list the one a phone opens on.

## Impact

- `site/src/pages/index.astro`: new sections above the tabbed lists, the tabbed lists moved down, the scripts for narrowing, the since line and paging extended to the new rows.
- `site/src/lib/`: one new pure module that builds the list from the export and the last-checked day, and one for the row sentences; `reports.ts`, `changes.ts`, `returning.ts`, `status.ts` and `trial-facts.ts` are read, and `returning.ts` gains the last-visit line.
- `site/src/components/`: row components for the three kinds; `StageFilter`, `StageTrack`, `Outlet`, `PromiseText` reused.
- `site/tests/`: tests for the list module and the sentences against the fixture export, and page tests for the home page as built.
- `DESIGN.md`: the new components, the three grounds and what pale blue now also means in a list, the phone's opening band. `PRODUCT.md`: the home page's capability line.
- Page weight: every row is in the page as built, so the home page grows; the design sets how it is measured.
- No change to the export's shape, `site/export.schema.json`, the pipeline, the extension or the lookup service.
