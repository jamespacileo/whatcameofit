# Proposal

## Why

The trials table on a claim page (change `page-frame`) gives every trial five columns: the trial, compared with, design, state and results. On the ivonescimab page, with 15 trials and none with posted results, two of the five columns say the same thing on every row, each row carries two competing links, and what tells the trials apart (what each sets out to measure, who runs it) is only inside the row's fold. Only five trials are shown; the other ten are one press away under one control.

Four directions were mocked on that claim's data (`.impeccable/mocks/trials-table/index.html`). On 16 Nov 2026 the operator chose B, "grouped by phase".

## What Changes

- The trials section is grouped by each trial's furthest phase, furthest first. Each phase is a heading with its number of trials and, when any have them, how many have posted results. A Phase 1/Phase 2 trial sits with Phase 2, and the group's heading names both wordings. Trials with no phase are in a last group, "No phase given".
- Each trial is one row: people, compared with, main measure in the registry's words (with who runs it under it), state (with "Results posted <date>" under it when posted), and the trial's identifier. The design moves into the row's fold, next to the registry's own terms. The identifier leads to the trial's page on this site when there is one, else to the registry; the registry link is also in the fold's notes.
- Each phase shows its first ten trials; the rest of that phase open on request, from a control that counts them and their posted results. The first-five rule across all trials goes.
- Only the first phase's table shows the column names; the others carry them for a screen reader.

### After the critique (16 Nov 2026, 22/36)

The operator asked for every finding to be fixed, the pipeline included, and for trials with posted results to lead:

- Trials that posted results come first, under "Results posted", whatever their phase.
- Each trial's arms are exported in the record's words, with whether the claim's treatment is the arm under test or only the comparison (exact name match, else no answer). "Compared with" names the comparator arms, and a trial that tests another drug says so.
- Known registry abbreviations in the main measure are said plainly, once per section. The sponsor carries its kind in the row.
- The opened row says the match and the design once, in two columns on a wide screen. Every table shows its column names, group headings stay in view, and on a phone the identifier is a 44px target opposite the size.

## Impact

- `pipeline/src/thenwhat/events/trial_facts.py` (arms, `claim_arm`), `pipeline/src/thenwhat/export/build.py`, `site/export.schema.json`, `site/data/seed-export.json`, `site/src/lib/export.ts`.
- `site/src/lib/trial-facts.ts` (`phaseGroups`, `TRIALS_PER_PHASE`, `measureGlosses`, `comparedNames`), `site/src/components/Trial.astro`, `site/src/pages/[slug].astro`, `site/src/styles/global.css`, `DESIGN.md`.
- Modifies "A long list of trials opens with the furthest" in `site-publishing`, and the column list of "Trials read across as a table" in the `page-frame` change, which is not yet archived.
