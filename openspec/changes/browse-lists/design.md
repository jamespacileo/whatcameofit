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

## The front page is orders over the record, not a ranking

Reddit ranks by votes. This site collects nothing about readers, so each list's order
is a fact of the record: a publication date, a change date, a promised date, a count of
years. No order depends on the day the page is read, so a built page stays true: the
Promises list is in date order and never says "overdue".

Tabs, not four stacked tables: one list above the fold, the others one press away, and
without scripting the four simply follow one another under their headings.

## One stage filter, two scopes

The status filter that sat inside `ClaimTable.astro` is now `StageFilter.astro`. On a
topic or year page it narrows the table after it, as before. On the home page it is
given a scope and narrows every table in the feed. Each filter leaves its own mark on
a row (`data-out` for status, `data-out-topic` for topic); the pager shows the rows
with no mark, so filters combine without knowing of each other.

A feed row is not always a claim (a claim can have several reports or changes), so
the home page names the picked status and does not say "N of M claims".
