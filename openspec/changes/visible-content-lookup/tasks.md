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

## Slow article lookup correction
- [x] Reproduce the ScienceAlert delay and isolate paper retrieval using timed production requests
- [x] Establish failing regression checks for stalled sources, non-treatment identification and popup timeout/retry
- [x] Bound upstream retrieval and preserve private fallback when public proof stalls
- [x] Bound popup attempts and prevent late work after timeout or closing
- [x] Run source, controller, service, build and protected regression checks
- [x] Count the linked papers not looked up in the answer, say so beside the list on the site and in the popup, keep such an answer out of the shared and saved results, and end the paper request in flight for a non-treatment identification
- [ ] Release the service and updated Safari extension, then verify the article in installed Safari


## Faster article lookups
- [x] Establish protected checks for negative reuse, staged results, overlapping source work and source-cache privacy
- [x] Implement earlier safe cache reuse and conservative text-article visual handling
- [x] Implement progressive completed clinical results with compatible JSON fallback
- [x] Overlap independent sources and add bounded structured source reuse
- [ ] Run regression suites, builds and independent review; resolve findings
- [ ] Deploy through reviewed CI and install the signed Safari update
- [ ] Retest the same articles, compare fresh/core/completion/repeat timings and record limitations
