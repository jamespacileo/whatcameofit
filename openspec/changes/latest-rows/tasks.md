# Tasks

## 1. Rows

- [x] 1.1 Add `RowStanding.astro`: the status column as a button (status in words, place on the path, change or no-signal note, counts) and the detail it opens. Verify: home-days tests find the status in the button and the detail under the row.
- [x] 1.2 Rebuild `DayReport.astro` and `DayRecord.astro` on it: report rows lead with outlet, title and claim; registry rows lead with the newest report and show the record as one dated item. Verify: the scenarios of the three modified requirements.
- [x] 1.3 Draw statuses off the path in `StageTrack.astro` for rows. Verify: a test renders "Trials ended early" with no place marked.

## 2. Search

- [x] 2.1 Move the status column of `.hit-row` to the right on a wide screen. Verify in the browser at 1100px and 375px.

## 3. Records

- [x] 3.1 Update DESIGN.md: the day list's rows, the detail button, the panel blue for an on-record item.
- [ ] 3.2 `make check` passes; the home page checked in the browser at desktop and phone widths, light only.
