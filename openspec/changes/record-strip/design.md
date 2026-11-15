# Design

## Context

See `proposal.md` for why. What shapes the approach:

- The site is static Astro, built from one export; nothing may need a script in the browser.
- `site/src/lib/row-sentences.ts` already builds the row sentences by fixed rules and fails the build on verdict wording. `DayReport.astro` shows them; `ClaimTable.astro` draws every claim list table.
- Published data on 2026-11-15: 84 claims; dated records per claim 0 (44 claims) to 79; first record to last check 0 to 21 years; 58 claims first reported in 2026; 16 of 53 promises hold a date, several after the last check; record kinds are trial registered (237), trial status change (278), results posted (38), follow-up paper (3), regulator's decision (2), retraction (1).
- `DESIGN.md` rules that bind: amber and a dashed rule mean "promised" and nothing else; the stage track marks a place and is never filled; nothing says whether a promised date has passed; every trial is drawn at one size; status is never by colour alone.
- Operator decisions of 2026-11-15, taken in the critique and the brief: status label stays in sight, repeated captions move to a key and text alternatives; one shared scale; numerals beside the strip; home rows and tables first; trials keep one size.

## Goals / Non-Goals

**Goals:**
- One graphic, one module, reused unchanged by rows and tables, and later by cards and the embed.
- A reader compares claims by looking down a column of aligned axes.
- The strip adds no judgement the sentences did not already carry.

**Non-Goals:**
- No interaction, tooltip or animation.
- No per-kind detail of registry records (registered, started, completed): that belongs to the claim page timetable.
- No removal of the status gloss from list rows in this change.

## Decisions

1. **Marks: five shapes plus an end stop.** News report: hollow ring centred on the axis. Registry record (trial registered, trial status change, follow-up paper, retraction): short vertical tick through the axis. Results posted: small solid square set above the axis. Regulator's decision: solid diamond on the axis. Promised date: amber dashed flag rising from the axis, the only non-ink colour, matching the site's existing meaning of amber. Last check: a full-height end stop at the right end.
   - Why: at about 20 px high, more than five shapes cannot be told apart. Results and decisions are the records a reader most needs to find, so they get their own shape and the square its own lane. A retraction stays a plain tick because the status label already says it and a distinct mark would read as a verdict.
   - Alternative rejected: one shape per record kind (seven shapes); colour per kind (fails colour-alone and print).

2. **True dates, overlap allowed, results never hidden.** Each mark sits at its date. Dense claims form a band of ticks; the square sits above the axis so it is never covered. Counts are given in numerals beside the strip.
   - Alternative rejected: binning by year with stacked units; it reads as a bar chart of activity and invites "more is better".

3. **Shared scale fixed at build.** Axis start = January of the earliest dated record year among published claims, floored to a multiple of five; axis end = the export's last-checked day. Faint gridlines every five years; year labels appear once, in the key or column head, never per row.
   - Why floor to five: the start moves rarely, and gridlines land on round years.
   - Alternative rejected: fixed 25-year window (drops or clips an older record without saying so); per-claim scale (rows cannot be compared; operator chose shared).
   - Consequence accepted by the operator: most claims reported in 2026 show a ring near the right end and an otherwise empty axis.

4. **The axis is never weakened.** One stroke, text colour, full length. No fill between marks, no arrowheads, no growth. This is the strip's version of "the track is never filled".

5. **Promises.** A flag is drawn only for a promise whose date the export holds and which is on or before the last check. Later dates are left to the home page's existing "promised dates after the last check" line. The flag is identical whether or not a record follows it.

6. **One pure module, one component.** A pure function in `site/src/lib` takes an exported claim, the axis start and the last-checked day and returns marks (kind, position as a fraction of the axis) and counts. A component renders them as inline SVG with strokes and fills in `currentColor`, except the promise flag, so print and forced colours keep every mark. Pure function gets the tests; the component is covered through the page tests.

7. **Text alternative.** `role="img"` with an accessible name made of the existing row sentences. When no sentence applies, a base sentence from counts: number of reports, and that no dated record is on file as of the last check. The base sentence is added to `row-sentences.ts` so it passes the same neutrality checks. The same name is used in tables.

8. **Counts line.** Wording owned by the site lib, numerals first: trials on record, and trials with results posted when at least one. A claim with no trial shows "0 trials": an explicit empty state, not a blank.

9. **Layout.** Table: own column, fixed width (about 144 px), so axes align. Phone: full row width under the status. Report row: under the status, counts line to its right on wide screens and under it on a phone.

10. **Key.** A small inline legend drawn with the same component marks, each with its word. Home: beside the existing kind pills. Tables: under the table's heading. Words pass the verdict check.

## Risks / Trade-offs

- [An empty axis after a report reads as "abandoned"] → Axis at full weight to a solid end stop labelled in the key as the last check; no fading; guide entry says what an empty stretch does and does not tell.
- [Most strips are nearly empty today, so the column looks sparse] → Accepted by the operator as honest; the column fills as backfill adds older claims.
- [Dense band of ticks on a 79-record claim is illegible as individual records] → Intended at this size; numerals give the count and the claim page gives the records.
- [Axis start shifts when an older record is published, moving every mark] → Floor to five years limits this to rare steps; the page tests assert alignment, not pixel positions.
- [Hidden sentences drift from what the strip shows] → Both are built from the same claim by the same module family; a test checks that each sentence's subject (first trial year, results count) has a matching mark or count.
- [`DESIGN.md` says words carry status and every record line says its kind in words] → Status label stays in sight; the strip is not a status and not a record line; `DESIGN.md` is amended in this change to record the operator's decision.

## Open Questions

- Exact width of the table column once seen beside the status column at 1280 and 1024 px. Decided during build by looking; does not change specs or tasks.
