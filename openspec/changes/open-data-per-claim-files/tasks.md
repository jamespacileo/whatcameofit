# Tasks

## 1. Site

- [x] 1.1 `openDataIndex` and `openDataRecord` in `lib/open-data.ts`; the index at `/data/claims.json` and one record per claim at `/data/claims/<slug>.json`. Verify: `site/tests/open-data.test.mjs`.
- [x] 1.2 Data page, researchers' and journalists' pages and the Dataset description say what the files are and how to fetch them all. Verify: `site/tests/open-data.test.mjs`, `site/tests/guide-and-landing.test.mjs`, `site/tests/reach.test.mjs`.
- [x] 1.3 A build fails when a built file is over 20 MiB, naming it. Verify: `site/tests/dist-size.test.mjs`.
- [x] 1.4 Review follow-up: a build fails over 18,000 files (`DIST_FILE_LIMIT` for a larger plan) and prints its count; `record` addresses from the site's root; `format` and `format_version` in each file, `entries` in the index. Verify: `site/tests/dist-size.test.mjs`, `site/tests/open-data.test.mjs`.

## 2. Later

- [ ] 2.1 The build held 14,223 files at 966 claims (about 14.7 a claim); 18,000 is reached near 1,230 claims and the free plan's 20,000 near 1,360. Fewer files a claim, or a plan that allows more, before then.
