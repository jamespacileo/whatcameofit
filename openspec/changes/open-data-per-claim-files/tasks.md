# Tasks

## 1. Site

- [x] 1.1 `openDataIndex` and `openDataRecord` in `lib/open-data.ts`; the index at `/data/claims.json` and one record per claim at `/data/claims/<slug>.json`. Verify: `site/tests/open-data.test.mjs`.
- [x] 1.2 Data page, researchers' and journalists' pages and the Dataset description say what the files are and how to fetch them all. Verify: `site/tests/open-data.test.mjs`, `site/tests/guide-and-landing.test.mjs`, `site/tests/reach.test.mjs`.
- [x] 1.3 A build fails when a built file is over 20 MiB, naming it. Verify: `site/tests/dist-size.test.mjs`.
