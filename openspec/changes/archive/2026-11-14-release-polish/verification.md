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

A later Safari check on the Nottingham article reused the previous result and displayed five OpenAlex papers and two ROR identities. Tab/Space opened and closed the papers and organisation disclosures correctly, including source caveats and links. A clear screenshot was saved after temporarily disabling Stage Manager; Stage Manager was restored to on.

The computer-use connection intermittently stalled, and mouse automation inside native popup disclosures was unreliable. Keyboard operation succeeded; this was not treated as an application defect. A read-only crawl of the live site checked 117 pages and 2,386 internal links/anchors, with no broken targets, duplicate IDs, missing page titles or missing image alt attributes found.

The submitted Safari 0.9.0 (9) remains Waiting for Review; 0.9.1 is the local patch and GitHub extension package. No permissions, privacy destinations, provider configuration or spending limits changed. Chrome registration remains parked.

## Merged release and live verification

[PR #51](https://github.com/jamespacileo/whatcameofit/pull/51) merged as `7b3e89a5724f5ea4931135c9ed01b8ee17572e65`. The final PR run 43512056325 passed. [Main run 43512392326](https://github.com/jamespacileo/whatcameofit/actions/runs/43512392326) passed all 973 tests, both builds, Cloudflare deployment and the live-site smoke checks; deployment completed at 21:40 UTC on 13 November 2026.

Post-deployment browser checks covered the claim page, home search, Topics and It happened at 320 pixels, plus the approval page at 768 pixels. No horizontal overflow was found. Searching for baxdrostat returned the tracked claim. The six-month reminder downloaded an all-day calendar event for 13 May 2027, with the correct claim URL and exclusive end date of 14 May. It was inspected without importing it into a calendar.

The in-app browser logged two native cross-document transition aborts during navigation; normal page content and keyboard navigation worked. An automated pointer click needed a keyboard retry. This is recorded as a browser-control limitation, not evidence that every browser interaction is flawless.

[Preview 0.9.1](https://github.com/jamespacileo/whatcameofit/releases/tag/v0.9.1-preview.1) contains the Chrome ZIP for local testing, Safari extension resources, generated Safari Xcode project and SHA-256 checksums. All four assets were confirmed uploaded. The ZIPs contain version 0.9.1, no development preview states and no credentials. The Safari project still requires the recipient's own signing; it is not an App Store installation package.
