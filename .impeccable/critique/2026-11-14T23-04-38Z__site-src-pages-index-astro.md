---
target: "home page, day-by-day list (openspec home-day-by-day): finish review against the change's contract"
p0_count: 0
p1_count: 4
p2_count: 6
target_path: site/src/pages/index.astro
timestamp: 2026-11-14T23-04-38Z
slug: site-src-pages-index-astro
---
Method: one finish reviewer (Impeccable), given the change's proposal, design and spec delta, DESIGN.md, PRODUCT.md, the approved mock (`.impeccable/mocks/frontpage/mix-days.html`), the source of the new components, a static build from the published export, and six captures: 1280 wide (top, head with controls and side column, report rows) and 375 by 812 (first screen, report rows, a week heading with a promise). The fixes were then checked in the `site-published` preview.

Not judged, because no capture existed: a registry row, a promise row and a "Changed" row as drawn, the last-visit line, the opened list of promises to come, the four tabs on a phone, print, keyboard focus, hover, a forced palette, and a page opened on a later day than its check. Findings on those came from the source and the built page.

## Verdict

The page keeps the mock's topology, its three grounds and its wording rules, and nothing in the captures is broken at 1280 or 375. Disposition: fix before shipping. No P0.

## Findings and what was done

| # | Sev | Finding | Done |
|---|---|---|---|
| 1 | P1 | "Go to where you left off" led nowhere when the last visit fell under a heading not yet shown; the note counted rows without saying of what kind | Fixed: the link opens the list as far as the line, on a press as well as from the address; the note names the kinds ("40 reports, 6 registry records"). Checked with a kept visit of 12 Oct |
| 2 | P1 | A headline of one line was a 24 px target on a phone | Fixed: 44 px minimum |
| 3 | P1 | The four kind controls would widen the page at 320 px (by arithmetic) | Fixed: they wrap under 22rem. Checked at 320: no sideways scroll, two rows |
| 4 | P1 | The operator has not read the sentence templates (task 2.3). One to settle: "none with results posted" states a zero, while a zero of completed trials is left out | Open: the operator's to decide |
| 5 | P2 | The day of the last check was announced as the current date to a screen reader | Fixed: it is marked as the checked day; the script marks the current date only when it is the reader's own |
| 6 | P2 | The seven days kept their full counts and led to hidden headings while the list was narrowed | Fixed: a cell counts the reports left under its heading and leads nowhere while that heading is not shown |
| 7 | P2 | No rules for a forced palette or for print in the new parts | Fixed in part: outlines and edges with a forced palette; a row is not split across sheets and a heading stays with its first row. Still open: with scripting off, promises to come stay folded on paper |
| 8 | P2 | A phone dropped counts the spec requires, and the two-form wording was doubled for a reader without the styles ("Saturday 14 November 202614 Nov 2026", "EverythingAll") | Fixed: counts are clipped, not removed; the heading is the long date once, with the parts a phone leaves out marked; the first control reads "All" at every width |
| 9 | P2 | A topic that wrapped under the outlet touched the headline on a phone | Fixed: space under the grey line |
| 10 | P2 | "Trial registered. A trial in people is registered" stands above "3 trials on record, 3 completed, 3 with results posted" (the Tourette device claim) | Open: checked against the export, the count and the status rest on the same three approved records; their phase is "not applicable", and the status rule counts a trial as started only with a phase. Four published claims are in this position. The gloss, or the rule, is the operator's to decide |

## Still open after this review

- Findings 4 and 10: the operator's decisions, recorded in the change's `notes.md`.
- On paper with scripting off, the promises to come are inside a folded section.
- No capture of keyboard focus, hover, print or a forced palette was made; the forced-palette and print rules were written from DESIGN.md's Resilience section and have not been seen.
