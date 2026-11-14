# Tasks

## 1. The list model

- [x] 1.1 Add the pure module in `site/src/lib` that builds the day-by-day list from the published claims and a given day of last check (design decision 3): report rows merged per claim per day, record rows for events in the ninety days up to that day, promise rows on or before it, the promises to come, and headings by day, week and year. Verify with a new test file against `site/tests/fixture-export.json` and a fixed day: one test per scenario of "The home page lists what is dated, day by day" and "A report row sets the report beside the record" (two outlets on one day, one claim on two days).
- [x] 1.2 In the same module give the seven days with their report counts, keep a heading for each of the seven even when empty, and return nothing at all when the day of last check is null. Verify with tests for a day with nothing dated and for a null day.
- [x] 1.3 Mark the record row that says "Changed" from `changesOf`, the first of a claim's records on a day its status changed, with the status before and from that day; carry an event's confidence when below 1. Verify with tests for a record that changed a status, a second record the same day, a record that changed nothing, and a paper scored 0.6.
- [x] 1.4 Choose the older claim by the rule in design decision 3. Verify with tests that two calls for one day agree, that consecutive days differ when more than one claim qualifies, and that no claim is returned when none was first reported in an earlier year.

## 2. Row sentences

- [x] 2.1 Add the module that holds the four sentence templates and their order of preference (design decision 4), counting trials as the claim page does and leaving the count sentence out when the export carries no trials for the claim. Verify with tests for the three scenarios of "A report row says what the records add" and for a claim with no `trials` field.
- [x] 2.2 Guard the templates at module load with `assertNeutral`, `assertNoOutcomeVerdict` and the new check for words that characterise an interval or a count. Verify with a test that a template reworded with "still" or "only" throws and names the sentence, and that `make site-build` passes with the templates as written.
- [ ] 2.3 Show the operator the four templates rendered for five published claims and record their agreement, or the wording they change, in this change's notes. Verify the notes file names the day and the final wording.

## 3. The list on the page

- [x] 3.1 Add row components for a report, a registry record and a promised date, reusing `Outlet`, `StageTrack` and `PromiseText`, each saying its kind in words and each carrying `data-kind`, `data-status`, `data-topic` and `data-on`. Verify in the `site-published` preview against `.impeccable/mocks/frontpage/mix-days.html` at 1280 and 375 pixels wide, and with a page test that a registry row's kind is in its text.
- [x] 3.2 Draw the dated head, the seven days linking to their headings, and the list with its headings and counts in `index.astro`, under the lookup and above the status path (design decisions 1 and 2); move the tally line to the head; build neither head nor list when the export has no day of last check. Verify with page tests on the built home page: the head names the fixture's day of last check, no heading is dated after it, an empty day says nothing is dated, and a build from an export with a null day shows the four lists straight after the lookup.
- [x] 3.3 Draw the line for promised dates to come, opening them in place, and the older claim after the rows of the day of last check, said to be picked by the date. Verify with page tests for the count and next date in the line, for the line's absence when nothing is to come, and for the older claim's row.
- [x] 3.4 Move the headline's view-transition name from the Headlines table to the day-by-day list's report rows (design decision 10). Verify with a page test that no transition name occurs twice in the built home page, and by pressing a headline in the preview and seeing it carried to the claim page.
- [x] 3.5 Record the new components, the three grounds and the line on the panel blue in a list in `DESIGN.md`, and update the home page's line in `PRODUCT.md`. Verify both documents name the day-by-day list and that `DESIGN.md` still states that pale amber means "promised" only.

## 4. Controls

- [x] 4.1 Add the kind controls with their swatches and counts, setting `data-out-kind`, hiding a heading whose rows are all out, rewriting a heading's count from the rows left, and recording the pick in the address. Verify with a browser test in the preview: picking registry records leaves only those rows, the address names the pick, and reloading that address shows the same list.
- [x] 4.2 Widen the status and topic narrowing to the new rows and draw the topic choice as the side column's list on a wide screen (design decision 6). Verify with the two new scenarios of "The home page's lists can be narrowed by status and by topic" in the preview, and that the existing narrowing tests for the four lists still pass.
- [x] 4.3 Show the day headings first and reveal earlier headings eight at a time from one control that states the rows remaining; open the list as far as a heading named in the address; hide nothing without scripting or in print. Verify with a page test that every row is in the built HTML, and in the preview that the control counts down and that an address naming an earlier week lands on it.

## 5. Reader state

- [x] 5.1 Add to `returning.ts` the pure function that places the last-visit line among dated rows, using the since line's span. Verify with tests in `site/tests/returning.test.mjs` for a later visit, a first visit, nothing dated in the span, and a kept value in the wrong shape.
- [x] 5.2 Draw the line in script, redraw it when a kind or a narrowing changes the rows in view, link to it from the side column's sentence, and word "Today" and "Yesterday" on a heading from the reader's own date only. Verify in the preview with a kept visit of a week ago: the line stands where the since line's count ends, no row of the list carries "New", and with the clock a day ahead no heading says "Today".

## 6. The four lists and the phone

- [x] 6.1 Move the since line, the tabs and the four lists under the day-by-day list beneath a heading of their own, leaving their behaviour as it is. Verify that the existing home page tests for paging, the four orders and the since line pass unchanged apart from where the lists stand, and that an address naming a tab still opens it.
- [x] 6.2 Lay the page out below the breakpoint as design decision 9 sets: no lede in the band, the head on one line, kind controls without counts in one row, the promises line after the first heading's rows, no side column. Verify in the preview at 375 by 812 that the first row of the day-by-day list starts above 812 pixels, that the kind controls are in view without sideways scrolling, and that every pressed thing is at least 44 pixels tall; record the measurements in `notes.md` (the site's tests run in Node and cannot lay a page out).
- [x] 6.3 Update `DESIGN.md` for the opening band and the home tabs on a phone, and the method page's list of ways to keep up if it names where the since line stands. Verify the documents match the page as built.

## 7. The whole page

- [x] 7.1 Run `make check` and verify it passes.
- [ ] 7.2 Build from the published export, measure the home page's compressed HTML, CSS and script before and after, and write the figures into `DESIGN.md` (design decision 11). Verify the figures are in the document with the day they were measured.
- [ ] 7.3 Have the home page reviewed with Impeccable at 1280 and 375 pixels wide, with scripting off and in print, against this change's `proposal.md`, `design.md` and spec delta; make the fixes it asks for. Verify the review is saved under `.impeccable/critique/` and its open findings are none or are listed in this change's notes.
- [x] 7.4 Bring `.impeccable/mocks/frontpage/directions.html` up to date with one line saying the direction was built and where. Verify the line names this change.

## Workflow follow-up

- Deploy through a pull request to `main`, which the operator merges; `make deploy-check` first.
- Archive the change once it is deployed and the specs are synced.
