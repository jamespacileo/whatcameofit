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
- [ ] Release the service and updated Safari extension, then verify the article in installed Safari
