# Proposal

## Why

"The record in brief" (change `claim-at-a-glance`) tells a skimming reader how a claim was tested and sends them to "Trials on record" for the rest. What they land on is written for someone who already reads trial registries. Each entry leads with a registry identifier and the registry's own title ("Median Nerve Stimulation for Tourette Syndrome and Chronic Tic Disorder"), then "No phase · Completed · 135 participants enrolled", then "Randomised, quadruple-blind, compared with a sham procedure and no treatment". What the trial measured, and the numbers its sponsor posted, are behind a fold labelled "Planned measures and posted results", as a run of lines with no column to read down.

The readings added by `claim-at-a-glance` can now say what a trial measured in plain words. The operator reviewed a redrawn entry on 2026-11-14 (boards I and J, https://claude.ai/artifact/YPJVB4nTa7UHypiH9E2huE) and asked for it to be specified. It replaces the first mockup of this idea (board B), which a design critique rejected for oversize result figures, tint chips and one trial drawn larger than the others.

## What Changes

- A trial entry leads with a plain heading: how many people, and what the record says it was compared with ("135 people, compared with a sham device and with no treatment"). The registry identifier stays on the entry as the link to the record; the registry's title moves into the fold.
- Where a usable reading exists, one sentence says what the trial measured and for how long ("It measured the change in a symptom score over 4 weeks."), in the wording "The record in brief" already uses.
- The design and state are said in plain words on one line: assigned at random, blinded or open label, finished or under way with its date, results posted with its date, and the phase when the registry gives one. The registry's exact terms stay one press away.
- The fold says what is in it, and its posted results become a table: one row for each group, with the value and how many were analysed, under a line that says what the numbers are. No figure is larger than body text.
- Every trial is drawn the same. The order is unchanged: furthest phase first, then those with posted results.

Out of scope:

- Paper entries. They already show where a paper appeared, what kind of publication it is and which trial's record names it, which is all the index's record allows; abstracts are not stored.
- What a measure's scale runs from and to, and which way is better. A registry gives it only in a free-text description that `trial-facts` does not carry. The entry says so and links to the record's results.
- Any change to the order of trials, to the five-trial fold, to trial facts, to readings or to the export.
- Charts, bars or any drawing of a result.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-publishing`: a trial entry leads with plain words read from its record; says what it measured where a reading allows; shows posted results as a table that says what its numbers are.

## Impact

- `site/src/components/Trial.astro`: the visible lines and the fold.
- `site/src/lib/trial-facts.ts`: plain wording for allocation, masking and state; the heading; the fold's label. `site/src/lib/record-brief.ts`: the measure phrases move to a module both use.
- `site/src/pages/[slug].astro`: passes a trial's completion and results dates, which are already in the claim's events.
- `site/src/styles/global.css`, `DESIGN.md` (Trial entry), `GLOSSARY.md` if a new term is used.
- `site/tests/trial-facts.test.mjs`, `site/tests/site.test.mjs`, `site/tests/trials.test.mjs`: new scenarios; existing assertions on the entry's first lines are updated.
- No pipeline, export, schema or seed change. Depends on `claim-at-a-glance` being merged (readings, measure phrases).
