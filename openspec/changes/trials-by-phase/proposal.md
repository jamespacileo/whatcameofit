# Proposal

## Why

The trials table on a claim page (change `page-frame`) gives every trial five columns: the trial, compared with, design, state and results. On the ivonescimab page, with 15 trials and none with posted results, two of the five columns say the same thing on every row, each row carries two competing links, and what tells the trials apart (what each sets out to measure, who runs it) is only inside the row's fold. Only five trials are shown; the other ten are one press away under one control.

Four directions were mocked on that claim's data (`.impeccable/mocks/trials-table/index.html`). On 16 Nov 2026 the operator chose B, "grouped by phase".

## What Changes

- The trials section is grouped by each trial's furthest phase, furthest first. Each phase is a heading with its number of trials and, when any have them, how many have posted results. A Phase 1/Phase 2 trial sits with Phase 2, and the group's heading names both wordings. Trials with no phase are in a last group, "No phase given".
- Each trial is one row: people, compared with, main measure in the registry's words (with who runs it under it), state (with "Results posted <date>" under it when posted), and the trial's identifier. The design moves into the row's fold, next to the registry's own terms. The identifier leads to the trial's page on this site when there is one, else to the registry; the registry link is also in the fold's notes.
- Each phase shows its first ten trials; the rest of that phase open on request, from a control that counts them and their posted results. The first-five rule across all trials goes.
- Only the first phase's table shows the column names; the others carry them for a screen reader.

## Impact

- `site/src/lib/trial-facts.ts` (`phaseGroups`, `TRIALS_PER_PHASE`), `site/src/components/Trial.astro`, `site/src/pages/[slug].astro`, `site/src/styles/global.css`, `DESIGN.md`.
- Modifies "A long list of trials opens with the furthest" in `site-publishing`, and the column list of "Trials read across as a table" in the `page-frame` change, which is not yet archived.
