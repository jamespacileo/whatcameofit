# Verification — 14 November 2026

Local implementation only, compared with main at da6afb8. No deployment, push or merge.

## Automated checks

- Published-snapshot build: passed, 307 pages checked for footer notices; Pagefind indexed the existing 84 claim pages. The private reader template is excluded.
- Full site suite: 249 tests passed. The final focused reader/Worker run passed all 61 tests.
- Protected pre-implementation contract: 13 checks passed, including no forwarded cookies/credentials, fixed upstream URL, timeout, identity validation, HTML escaping, cache expiry, stale provenance, unavailable states, methods and optional KV.
- Compiled-page inspection: nine official trial links retained and nine adjacent alternatives, with five placements for NCT04605549 and two each for NCT07007793 and NCT07800858. All are in the export-derived allowlist.
- All three live local routes returned 200 with correct record identifiers, readable HTML, canonical URLs and noindex metadata. Direct template paths and their HTML aliases returned 404.
- `openspec validate trial-record-fallback --strict` and `git diff --check`: passed.

## Safari check

Tested the real local Worker and assets in Safari Technology Preview, not a simulated user-agent. Removed the registry's visible cookies; `document.cookie` was empty. Its internal NCT04605549 request with `credentials: omit` still returned 403. Followed the local fallback link from the claim page and loaded all three local trial records. All returned 200 with cookies omitted. The first page-navigation request had no Cookie or Authorization header, and the local origin had no cookies. Safari's network log showed zero browser requests to ClinicalTrials.gov during fallback use. The registry cookies remained absent throughout the test and were restored afterwards.

Inspected desktop and phone-width Safari full-page captures (actual viewports 1277×915 and 395×847). No horizontal overflow; all nine alternative links and the full-title disclosure provide 44px phone targets. The original source links remain available. The HTML contains the details before any JavaScript executes.

A separate, loopback-only test harness exercised an unavailable registry response (503, retry/source/claim links) and a two-day-old cached response (200, explicit older-copy notice, unchanged retrieval date). These were visually checked in Safari. The harness does not alter the preview's cache or add production test routes.

## Review and corrections

Separate standards and requirements reviews found four issues, all corrected: single-pass template replacement to protect marker-like registry text, 503 for shared capacity exhaustion, the phone-sized disclosure target, and use of the configured site name. The claim-navigation element was also closed explicitly. Regression checks cover marker-like text and the unavailable status.

The preferred Claude worker could not verify the existing subscription and did not run; no API fallback was used. Codex completed and verified the implementation. No worker-token savings are claimed.

## Local preview

`http://127.0.0.1:8789/primary-aldosteronism-baxdrostat` with direct readers at `/trials/NCT04605549`, `/trials/NCT07007793`, and `/trials/NCT07800858`. See docs/trial-records.md to restart it. The preview binds only to loopback; no public tunnel or publication was created.

## Revision, 14 November 2026

Before release, the older-copy state checked above was removed under the operator's rule against lower-quality fallbacks. A record is reused for 24 hours. After that it is read again, and when the registry cannot be read the page shows the unavailable state. `site/tests/trials.test.mjs` covers both cases. The branch was also brought level with `main`, and the "View trial details here" link now sits in the `Trial` and `MatchList` components that replaced the old matched-records list.
