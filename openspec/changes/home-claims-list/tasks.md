# Tasks

## 1. The rule

- [ ] 1.1 Add `testedSummary(claim)` to `site/src/lib/record-brief.ts` and rebuild `testedRow` and `resultsRow` on the same counts, with every new string in the module-load `assertNeutral` call; verify `site/tests/record-brief.test.mjs` passes unchanged
- [ ] 1.2 Add tests to `site/tests/record-brief.test.mjs` for "Claim with three trials", "Claim with no trial", "Trials with no results posted" and "Same words as the claim page"; verify they pass

## 2. The column

- [ ] 2.1 Add `site/src/components/TestedCell.astro` and the "Tested in people" column to `site/src/components/ClaimTable.astro` between First reported and Latest promise, with the note above a table of six or more claims; verify on a built topic page that every row carries the column and the note stands once
- [ ] 2.2 Style the column in `site/src/styles/global.css` (widths, the grey line, a labelled line under 40rem); verify in the browser preview at desktop, 390 and 320 pixels that no date breaks, nothing overflows and there are no console errors
- [ ] 2.3 Add tests "Topic page" and "Narrow screen" to `site/tests/site.test.mjs`, update any test that counts the claims table's columns, and verify the site tests pass

## 3. The Claims list on the home page

- [ ] 3.1 Add the Claims view to `site/src/pages/index.astro` after Headlines: its tab and count, its panel with heading, note, table and pager, rows in order of first report carrying `data-status` and `data-topic`; verify on the built home page that the tab shows the list and the address records it
- [ ] 3.2 Verify in the browser preview that the status counts and the topic select narrow the Claims list, that the pager says which rows are in view, and that with scripting off the list follows Headlines under its own heading
- [ ] 3.3 Add tests "Lists on the home page", "Every claim once", "Claims in order of first report", "A list named in the address", "Narrowed to a status", "Narrowed to a topic", "More claims than a page holds" and "Promise beside the record" to `site/tests/site.test.mjs`, updating the existing tests of the home page's lists; verify they pass

## 4. Record and check

- [ ] 4.1 Update `DESIGN.md`: Index tables (the column and its note), Home tabs (five tabs), Headlines table if its wording refers to four lists; verify each names the change
- [ ] 4.2 Run `make check` and verify ruff, ty, pytest, the site tests, the site build and the extension tests all pass
- [ ] 4.3 Open the home page's Claims list, one topic page and one claim page in the browser preview with the published export, and verify three claims' rows against their claim pages' "Tested in people?" answers

## Workflow follow-up

- Archive the change after the PR is merged.
