## Implementation
- [x] Compact result hierarchy and labelled icons
- [x] Accessible candidate and source disclosures; preserve consent and uncertainty
- [x] Check wording compatibility, render states and keyboard interactions
- [x] Package and install the updated Safari extension

## Release
- [x] Review changes and pass required checks
- [x] Publish the source update and verify CI

Checked 2026-11-14: built in `564b3c2` with tests in `extension/tests/view.test.mjs` for candidate-first cards, unavailable confidence, disclosures and visible first-use sharing, and shipped in the Safari 0.9.0 release (`a68ffd4`). Updating the Apple build and screenshots moved to `safari-0-9-1-release`, which captures current screenshots and submits the next build.
