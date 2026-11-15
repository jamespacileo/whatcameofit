# Proposal

## Why

The home page lists news reports, status changes, promises and quiet claims, but nowhere lists the claims themselves. "84 claims tracked in 18 topics" leads to the topics, so a reader who wants to skim what the site tracks has to open topic after topic. And every list of claims the site does have (topic, year, source and approval pages) tells a skimming reader the status and nothing about how much testing stands behind it: a claim with one registered trial and a claim with thirteen read the same until the page is opened.

"The record in brief" (change `claim-at-a-glance`) already works out, by rule, whether a claim has been tested in people, in how many trials, how large the largest was and whether results are posted. That answer fits on a row.

The operator reviewed a redrawn home page on 2026-11-14 (boards K and L, https://claude.ai/artifact/YPJVB4nTa7UHypiH9E2huE) and asked for it to be specified. It replaces the first mockup of this idea (board D), which a design critique rejected for swapping the site's index table for generic cards, dropping the promise column, and adding five filter chips beside the tabs.

## What Changes

- The home page gains a list, **Claims**, second after Headlines: every published claim once, newest first report first, read a page at a time like the other lists, and narrowed by the same status and topic controls.
- Every list of claims gains a column, **Tested in people**: how many trials are on record, with the largest stated size and whether results are posted on a grey line beneath; or "None on record", with what the first report was about. It is the first answer of "The record in brief", read by the same rule.
- Above a list that carries the column, one grey line says the column counts trials on record and does not say what they found.

Out of scope:

- Cards, chips, or any filter beyond the status and topic controls the home page already has.
- A model-read fact on a row. The column is read by rule alone.
- Sorting a list by how much a claim has been tested. Lists keep their dated orders; the site does not rank claims.
- The Headlines, Status changes, Promises and No signal lists, whose rows are reports, changes and promises, not claims.
- `lookup.json`, cards, the embed and the extension.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `site-publishing`: the home page offers a fifth list, of the claims themselves; a list of claims says of each how much it has been tested in people.

## Impact

- `site/src/lib/record-brief.ts`: the rule behind the brief's first answer is exposed for a row (`testedSummary(claim)`), so the column and the brief cannot disagree.
- `site/src/components/TestedCell.astro` (new), used by `site/src/components/ClaimTable.astro` and by the new panel in `site/src/pages/index.astro`.
- `site/src/pages/index.astro`: the Claims view, its tab, its panel and its pager; rows carry the status and topic the existing controls narrow by.
- `site/src/styles/global.css`, `DESIGN.md` (Index tables, Home tabs), `site/tests/site.test.mjs`, `site/tests/record-brief.test.mjs`.
- No pipeline, export, schema or seed change. Does not depend on `plain-trial-entries`.
