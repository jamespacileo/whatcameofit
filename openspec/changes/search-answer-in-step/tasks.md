# Tasks

- [x] 1 The box's script: history steps and popstate, the emptied field, "Try again", the reminder on every untracked article, the link to the answer's heading, the notice said once, the described search button. Verify: `site/tests/home-search.test.mjs`, `site/tests/lookup-component.test.mjs`.
- [x] 2 The line under the field, and the under-box and the example giving way to an answer. Verify on the dev server with the published export at 1024px and 375px, light and dark: a tracked article, an untracked one, a failed word search.
- [x] 3 Word search on a built site (fixture export): the answer, the link to its heading, Back, Forward, Escape.
- [x] 4 `DESIGN.md`.
- [x] 5 Second pass: the true count, the answer brought into view with the box, focus on the answer's heading, the matched name in a suggestion, wording at the dead ends. Verify: `site/tests/home-search.test.mjs`, `site/tests/suggest.test.mjs`; a site built from the published export at 1280x720 and 375px.
- [x] 6 A phone result row that says where the claim stands before its reports, a way to the claims not shown, and a mark on suggestions that open a page: mocked for the operator to choose (`.impeccable/mocks/search-next/`). The operator chose A (status under the headline), E ("Show 20 more") and G (an arrow on rows that open a page) on 2026-11-17. Built; verified on a site built from the published export at 375px and 1280x720: the first "cancer" result 716px to 435px on a phone, 40 rows after one press with the page unmoved, arrows on topics, treatments and reports.

- [x] 7 Keep the next batch stable while the topic changes, count an exact-headline claim once, and restore expanded or filtered searches and pasted-link answers with Back and Forward. Verify with `site/tests/home-search.test.mjs`.

Not checked: a screen reader's reading of the answer and of the described button; the search button's description on a site built with a lookup service (this build has none); Safari and Firefox, where Escape and the field's cross may not empty the field the same way; forced colours.
