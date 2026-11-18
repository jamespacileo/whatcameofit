# Proposal

## Why

A home page report row fills a phone screen, mostly with sentences that say when records are dated relative to the report ("The first trial was registered in 2012, 14 years before this report", "No record is dated in the 9 years since the first report"). A design critique on 2026-11-15 (`.impeccable/critique/2026-11-15T12-10-45Z__site-src-pages.md`) found that dates, order and elapsed time are read faster as positions on a line than as sentences, and the operator asked for the site to say more by shape and position and less by copy. 37 of the 84 published claims have records dated before their report and 24 carry a no-signal note; a list cannot show either without a sentence per row today.

## What Changes

- A new graphic, the **record strip**: one horizontal time axis per claim, on the same year scale for every claim on the site, ending at the day the registries were last checked. It marks each news report, each dated registry record, each posting of results, each regulator's decision and each promised date the export holds, by shape and position.
- The strip is drawn on home page report rows and in every claim list table (topic, year, approved claims, source, and wherever else the table is used).
- On a home page report row the two sentences are no longer shown. In sight the row carries the strip and one line of counts in numerals. The sentences, built by the same fixed rules, become the strip's text alternative.
- One key per page names the strip's marks. The guide gains an entry for the strip.
- The strip never fills, fades or breaks its axis, never marks a promised date as passed, and never uses colour or size to tell one record from another.
- `DESIGN.md` records the strip and the operator's decision of 2026-11-15 on words beside marks: a status label stays in sight wherever a status is shown; captions that repeat on every row move to a key and to text alternatives.

Out of scope: the claim page timetable as trial lanes, the status when first reported drawn on the stage track, moving the status gloss out of list rows, the link-preview cards, the embed, the extension popup, the claim page digest, and any change to the export. Each is a later change.

## Revised 2026-11-15

After a critique of the built strip, the operator moved it off the home page: a report row shows the counts in words, and the claim page draws the claim's records on an axis of its own. Lists keep the shared axis with three marks. See design decisions 11 to 14.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-publishing`: a record strip is drawn on report rows and claim list tables; a report row shows counts in numerals with the strip in place of its sentences, which become the strip's text alternative; the wording rule for row sentences extends to the strip, its counts and its key.

## Impact

- `site/src/components/`: a new strip component; `DayReport.astro` and `ClaimTable.astro` draw it; the home page kind key and the table heading gain the strip's key.
- `site/src/lib/`: a new pure module that turns one exported claim into the strip's marks and counts; `row-sentences.ts` keeps its rules and feeds the text alternative.
- `site/src/guide/`: one new entry on the site's own words shelf.
- `site/src/styles/global.css`, `DESIGN.md`, `GLOSSARY.md`: the strip, its marks and the words-beside-marks decision.
- `site/tests/`: tests for the new module, the report row and the tables.
- No change to the pipeline, the export's shape, `site/export.schema.json` or the seed.
