# Proposal

## Why

The open data was one file holding every published claim's full record. At 966 claims it was 27.5 MiB indented, and the host refuses any file over 25 MiB, so a deploy failed. As a stopgap the file was written without indentation (18 MiB); it would pass the limit again near 1,300 claims. On 2026-11-17 the operator chose an index with one short entry per claim, and each claim's full record in its own file.

## What Changes

- `/data/claims.json` becomes the index: the licence, credit line, sources and method address as before, and for each claim its slug, headline, intervention, indication, status code, first reported date, the day the registries were last checked, and the address of its full record.
- Each claim's full record, unchanged, is at `/data/claims/<slug>.json`, with the licence, credit line and sources repeated so the file stands alone.
- The data page and the researchers' page say the data is an index plus one file per claim, and how to fetch everything: the index, then each record.
- Every build fails when any built file is over 20 MiB, naming the file, so the host's limit cannot surprise a deploy again.

## Capabilities

### Modified Capabilities

- `open-data`: the download is an index and one file per claim; no built file may come near the host's limit.

## Impact

- `site/src/lib/open-data.ts`, `site/src/lib/site-open-data.ts`, `site/src/pages/data/claims.json.ts`, `site/src/pages/data/claims/[slug].json.ts`, `site/src/pages/data.astro`, `site/src/pages/for/researchers.astro`, `site/src/pages/for/journalists.astro`, `site/src/lib/structured.ts`.
- `site/scripts/check-dist.mjs`, `site/scripts/dist-size.mjs`: the size check, run by every build and so by `make deploy`.
- A reader who read every record from `claims.json` now reads the index, then each record file.
