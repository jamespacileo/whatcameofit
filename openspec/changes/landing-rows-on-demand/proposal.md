# Proposal

## Why

The home page is the page a phone opens first, and it held every row of every list. Measured on 2026-11-17 with 970 published claims, at 375 pixels wide: 197,607 elements, of which 193,424 sat inside containers that were not shown, and 2,841 images. The day-by-day list held 101,577 of them, the five tabbed lists 79,287, the calendar of first reports 16,203. An automated detector held the page's main thread for over 100 seconds. Every reader paid for rows that only a reader who pages, narrows or widens a list ever sees.

## What Changes

- The home page as built holds what a reader sees on arrival: the first ten rows of each tabbed list, the day-by-day list's day headings, and no day of the calendar of first reports.
- The rest of each list is a file of rows under `/rows/`, made by the same components that draw the rows in the page. The page fetches a list's file the first time something needs it, once: a step to the next page, a status or topic choice, a count pressed on the line about the reader's last visit, a span wider than the past week, promised dates, or an address that names a later page or an earlier heading. The rows are then narrowed, counted and paged exactly as before.
- The counts on the tabs, the pagers and the line about the reader's last visit are the lists' own from the start: they come from the build, not from the rows in the page.
- While a list's rows are being fetched, the list says so ("Loading the rest of this list."), and is marked busy. If they do not arrive, the list says "The rest of this list did not load." with a "Try again" control. A list is never drawn as whole while it is not: its "nothing for that choice" line, the end of a span and the "earlier rows" control wait for the rows.
- The calendar block fetches the one day the reader's own date picks. The page holds which days have a first report, and in which years, so that the day can be picked without the reports.
- **Scripting off, and paper.** The rows that are not in the page cannot be shown without the script. Each list then says so in the page's own words: how many of its rows are shown, and that every claim is also listed under its topic, with a link to the topics. The same line is printed while a list's rows are not in the page. This replaces "with scripting off, and in print, the whole list SHALL be shown" for the home page's lists only. A topic's and a year's list of claims keep every row in the page.
- The files of rows are not pages. They are served as text, hold no footer, and search engines are asked not to index them.

## Decision to confirm

The operator has not yet agreed to the home page showing less with scripting off. The alternatives were weighed and left out:

- A second page per list that holds every row (for a reader without scripting, and for search engines). It would be a new public page with its own name, title and place in the sitemap, and the day-by-day list's would again be a page of 100,000 elements.
- Keeping every row in the page behind a `<template>` or `content-visibility`. The rows would still be downloaded and parsed by every reader.

Every claim page stays reachable without scripting: from its topic's page, its year's page, and the sitemap.

## Not changing

- What a row shows, the order of any list, what a filter means, the addresses that name a list, a page, a span, a kind, a status or a topic.
- The names given to a headline's place on a claim page (`view-transition-name`) on the rows in the page.
- Every other list of claims (a topic's, a year's): it keeps every row in the page.

## Left for later

- A status or a topic choice fetches the rest of all five tabbed lists, because each tab shows how many of its rows are left. The day-by-day list is fetched whole when a span wider than the past week is asked for. Both are what every reader downloaded before; fetching the day-by-day list a span at a time, and counting a narrowed tab without its rows, would make them lighter still.
