# Proposal

## Why

The operator asked on 2026-11-11 for the site to cover popular, miraculous-sounding cure stories from the last three months across many conditions, clickbait titles included, and for the home page to show recent news articles. Until now the only topic was dental regeneration, the candidates were years old, and the home page listed claims, not the headlines readers remember.

## What Changes

- The home page gains a list of the most recently published news reports about published claims, each headline quoted as the outlet wrote it, beside the status the evidence supports.
- A topic appears in menus and lists only once it has a published claim, so new topics can be configured before their claims are reviewed.
- Thirteen topics are added to the configured set: ageing, allergies, brain and nerves, cancer, dementia, diabetes and metabolism, hair loss, heart and circulation, infections, mental health, pain, sight and hearing, transplants.
- A second candidate list, `data/seed/claims-recent.csv`, holds claims reported between 2026-08-11 and 2026-11-11, gathered from mainstream, popular-science and mass-market outlets. Every row is a pending draft.
- The candidates are imported, run through extract, resolve and fetch, and reviewed by the operator, the same way as the dental backfill.

Popularity is not stored or shown. "Popular" describes how the candidates were chosen: from widely read outlets and stories carried by several of them. Showing a measure of popularity would need a stored signal and is left for a later change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-publishing`: the home page lists recent reports; topics without published claims are not listed.

## Impact

- **Site:** `site/src/pages/index.astro`, `site/src/lib/reports.ts`, topic lists in the layout, home and not-found pages. No change to the export's shape.
- **Pipeline:** `claims/verticals.py` only. No schema change and no migration.
- **Data:** a new candidate file and its notes. Nothing is published until reviewed.
- **Wording risk:** outlet headlines often say more than the evidence. They are shown as quotations with the outlet named, never as the site's own statement, and always beside the derived status.
- **Needs before the run:** the same `.env` settings as `backfill-dental-regeneration`, and the operator's review time.
- **Recent claims and the no-signal note:** a claim reported weeks ago cannot have been quiet for three years, so these pages will mostly show an early status and a promise still open. That is the intended starting point for tracking them.
