# Proposal

## Why

On 2026-11-19 the operator dropped claims. The lab (`thenwhat-lab`) now tracks every coded treatment and condition pair that the registry's trials support (its change `track-pairs`), and it already writes each page of the site as one JSON file with a JSON Schema per page model (`lab pipeline pages`). The site still reads one 42 MB export of 1,126 claims, and about 130 of its 209 source files name claims.

The same day the operator approved a plan to finish (Claude Doc "Finishing the pipeline and the Cloudflare site", decisions recorded in `design.md`):

- The site's only input becomes the lab's page files, published as a versioned bundle.
- The main pages are built ahead; the long tail of pair pages is rendered on request.
- The first version is registry-first: no headlines until the lab builds reports.
- The Postgres migration and the parallel run of `cloudflare-source-of-truth` are superseded.

A run over the active phase 2 and 3 trials (about 26,000) will make tens of thousands of pairs. One export file and one built page per pair do not hold at that size.

## What Changes

- **The site reads a bundle of page files.** One JSON file per page, one JSON Schema per page model, and a manifest with a checksum, counts by page model, the versions of the steps that made it and when. **BREAKING** for `site-publishing`: `site/data/export.json` and `site/export.schema.json` go.
- **The bundle lives in R2 under its version**, and one pointer names the current version. Publishing and rolling back are each one write of the pointer.
- **Types and validators are generated from the bundle's schemas** when the site is built. A page model the site does not know, or a file that does not fit its schema, fails the build.
- **A pair has a page at `/{address}`**, replacing the claim page. It shows the intervention, the condition, the status with the events that produced it, each supporting trial with its arms, facts, events, papers and posted results, and the history of the status.
- **Main pages are built ahead; other pair pages are rendered on request.** The Worker reads the pair's file from the current bundle by its address, renders it with the same template, and the answer is cached for a day. A reader cannot tell the two apart.
- **Every claim address answers.** A claim whose pair is published redirects to it (301). A claim with no coded pair keeps its page until the operator decides it. An archived claim still answers 410.
- **Intervention, condition, topic and clinical category pages list pairs.** The condition page is new.
- **`lookup.json` keeps the keys the extension reads**, generated from pairs, so the extension needs no release at the cutover.
- **Left out of the first version**, because the lab holds no reports yet: headlines, source articles, promises, reported statements, outlet pages, year pages, anniversaries, "it happened". A pair that came from a seeded claim shows that claim's first report where the lab holds it. Their addresses answer 404 until the lab's reports are built, except those a redirect covers.
- **Wording stays the site's.** Files carry codes. A status label with verdict wording still fails the build.
- **Site tests build a small bundle of real page files** cut from the lab's eval slice, so `make check` keeps its time. The full bundle is built only for a preview or a deployment.

Not in this change:

- The lab's bundle command, the full run and the rule that clears held pairs: the lab's work.
- The lookup service's port to TypeScript and its conformance suite.
- Daily upkeep on Cloudflare (Cron and Workflows). The bundle is published from the operator's machine.
- The extension, beyond a check that `lookup.json` still fits it.
- Reports and headlines.

## Capabilities

### New Capabilities

- `site-bundle`: what the bundle holds, where it is kept, how one version becomes current, and how the site refuses a bundle that does not fit.
- `pair-pages`: the pair page and the pages that list pairs, which are built ahead and which on request, and what old addresses answer.

### Modified Capabilities

- `site-publishing`: the site is built from the bundle, not from an export; the claim page is removed.

The claim-keyed requirements of `claims`, `open-data`, `anniversaries`, `source-pages`, `sharing`, `landing-pages`, `health-areas`, `clinical-classification` and `deployment` are revised or removed in this change's task 1.2, each as its own delta, before any page is built. They are not written yet: which survive depends on the pair page models as merged at the lab's step S9.

## Impact

- **Decisions to record (ADRs):** the site's input is the lab's bundle; a pair page may be rendered on request from a public file; `CLAUDE.md`'s line "Its only input is the pipeline's JSON export at `site/data/export.json`" is superseded.
- **Code:** `site/src/pages`, `site/src/lib`, `site/worker` (redirects, on-request pages, an R2 binding), `site/scripts/deploy.mjs`, `site/wrangler.jsonc`. `pipeline/` publishes nothing after the cutover and is frozen.
- **Other changes:** `cloudflare-source-of-truth` loses its migration, parallel-run and store-export tasks (its sections 0, 5 and 6) and keeps D1, the ingest service and records from lookups for the lookup port. `trial-first-route`'s trial page is served by the pair bundle's trial rows; its other sections are the lab's now. `registry-drafted-claims`, `file-based-backfill`, `claim-identity-records` and `same-story-candidates` were closed as superseded by pairs on 2026-11-19, at the operator's word.
- **Cost:** R2 holds well under 1 GB; reads sit inside the Workers Paid plan's allowance at present traffic. To be read from Cloudflare's pages and noted in `docs/sources.md` before the binding is added.
- **Readers:** every claim address changes once. Shared links and search results keep working through redirects.
