# Tasks

## 1. Measure

- [x] 1.1 Count the elements of each block of the home page as served (`curl` of the page, parsed). Before: 197,602 elements in 41.6 MB as the development server sends it; the day-by-day list 101,577, the five tabbed lists 79,287, the calendar of first reports 16,203, everything else 535.

## 2. Rows drawn in one place

- [x] 2.1 `lib/home-lists.ts`: the home page's lists worked out once, with their totals, their dates and where the rest of each is.
- [x] 2.2 `FeedRows.astro`, `DayGroups.astro`, `AnniversaryDay.astro`: the rows of a tabbed list, the headings of the day-by-day list and one calendar day, each drawn by the page and by the file of rows with the same markup.
- [x] 2.3 `/rows/<list>.txt` and `/rows/on-this-day/<month-day>.txt`: the files of rows. A list that is whole in the page has no file. `public/_headers` asks search engines not to index them.

## 3. Rows fetched when asked for

- [x] 3.1 `lib/rest.ts`: one loader. A holder names its file; the rows are fetched once, marked by each filter before they are in the page, put in, and announced to what counts and pages them.
- [x] 3.2 The pager, the tab counts, the status and topic choices, the line about the last visit, the day-by-day list's kind, span and headings, and the calendar block ask for the rows when they need them, and read them when they arrive. A row's detail and an outlet's icon behave in an arrived row as in a built one.
- [x] 3.3 `RestSaid.astro`: the loading line, the line and control when the rows do not arrive, and the line read with scripting off and on paper.

## 4. Records

- [x] 4.1 Tests: the built page holds the first rows only, the files hold the rest, the totals match, a list that fits has no file (`site/tests/home-rows.test.mjs`); the day-by-day list's and the calendar's scenarios updated (`home-days.test.mjs`, `site.test.mjs`).
- [x] 4.2 Verified in the browser at 375 pixels wide on the development server: 5,278 elements on arrival; "Next" shows rows 11 to 20; a status narrows every list across all its rows; a tab is switched; a span is widened; a file that answers 503 is said, and "Try again" brings the rows.
- [x] 4.3 `make site-test` passes (789 tests). `EXPORT_FILE=data/published-export.json make site-build` passes with 970 claims: the home page is 367 kB with 5,241 elements; the files of rows are 10.6 MB between them, the day-by-day list's 6.2 MB (512 kB compressed); 332 files of rows among 11,000 files of the 18,000 a build may hold.
- [ ] 4.3a `make check` in full (the pipeline's lint, types and tests were not run for this change: nothing of theirs is touched).
- [x] 4.4 Operator confirms that the home page may show its lists' first rows only with scripting off and on paper (proposal, "Decision to confirm"). Confirmed by the operator on 2026-11-17.
- [ ] 4.5 Checked on the deployed site: a file of rows is served, with the header that asks search engines not to index it.

## 5. Paging, retry and print across home lists

### P2

- [ ] 5.1 <a id="task-f29"></a>Invalidate pending paging intent when the filter changes. Delay the download and verify both the range and page state after filtering. [F29](../../../docs/reviews/2026-11-17-code-review.md#finding-f29) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-a-filter-changes-while-next-is-pending)

- [ ] 5.2 <a id="task-f30"></a>Retain the current action across a failed fetch. Test Next and an older heading, including replacement by a newer action before retry. [F30](../../../docs/reviews/2026-11-17-code-review.md#finding-f30) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-retry-completes-the-original-action)

- [ ] 5.3 <a id="task-f31"></a>Bind row downloads to the HTML's export or recover to a single export. Test Next across a changed ordering, including loss of an older row file. [F31](../../../docs/reviews/2026-11-17-code-review.md#finding-f31) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-a-deployment-changes-the-home-list-order)

- [ ] 5.4 <a id="task-f33"></a>Expose every list's initial rows in print media. Check all five with different active tabs and verify printing does not require downloading later rows. [F33](../../../docs/reviews/2026-11-17-code-review.md#finding-f33) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-printing-after-selecting-a-different-tab)
