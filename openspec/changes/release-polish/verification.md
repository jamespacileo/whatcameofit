# Release polish verification — 13 November 2026

## Automated checks

GitHub run 43509786063 at 8478458 passed: 618 pipeline tests, 239 site tests, 116 extension tests, the normal site build, and the production rehearsal with 84 claims / 306 pages. The UI detector reported no findings for the changed home page and extension renderer. Source diff whitespace checks passed.

The new website regressions exercise the actual home-page script: submit an untracked URL, click its registry-search button, and return a synthetic API answer. They verify per-record confidence and collapsed limitations, plus stale URL lookup success/failure after a newer or empty submission. Saved-check regressions exercise the real answer formatter, local persistence shape and renderer.

A loaded Mac caused one existing five-second popup test to time out during concurrent builds. After stopping redundant local builds, it passed independently and all 116 extension tests passed together. The complete suites also passed in GitHub's clean runner. No timeout was raised or assertion weakened.

## Browser checks

- Live site search and claim pages at 375 and 320 pixels: no horizontal overflow; evidence disclosure and Escape dismissal worked.
- Updated home page with synthetic candidates: valid 94% confidence and unavailable confidence belonged to separate records; long titles fit at desktop and 320 pixels, with both disclosures independently expanded.
- The extension's 32 pre-existing preview states fit their 360-pixel popup width. The added saved-check preview showed the registry-not-searched limitation.
- Installed Safari 0.9.0 was checked before changes, including reopening the Kyoto article popup.
- Safari 0.9.1 built with stable Xcode 27.2 (27B52) for arm64 and x86_64. Its bundled runtime files matched the tested extension resources.
- Updated the same local application in place, preserving the previous local signing entitlements. Code-sign verification passed; macOS registered one extension. Safari Settings showed one enabled What came of it? 0.9.1 entry.
- Opened the installed 0.9.1 popup on Kyoto University's 31 March 2021 article: the tracked claim and Phase 1 result rendered. Opened Recently checked and verified the new neutral wording on older entries, without losing the saved list.

## Limits and release state

Native window capture remained unreliable under Stage Manager, and the computer-use connection later dropped during an additional Nottingham article check. That extra check is not claimed as complete. Stage Manager was restored after the earlier rendering check and no further desktop preference changes were made.

The submitted Safari 0.9.0 (9) remains Waiting for Review; 0.9.1 is the local patch and GitHub extension package. No permissions, privacy destinations, provider configuration or spending limits changed. Chrome registration remains parked. Web deployment is verified after merge through the normal GitHub pipeline.
