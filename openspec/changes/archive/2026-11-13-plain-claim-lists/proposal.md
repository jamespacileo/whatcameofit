# Proposal

## Why

A reader without a medical background cannot scan a claim list or read a status. Each row is a headline of about twenty words, statuses are named in trial vocabulary ("Preclinical only", "Phase 3 trial"), and a topic page opens with a count and no account of where its claims stand. The plain meaning of a status is reachable only through a popover or the method page.

Evidence sites such as examine.com handle the same two audiences on one page: a short name per row, one plain sentence at the top, and the precise detail one step further in. Three of those patterns fit this site without a verdict, a grade or a model.

## What Changes

- A row in every claim list leads with the claim's intervention name. The full headline stays in the row beneath it, in lighter weight.
- Every status has a fixed plain-language gloss: one short phrase that says what the status means without trial vocabulary. The gloss is shown under the status label in claim lists and on the claim page. The existing precise meaning stays where it is.
- A topic page opens with one sentence built by rule from the counts of its claims' statuses, for example "Of 7 reported breakthroughs tracked, 5 have no trial in people on record and 2 are in a large late-stage trial in people."
- The neutral-wording build check covers the glosses and every clause the summary sentence can use.

Out of scope: letter grades, effect ratings, a separate expert edition, text filtering and row expansion in lists, and any change to the export, the pipeline, `lookup.json` or the extension.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-publishing`: claim lists lead with the intervention name; every status shown carries a plain-language gloss; a topic index opens with a summary sentence derived from status counts; neutral wording extends to glosses and the summary.

## Impact

- `site/src/lib/status.ts`: gloss and summary-clause wording per status code, both under the neutral-wording check; a pure function that builds the summary sentence from counts.
- `site/src/components/ClaimTable.astro`, `site/src/components/StatusCell.astro`: row layout and gloss. The table is used by the topic, year, source, approved-claims and claim pages, so all five change.
- `site/src/pages/topic/[vertical].astro`: summary sentence in place of the count-only lede.
- `site/src/pages/[slug].astro`: gloss beside the status label.
- `site/src/styles/global.css`, `DESIGN.md`: row and gloss styling, recorded in the visual system.
- `site/tests/site.test.mjs`: one test per new scenario.
- No export shape change: `intervention.name` is already exported. No schema or seed regeneration.
