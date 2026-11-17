# Proposal

## Why

On 2026-11-17 the operator asked for every section of a claim page below "At a glance" to be rebuilt to the simplicity that section had gained: primary information in sight with the least copy, shapes where words can go, and the rest down a funnel, as "At a glance" goes from label and value, to definition and source, to why it matched. Twenty-one variants of nine sections were mocked from three real claims (`.impeccable/mocks/sections-rebuild/`), and the operator picked one or two for each.

## What Changes

One rule for every section: **in sight**, a label and its value with a number or a shape; **one press**, what it means and where it is from; **a second press**, why it is listed and how sure the reading is.

- **The record in brief** (picks C and A together). One plain sentence gives every answer, each figure a link to its row. The answers are rows of a fact sheet: the question, the answer, and a bar where the answer is so many of the claim's trials. A row opens to what the answer means; where it was read from is a press further in. The two group names are gone.
- **What the report said** (pick B, with A's order as a choice). Under its report a statement stands in a group named in the label's column: who said it, or what kind of statement it is, as the reader chooses. A row is a tag, a mark for how firmly it was put (full: as a fact; a broken ring: as a possibility) and the statement, its figures in bold. It opens to what the report gave as its basis. **The score moves**: how sure the reading is stands a press further in, and stays on the row only when the check is less than very sure (below 0.8).
- **Recorded** (pick B). The section opens on the record's moments in order on one line, each leading to its year. The strip, the filter and the timetable are one press under it.
- **Trials on record** (pick A, in part). Over the table, a mark a trial under its phase, in the shape of its state and ringed where results are posted; a size bar under each trial's head count.
- **Possible registry records** (pick A, in part). A possible record's title carries the dotted ring.
- **Papers on record** (pick A). A group's papers stand newest first under their year; a row is the title on one line, the kind of paper and how many trials it is tied to, by mark.
- **Organisations named** (pick A). Two rows of a fact sheet, the names of each part beside its label; a name opens its part, its trials and what a registry says of it.
- **Other claims** (pick A). A name, a place on the path and a date.
- **Keep or pass on** (pick A). Sharing, reminders, following, the feed and the embed are rows of one section, replacing "Pass it on" and "Check again later". `#check-again` is now the reminders' row.

## Not in this change

Asked for by the operator and not buildable from the export as it stands: a statement as a verbatim snippet (the site stores and shows no article text: a rule of the project), a speaker's name and icon (the export carries a role, never a name), and the most important part of a statement highlighted (nothing marks it; figures are set in bold by rule instead).

## Impact

`site/` only: components, `styles/global.css`, `scripts/folds.ts`, `lib/record-brief.ts`, `lib/statements.ts`, tests. No change to the export.
