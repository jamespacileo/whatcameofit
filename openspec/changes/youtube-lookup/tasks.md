## Implementation
- [x] Scope YouTube text and links to the current video; preserve selection precedence.
- [x] Restrict capture to the current visible video and reject stale context or ads.
- [x] Canonicalise video links and keep browser content out of shared cache writes.
- [x] Document loaded-caption limits and retain existing permissions and budget controls.

## Verification
- [x] Pass extension and site regression suites and production builds (195 site tests; extension suite plus focused capture/popup regressions; site and extension builds).
- [x] Complete independent standards and specification reviews; fix the two specification findings (loose video identity and player overlays), then recheck with no remaining findings.
- [x] Inspect real YouTube watch and Shorts layouts in Chrome, including navigation between Shorts; adapt selectors to the observed player-title permalink.
- [ ] Verify the installed extension on a regular video, loaded transcript, Shorts navigation and frame fallback in Safari/Chrome before publishing this extension update. DOM inspection and fixtures do not establish end-to-end runtime acceptance.
