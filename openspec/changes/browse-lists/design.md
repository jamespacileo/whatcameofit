# Design

## Paging happens in the page, over rows already there

Every row is rendered at build time. Rows after the first page carry `data-later`,
hidden by `@media (scripting: enabled)`, so nothing jumps on load. One component,
`Pager.astro`, owns which rows are visible; the status filter marks rows `data-out`
and tells the pager to redraw.

Chosen over built pages (`/headlines/2`) because:

- The status filter must narrow the whole list. With built pages it could only narrow
  the page in view.
- No-JavaScript readers, print and crawlers keep the whole list, as the site already
  promises for topic pages.
- One mechanism serves every table.

Cost: the home page carries every report (104 today). Revisit with built pages when
the home page's HTML passes about 500 KB or 1,000 reports.

## Page sizes

Ten on the home page, where two lists share the page with the lookup. Twenty-five on
claim lists, which have the page to themselves.
