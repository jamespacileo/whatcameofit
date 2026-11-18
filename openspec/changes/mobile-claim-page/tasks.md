# Tasks

## 1. Status card

- [x] 1.1 Add `digestApproval` to `site/src/lib/record-brief.ts` and draw its sentence in the status card after what the status means. Verify: record-brief test "Phase 3 status with no approval listed".
- [x] 1.2 Cap the "Why this status" list at the three latest records, with the count and a way to the timetable when there are more. Verify in the browser on a claim with 44 such records.
- [x] 1.3 Give `Pop.astro` a `close` option: a "Close" control held at the panel's foot. Use it on the two panels of the status card. Verify in the browser at 375px.

## 2. Line under the title

- [x] 2.1 Draw the byline under the title: the unchecked wording with its link, then the last-checked day. Remove the notice under the status card. Verify: site test "Preview build".
- [x] 2.2 Make the two links under the title a fingertip tall on a phone. Verify: measured at 375px.

## 2b. Second pass

- [x] 2b.1 Shorten the status card's trial count; `phase4Note` in the status panel. Verify: record-brief test "A status that names a phase counts the trials' states beside it".
- [x] 2b.2 Lift a fact row's links over the row's press. Verify in the browser: the centre of "See the posted results" reaches the link.
- [x] 2b.3 Drop "newest first" from the timetable's note; fingertip-tall moments, fold lines and marked words on a phone. Verify: measured at 375px.

## 3. Records

- [x] 3.1 Update DESIGN.md: the byline, the panel's close control.
- [ ] 3.2 `make check` passes; the claim page checked in the browser at phone and desktop widths, light and dark.

## 4. Status panel controls and Phase 4 context

### P2

- [x] 4.1 <a id="task-f32"></a>Separate the close button from hover-opening behavior. Test one-click dismissal on a hover device and retain keyboard and touch dismissal. [F32](../../../docs/reviews/2026-11-17-code-review.md#finding-f32) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-one-press-closes-a-hovered-status-panel)

- [x] 4.2 <a id="task-f35"></a>Determine Phase 4 note visibility from the trial records independently of the path diagram. Render the off-path ibuprofen/COVID example, an on-path claim and a claim without Phase 4 trials. [F35](../../../docs/reviews/2026-11-17-code-review.md#finding-f35) · [Acceptance scenario](specs/site-publishing/spec.md#scenario-a-phase-4-trial-is-present-with-an-off-path-status)
