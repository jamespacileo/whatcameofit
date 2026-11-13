## Implementation
- [x] Scope YouTube text and links to the current video; preserve selection precedence.
- [x] Restrict capture to the current visible video and reject stale context or ads.
- [x] Canonicalise video links and keep browser content out of shared cache writes.
- [x] Document loaded-caption limits and retain existing permissions and budget controls.

## Verification
- [ ] Pass extension and site regression suites and production builds.
- [ ] Complete independent standards and specification reviews.
- [ ] Verify regular video, loaded transcript, Shorts navigation and frame fallback in Safari/Chrome before publishing this extension update. Live inspection currently times out; do not claim runtime verification from fixtures.
