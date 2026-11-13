# Browse every list a page at a time, from a front page

## Why

The home page shows the ten newest reports and the ten statuses set most recently, and
stops. A reader who wants to explore has no way past the tenth row except the topic and
year pages. Lists on those pages have no such limit, and a year with many claims is one
long table.

## What changes

- The home page becomes a front page: four lists over the same claims, one shown at a
  time behind tabs. Headlines (newest report first), Status changes (newest change
  first, with the status before), Promises (earliest promised date first) and No signal
  (most years first). Each is read ten rows at a time.
- Above the lists, the path shows how many claims are at each status and a reader can
  pick one; a topic choice sits under it. Both narrow all four lists at once, and the
  path's counts follow the topic.
- Under the lists, "On this day": the claims first reported on the reader's own date
  in an earlier year, or those of the next date that has one.
- "Statuses set most recently" is replaced by Status changes: a batch of statuses set
  on one day said nothing about what had moved.
- Every claim list (topic, year, source, approvals, a claim's related claims) shows 25
  rows at a time with the same pager. The status filter on topic and year pages narrows
  the whole list, not the page in view.
- All rows stay in the page. Without JavaScript, in print and to a search engine the
  list is whole.
- The list and the page in view are kept in the page's address (`?view=moved&moved=2`), so going back from a
  claim returns to the same rows.

This replaces "at most ten" in `recent-headlines` (Recent reports on the home page).

## Not in scope

- A ranking by what readers look up. It would need a record of readers' questions.
- Separate addresses per page (`/headlines/2`). See `design.md`.
