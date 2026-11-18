# Proposal

## Why

A claim page draws the same few ideas many times, each coded apart: five label-and-value lists, five kinds of record row, four pale panels, three tables and several fold lines, with row padding of 0.6 to 0.9rem, rules in two greys, labels at 0.8 to 0.9rem, notes at 0.82 to 0.9rem, panel padding in four sizes and two table heads (pale on the timetable, navy on the trials). The sections read as built at different times. On 2026-11-16 the operator asked for the page's tables and repeated patterns to be unified and hardened, and left the decisions to the assistant.

## What Changes

- One scale, defined once in `global.css` and used by every list, table and panel on a claim page: row padding (`--row-pad`), the rule between rows (`--row-rule`), label and column-head size (`--label-size`), note size (`--note-size`), panel padding and corner (`--panel-pad`, `--radius-s`), label column width (`--label-col`).
- Every table has the same quiet head: small grey semibold labels on `--table-head`. The trials table gives up its navy head, so the record band is again the page's only navy block besides the masthead and footer.
- The "other N of M" fold line is one rule for trials, papers and registry records.
- A test (`site/tests/primitives.test.mjs`) fails when a family stops taking a value from the scale.

Decided by the assistant under the operator's instruction of 2026-11-16; the navy head on the trials table was the operator's choice earlier the same day (`trials-by-phase`) and is the one prior decision this reverses.

Out of scope: markup. The sections keep their elements and class names; shared components for rows and tables are a later step. The hero band's tones and the two-column "At a glance" from the mock are not part of this change.

## Capabilities

### Modified Capabilities

- `site-publishing`: a claim page's lists, tables and panels share one scale and one table head.

## Impact

- `site/src/styles/global.css`, `site/tests/primitives.test.mjs`, `DESIGN.md`.
