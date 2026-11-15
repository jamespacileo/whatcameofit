# Proposal

## Why

On 2026-11-15 the operator found the home page noisy: under the lookup stood a large dated heading, a tally, a row of seven days, four kind pills, a path of eight status counts, a line on promises to come, headings for days with nothing dated and a column of eighteen topic pills, all before the first headline. A new reader could not tell what to read first. The operator asked for patterns readers already know: choices folded into dropdowns, a span of time chosen as on Reddit, and a muted side column for navigation as on Examine, leaving the list plain.

## What Changes

- The list's head is one word, "Latest", with the day the registries were last checked in grey beside it. The tally and the row of seven days are gone.
- One row of fields above the list: the kind of row, the span of time (past week, past month, past year, all time, counted back from the last check), the status now with its counts, and on a narrow screen the topic. A field that narrows the list is tinted.
- The list opens on the past week. Where a span ends the page says so and offers the next span with one press.
- With scripting on, a heading with nothing under it is never shown.
- Promised dates still to come are offered when the reader chooses promised dates, not above every list.
- The one older claim stands under the list, under its own heading, in every span.
- On a wide screen a side column on the pale ground stands at the left of the list: the note on the last visit, the topics as a plain list with counts, and links to every claim, status changes, approvals and all topics. The topic chips at the foot of the page are not drawn where the column is.
- On a phone the "Narrow these lists" control is gone: the four fields sit two to a row.

- The opening band is centred on one axis with the box as the largest control on the page; under the box are three topics to try and one line saying how many claims are tracked in how many topics. The operator chose this on 2026-11-15 from three sketches of the first screen.
- The page stands on the pale ground with the list as one white sheet. At the right of the list on a wide screen a second quiet column says how a status is set, how to keep up and what the site is not, each with one link.

Out of scope: the wording of the lookup band, the five tabbed lists, the sections under them, and the rows themselves.

## Capabilities

### Modified Capabilities

- `site-publishing`: how the home page's day-by-day list is headed, narrowed and opened.

## Impact

`site/src/components/DayList.astro`, `HomeNarrow.astro`, `site/src/pages/index.astro`, `site/src/styles/global.css`, `site/tests/home-days.test.mjs`, `site/tests/site.test.mjs`, `DESIGN.md`. `StageFilter.astro` is unchanged and still draws the path on topic pages. No change to the export.
