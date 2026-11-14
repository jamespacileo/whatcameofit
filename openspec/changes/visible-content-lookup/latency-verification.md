# Article lookup latency verification — 14 November 2026

## Reproduction

ScienceAlert's tinnitus biomarker article reproduced the reported slow lookup in the production API. Single diagnostic runs, using identical article text:

| Input | Elapsed | Result |
| --- | ---: | --- |
| Browser text with the article URL for independent public verification | 32.8 s | No specific treatment identified |
| Browser text with the article's first three DOI links, without public verification | 31.9 s | Same identification |
| Browser text without DOI links or public verification | 2.7 s | Same identification |

Separate local probes read ScienceAlert's robots and article in about 0.1 seconds total. All three Europe PMC calls returned HTTP 500. This is evidence of an optional paper dependency holding up an otherwise completed identification; it is not a measured post-deployment speed guarantee.

At diagnosis the installed Safari app was version 0.9.1, build 10. Its controller had no lookup deadline. The subsequent deployment and installation are recorded below.

## Regression coverage

A protected harness failed all five scenarios before the change and passed after integration: non-treatment identification with stalled papers/records; publisher stalls at robots, headers and bodies; paper and registry header/body deadlines; popup timeout followed by retry with late completions ignored; browser page reading completing after timeout without sending a request.

Committed tests also cover treatment requests overlapping normally, optional public proof falling back without shared storage, fast public proof excluding private additions, shared-cache and index timeouts, screenshot fallback under the same deadline, and popup closure. Two additional integration tests ensure an expired response cannot overwrite a successful retry or its stored result and a late page read cannot submit content.

- Site suite: 450 passed.
- Extension suite: 129 passed.
- Protected acceptance: 5 passed.
- Extension bundle built successfully.
- Site build passed, including footer notices on 63 pages and seven retired-topic redirects.
- Cloudflare Worker packaging dry run passed; nothing was deployed.
- OpenSpec strict validation and whitespace checks passed.

The corrected negative-identification path returns immediately in deterministic tests, but the 2.7-second production text-only reading is a diagnostic comparison, not a released extension benchmark.

## Deployment and installed-Safari verification

- [PR #94](https://github.com/jamespacileo/whatcameofit/pull/94) merged at `6386b159f3c48a98ad14b03756b7a930c2ad53db`, including the extension version bump to 0.9.2.
- [PR checks](https://github.com/jamespacileo/whatcameofit/actions/runs/43642743796) passed the complete `make check` suite and public deployment rehearsal.
- [Production run](https://github.com/jamespacileo/whatcameofit/actions/runs/43642992718) passed tests, verified Cloudflare authentication, deployed the latest main revision and passed the live-site smoke checks.
- Built Safari 0.9.2 (11), Intel and Apple silicon, with stable Xcode 27.2 (27B52). Signed with the existing Apple Development identity and exactly the installed app and extension entitlements; verified both signatures and every bundled extension resource against the tested build.
- Installed at `/Users/jay/Applications/WhatCameOfIt.app`. The registered Safari extension and both bundle versions report 0.9.2 (11). Previous application preserved in a rollback copy. Restarted Safari and restored its previous windows and tabs; existing extension permission and automatic-search consent persisted.
- Opened the existing ScienceAlert tinnitus article in the installed Safari extension. The popup advanced from screenshot reading to its automatic, unreviewed result instead of remaining on the loading message.
- Explicitly pressed **Search again** to bypass saved results. The fresh attempt was still reading the automatic screenshot at the 5.6-second observation and had displayed the completed answer by the 9.4-second observation. These are UI observation bounds, not instrumentation of exact completion time.
- Final text: “A specific treatment and condition could not be identified from the content that could be read. The registry was not searched; nothing has been ruled out.” This is the expected treatment-identification outcome for this biomarker report. The completed popup was left open on the article.

The update was installed locally; no App Store submission was performed.

## Delegation and integration cost

Implementation used the existing Claude subscription with explicit `claude-opus-5-5`, high effort, in an isolated offline source snapshot. The successful worker run took 315.4 seconds (317.8 seconds including evaluation), with a 5,500-character handoff and 1,212-character summary. Reported usage was 54 input, 79,131 cache-creation input, 1,360,701 cache-read input and 33,531 output tokens. All three evaluator checks passed and isolation was verified.

Preparation incurred two runtime/path preflight corrections and a 53.2-second unsuccessful worker run due to omitted recorded research fixtures; that run changed no files and used 3,375 output tokens. The missing fixtures were supplied without relaxing checks. Codex inspected and integrated eleven candidate files, added two persistent regression tests, updated specifications and ran full site/extension validation. No implementation rewrite was needed. These overheads are recorded; no net quota saving is claimed.
