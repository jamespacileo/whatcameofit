# Proposal

## Why

On 2026-11-17, after the band, the operator asked for the rest of the claim page: it "feels visually disorganised, non cohesive, hard to skim through", with the same research-summary site as the reference. The critique of that day (`.impeccable/critique/2026-11-17T08-06-55Z__site-src-pages-slug-astro.md`) measured it on a claim with 147 records: the timetable is 9,653px, 52% of the page on a wide screen and 67% on a phone; record data is drawn in three container styles (open rows between rules, rounded framed tables, bare lists); and each section opens with a note of a different length and weight.

## What Changes

- **Folded years.** A claim with more than 20 records folds its timetable by year. This year, last year and any year a promise names stay open. An older year is one line that says how many records it holds and of which kinds, carries the basis mark where the status rests on one of them, and opens to the year's records. A link to a record in a folded year opens it; narrowing the table to one kind, or printing, opens every folded year.
- **One container.** Every section's rows stand open between a 2px ink rule and a hairline, as "The record in brief" already is. Tables lose their rounded frame; lists start under the same rule.
- **One opening note.** A section's note is one muted line at the note size. "At a glance" joins the sections whose note is held to a line with "More". The notes that say "not advice" stay whole, as `quiet-sheet` decided.
- **Quieter rows.** In "At a glance" a source's words keep to two lines and where the term is filed shows once the row is open. In the trials table the main measure keeps to two lines and who runs the trial to one.

- **Trials as one table.** The columns are named once and stay in sight; each group ("Results posted", a phase) is a tinted row with its name and count; a trial's row is two lines.
- **Papers and organisations in two columns** from 40rem: what it is at the left, how it is tied to the claim at the right.

Measured on the same claim: the page goes from 18,128px to 8,635px at 1400px wide; at 375px, with the trials folded as a phone draws them, from 15,940px to 7,755px. A trial's row goes from 100px to 77px.

Not in this change: shared components for the row and table markup (`claim-primitives` task 2.1), one format for score chips, the type scale, the two legends over the timetable. A claim with 20 records or fewer is drawn as before.

## Capabilities

### Modified Capabilities

- `site-publishing`: the timetable's folding by year, and the container, opening note and row density of a record page's sections.

## Impact

- `site/src/pages/[slug].astro`, `site/src/components/Glance.astro`, `site/src/components/Paper.astro`, `site/src/scripts/timetable-kinds.ts`, `site/src/styles/global.css`, `site/tests/site.test.mjs`, `DESIGN.md`.
