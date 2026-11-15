## Implementation
- [x] Reproduce image-only failure with a protected service test
- [x] Accept bounded image input and wire provider visual reading
- [x] Add automatic capture, race checks and local reuse
- [x] Add shared cache with independent public-source boundary
- [x] Update privacy and result wording
- [ ] Complete regression, browser and live provider verification
- [ ] Configure shared Cloudflare storage and deploy through reviewed CI
- [ ] Install and test updated Safari app; refresh store privacy/listing/build
- [ ] Submit Safari release after final checks and screenshot

## 2026-11-15 corpus rerun
- [x] Reproduce the five failed rows and attempt every previously untested social URL on the deployed address path
- [x] Add regression cases for social-post identity, surrounding-content exclusion and old cache rejection
- [x] Bind social caption and screenshot scopes; correct non-treatment and multiple-claim identification
- [x] Run the corrected reader and current local service against captured/live public pages with real provider and registry requests
- [x] Preserve per-row build, method, timestamp, limitations and verdicts in the corpus and existing Google Sheet
- [x] Complete final regression, build, corpus and Sheet read-back verification

## Slow article lookup correction
- [x] Reproduce the ScienceAlert delay and isolate paper retrieval using timed production requests
- [x] Establish failing regression checks for stalled sources, non-treatment identification and popup timeout/retry
- [x] Bound upstream retrieval and preserve private fallback when public proof stalls
- [x] Bound popup attempts and prevent late work after timeout or closing
- [x] Run source, controller, service, build and protected regression checks
- [x] Count the linked papers not looked up in the answer, say so beside the list on the site and in the popup, keep such an answer out of the shared and saved results, and end the paper request in flight for a non-treatment identification
- [x] Release the service and updated Safari extension, then verify the article in installed Safari

## Corpus release and installed Safari verification
- [x] Review the corpus fixes against current main and pass the release checks
- [x] Deploy the corrected service through the existing GitHub CI workflow
- [x] Build, sign and install Safari 0.9.4 with unchanged permissions and a rollback copy
- [x] Reproduce the released S026 company-history false positive; strengthen whole-post classification and verify three real-provider negatives plus two positive controls
- [x] Reproduce the released S045 trial-arm false negative; distinguish comparators from roundups and verify the real S045/S021/S026 boundary
- [ ] Release the company-history follow-up with version-4 answer caches and Safari 0.9.5
- [ ] Rerun all 37 affected URLs against production and the released browser reader; verify installed Safari popup behavior
- [ ] Replace local-only corpus and Google Sheet evidence with dated released-version results and verify read-back


## Faster article lookups
- [x] Establish protected checks for negative reuse, staged results, overlapping source work and source-cache privacy
- [x] Implement earlier safe cache reuse and conservative text-article visual handling
- [x] Implement progressive completed clinical results with compatible JSON fallback
- [x] Overlap independent sources and add bounded structured source reuse
- [x] Run regression suites, builds and independent review; resolve findings
- [x] Deploy through reviewed CI and install the signed Safari update
- [x] Retest the same articles, compare fresh/core/completion/repeat timings and record limitations
