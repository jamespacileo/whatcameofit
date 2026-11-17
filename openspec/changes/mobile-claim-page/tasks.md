# Tasks

## 1. Status card

- [x] 1.1 Add `digestApproval` to `site/src/lib/record-brief.ts` and draw its sentence in the status card after what the status means. Verify: record-brief test "Phase 3 status with no approval listed".
- [x] 1.2 Cap the "Why this status" list at the three latest records, with the count and a way to the timetable when there are more. Verify in the browser on a claim with 44 such records.
- [x] 1.3 Give `Pop.astro` a `close` option: a "Close" control held at the panel's foot. Use it on the two panels of the status card. Verify in the browser at 375px.

## 2. Line under the title

- [x] 2.1 Draw the byline under the title: the unchecked wording with its link, then the last-checked day. Remove the notice under the status card. Verify: site test "Preview build".
- [x] 2.2 Make the two links under the title a fingertip tall on a phone. Verify: measured at 375px.

## 3. Records

- [x] 3.1 Update DESIGN.md: the byline, the panel's close control.
- [ ] 3.2 `make check` passes; the claim page checked in the browser at phone and desktop widths, light and dark.
