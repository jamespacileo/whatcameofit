# Tasks

The mocks in `.impeccable/mocks/examine/` are the reference for look and behaviour (`claim.html`, `claim-promise.html`, `topic.html`, with `mock.css` and `mock.js`). UI work goes through Impeccable; module and test work follows the repository's engineering conventions.

## 1. Status explanation lists only the deciding events

- [x] 1.1 Add tests in the pipeline's status rule tests for the five scenarios of "Status explanation" (Phase 2 claim, Trial registered with three trials, started known only from completion, earlier-phase trial beside the deciding one, No trial found) and verify the first four fail against the current rules
- [x] 1.2 Change `pipeline/src/thenwhat/status/rules.py` so a trial status is explained by each standing trial's registered event, and a phase status by the registered event and the started (or, with no started event, completed) event of each standing trial at the furthest started phase; leave approved, retracted, failed and terminated as they are; verify the new tests pass
- [x] 1.3 Update the pipeline tests that assert `explained_by` (`test_export.py`, `test_organisations.py`, `test_seed.py`) where the expected list changes, regenerate `site/data/seed-export.json`, and verify `site/export.schema.json` is unchanged and the pipeline suite passes
- [x] 1.4 Read `site/src/lib/open-data.ts` and `site/src/pages/for/researchers.astro` where they describe `explained_by`, correct any wording that says every event of a trial is listed, and verify `make check` passes

## 2. Frame components

- [x] 2.1 Add a slot to `site/src/layouts/Base.astro` between the masthead and `<main>`, a skip link as the first element of every page and an id on `<main>`; verify on a built page that Tab reaches the skip link first and that it moves focus to the content
- [x] 2.2 Add `Band.astro`, `Frame.astro` and `FoldSection.astro` with their styles in `site/src/styles/global.css`, adding the ground token and the wide-screen breakpoint; verify in the browser preview with placeholder content at 375, 900 and 1280 pixels wide that nothing scrolls sideways
- [x] 2.3 Add the head script that marks scripting as on and the fold script (press, link into a section, explicit state), with the CSS that sets a section's first state from its declared start; verify that a section declared folded never paints open on load, and that with scripting off every section is open
- [x] 2.4 Add the section-list component: names, counts, the section in view marked, and on a narrow screen the row that keeps the marked name in view and fades at an end with more beyond it; verify by scrolling a long page at 375 and 1280 pixels wide

## 3. Claim page

- [x] 3.1 Move the breadcrumb, title, reports followed and status panel of `site/src/pages/[slug].astro` into the band, with the status panel headed "Where it stands"; below the phone breakpoint show the first report and the follow and share controls at the top of the content, with one link to the rest; verify the scenarios of "Claim and topic pages open with a band" and "The band stays short on a phone"
- [x] 3.2 Wrap each section in `FoldSection`, keeping the ids `timetable`, `trials`, `papers`, `others` and `pass-on`, with papers, organisations and background starting folded and only the record in brief and the timetable open on a phone; verify the four scenarios of "Sections of a claim page fold"
- [x] 3.3 Put the follow, share, check-again and report-an-error controls in the actions column, before the content in source order; verify "Tabbing into a claim page" and that the focus ring is visible on a link inside the status panel
- [x] 3.4 Change `site/src/lib/timetable.ts` to return years newest first with promises beside records, gaps, and one pair of counts for promises and records; update its tests and verify "Records from 2021 to 2026 with none in 2024 and 2025" and "Promise for a year still to come"
- [x] 3.5 Keep the timetable as the site's table by year (operator's decision, 15 Nov 2026), newest first from the library's output, with each entry's kind in words for a screen reader, the key above it, and every label reading the one pair of counts; verify "Four promises and seventeen records" on the published claim with a dated promise
- [x] 3.6 Add the controls that narrow the timetable to one kind, with recounted year labels and the announced message, shown only when more than one kind is present; verify "Registry records only" and "One kind only", and that with scripting off every entry shows
- [x] 3.7 Rebuild `Trial.astro` and the trials section as a table with rows that open, keeping the first-five rule and the wording of every fact; verify "Three finished trials" and "The same table on a phone", and that the existing trial-facts tests still pass
- [ ] 3.8 Move match scores in `Paper.astro`, `Background.astro` and the trial detail into the notes, worded "Match to this claim: <band>, <percent>"; verify "Paper matched at 100%" and that "Confidence is shown with an event scored below certain" still holds for timetable events
- [ ] 3.9 Render "Other claims in <topic>" through the claim table with the link to all of the topic's claims beside the heading; verify the link is reachable and is not inside the fold control

## 4. Topic page

- [ ] 4.1 Give `site/src/pages/topic/[vertical].astro` the band (title, summary sentence, counts by status in words) and the frame with the other topics listed beside the claims; verify "Topic with one claim at each of two statuses" and "Topic among ten"
- [ ] 4.2 Add the word filter to `ClaimTable.astro` beside `StageFilter`, applied with the status to the whole list before paging and recorded in the address, with the count, its announcement and one control that clears both; verify "A word that matches one claim" and that picking a status on page two still returns to page one
- [ ] 4.3 Add the message shown in place of the table when nothing matches; verify "Nothing matches"

## 5. Print

- [ ] 5.1 Add print rules: folds open by CSS, addresses after outside links, masthead links, breadcrumb, section list and actions left out, basis mark and marked place drawn without backgrounds, band in ink on white; add the print handlers that show every timetable entry and restore the screen afterwards; verify both scenarios of "A printed claim page is whole" from the browser's print preview with scripting on and off

## 6. Tests, records and checks

- [ ] 6.1 Add one test per new scenario to `site/tests/site.test.mjs` and update the tests that read the status panel's place, the timetable's order or a trial entry's markup; verify the site suite passes
- [ ] 6.2 Update `DESIGN.md`: the navy band beside the masthead and footer, the 78rem frame with side columns and its breakpoint, the ground token, the newest-first timetable, trials as table rows, the fold pattern; add any new term used in site copy to `GLOSSARY.md`; verify both files name the new elements and that no rule in DESIGN.md contradicts the built pages
- [ ] 6.3 Run `make check` and verify ruff, ty, pytest, the site tests, the site build and the extension tests pass
- [ ] 6.4 In the browser preview at 375 by 812, 900 and 1280 pixels wide, open the seeded claim with a dated promise, a claim with no trial and a topic page; verify no sideways scroll, no console error, and that each matches its mock; then run `/impeccable critique` on the claim page and record the score in the pull request

## Workflow follow-up

- Three pull requests in the order given in design.md, section 8. The operator merges; deploy is `make deploy` from main.
- Archive the change after the last pull request is merged.
