# Proposal

## Why

A claim page says that a trial exists and when it changed state, and nothing about the trial itself: how many people it enrolled, how it was designed, what it set out to measure, or what its posted results say. The published export of 13 November 2026 holds 34 "results posted" events across 16 claims, and each reads only "Results posted for trial NCT…". The registry record that holds the answers is already stored with every trial event, so the gap is in what is read from it, not in what is collected.

Three smaller faults sit beside it. Each trial appears twice on the page, as dated events in the timetable and as a one-line row under "Matched registry records", and the two never meet. A matched paper is listed under a heading that calls it a trial registry record. A follow-up paper event carries a confidence of 0.6 or 0.9 that the page never shows.

## What Changes

- Each trial behind a published claim's approved events is exported once, as a trial, with the facts its registry record states: number of participants and whether that is the actual or the planned number, allocation, masking, comparators, whether healthy volunteers were studied, age groups, lead sponsor and its kind, planned primary outcomes, the registry's stated reason for stopping, and posted results for primary outcomes.
- The facts are read by fixed rules from the registry record already stored with the trial's events. No model is asked, no new source is called, and nothing is fetched that is not fetched today.
- Posted results are shown as the registry posted them: per group, the number analysed and the value, and each posted comparison with its p value and method. The site adds no word on whether an outcome was met.
- The claim page gains a "Trials on record" section with one entry per trial, furthest phase first, in place of the approved trial rows under "Matched registry records". Timetable events lead to their trial. A fact row states how many trials are on record and the size of the largest.
- Matched papers move under their own heading.
- An evidence event whose confidence is below 1 shows that confidence.
- The open data file carries the trial facts.

Not in this change: any change to how status is derived, or to how a claim becomes "failed"; adverse event counts; papers a registry record cites (they belong to `related-research`); facts for candidate matches not yet approved; trial locations, contacts or eligibility criteria, which are never exported; reasons on a match, whose column no step fills until `related-research` task 4.2.

## Capabilities

### New Capabilities

- `trial-facts`: what a registered trial says of itself (size, design, who ran it, planned outcomes, posted results), read by rule from its registry record and published with a claim.

### Modified Capabilities

- `site-publishing`: the claim page shows each trial once with its facts, lists papers apart from trial records, and shows the confidence of an event scored below 1.
- `open-data`: the data file holds the trial facts the claim pages show.

## Impact

- Pipeline: a new pure module beside `events/trial.py` that reads facts from a registry record; `export/build.py` gains a `trials` list on each claim and `confidence` on each event. No migration, no new setting, no new request.
- Site: `site/src/pages/[slug].astro`, `site/src/lib/export.ts`, a new wording module for the fact codes, `site/src/lib/open-data.ts`, `site/src/pages/how-it-works.astro`, `site/export.schema.json`, `site/data/seed-export.json`.
- Tests: one new recorded registry fixture of a trial with posted results, with a generic client name.
- Docs: `GLOSSARY.md` gains "Trial facts"; `docs/sources.md` notes which registry fields are republished and how the registry's terms on dating and stating modifications are met.
- Extension and lookup service: unchanged. The extension reads `lookup.json`, whose shape does not change.
- Cost: none. No model call and no additional registry request.
