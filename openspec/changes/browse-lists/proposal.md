# Browse every list a page at a time

## Why

The home page shows the ten newest reports and the ten statuses set most recently, and
stops. A reader who wants to explore has no way past the tenth row except the topic and
year pages. Lists on those pages have no such limit, and a year with many claims is one
long table.

## What changes

- The home page lists every report of a published claim and every claim with a status,
  ten rows at a time, with a pager under each list.
- Every claim list (topic, year, source, approvals, a claim's related claims) shows 25
  rows at a time with the same pager. The status filter on topic and year pages narrows
  the whole list, not the page in view.
- All rows stay in the page. Without JavaScript, in print and to a search engine the
  list is whole.
- The page in view is kept in the page's address (`?headlines=3`), so going back from a
  claim returns to the same rows.

This replaces "at most ten" in `recent-headlines` (Recent reports on the home page).

## Not in scope

- New home page sections (changes this week, promises coming due). Proposed separately.
- Separate addresses per page (`/headlines/2`). See `design.md`.
