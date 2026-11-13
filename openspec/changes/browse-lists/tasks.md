## 1. Pager

- [x] 1.1 Work out the rows of a page in a pure function; verify the site tests "More rows than one page", "A list that fits one page" and "A page that does not exist" pass
- [x] 1.2 Add the pager under the home page's two lists and under every claim list; verify the built home page from the fixture has no row held back and a hidden pager
- [x] 1.3 Make the status filter narrow the whole list and reset the pager to its first page
- [x] 1.4 Look at the home page and a year page at desktop and phone widths with the published export; verify Next and Previous step through every row and the address keeps the page
- [x] 1.5 Verify `make check` passes

## 2. Front page

- [x] 2.1 Put status changes, dated promises and no-signal claims in order with pure functions; verify the site tests "Status changes, newest first", "Promises in order of their date" and "Longest without a new record" pass
- [x] 2.2 Show the four lists on the home page behind tabs, each with its count and pager; verify the site test "Lists on the home page" passes
- [x] 2.3 Look at each list at desktop and phone widths with the published export; verify the tab is kept in the address and nothing overflows
- [x] 2.4 Verify `make check` passes

## 3. Narrowing the front page

- [x] 3.1 Move the status filter into its own component, usable over one table or every table in a scope; verify the year page still narrows and pages as before
- [x] 3.2 Show the path with counts above the home page's lists and narrow all four by the picked status; verify the site test "Counts on the path" passes
- [x] 3.3 Add the topic choice, with the path's counts following it; verify the site tests "Narrowing to a topic" and "One topic" pass
- [x] 3.4 Look at the home page at desktop and phone widths with a status, a topic and both picked; verify counts, the empty-list line and the address
- [x] 3.5 Verify `make check` passes
