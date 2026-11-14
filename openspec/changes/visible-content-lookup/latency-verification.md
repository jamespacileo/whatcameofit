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

## Broader article checks and speed opportunities

Additional checks on 14 November 2026 used the deployed service and installed Safari 0.9.2 (11). Three previously untracked articles exercise DOI and PubMed links, treatment identification, candidate matching, and searches with no accepted match. A tracked ScienceAlert article is the fast-path control.

| Article | Research link | Fresh API result | Shared-cache API | Safari saved result observed by |
| --- | --- | ---: | ---: | ---: |
| [ScienceDaily: brain-tumour CAR-T research](https://www.sciencedaily.com/releases/2026/11/261104084009.htm) | DOI `10.1126/scitranslmed.aed9994` | 8.998 s | 142 ms | 1.645 s |
| [ScienceDaily: hearing-loss gene therapy](https://www.sciencedaily.com/releases/2026/04/260403044651.htm) | DOI `10.1038/s41591-025-03773-w` | 9.387 s | 97 ms | 1.130 s |
| [King's College London: lab-grown teeth](https://www.kcl.ac.uk/news/lab-grown-teeth-might-become-an-alternative-to-fillings-following-research-breakthrough) | PubMed `39532305` | 8.172 s | 119 ms | 1.053 s |

The API measurements include the full HTTP response and JSON body. Fresh calls sent transient article text, paper links and the public URL with `refresh: true`, exercising the browser-text route including independent public verification. They exclude browser collection and popup rendering. Warm calls explicitly used `cacheOnly: true`; every response was HTTP 200 with `cache.shared: true`. Fresh requests were paced, without automatic paid retries. This is one fresh API observation per article, not a percentile benchmark.

All three returned successful automatic searches, not timeout/error fallbacks. The hearing-loss report returned eight candidate records, including high-confidence OTOF gene-therapy matches. The CAR-T and tooth-regeneration reports returned candidate records but no accepted matching trial; Safari correctly displayed the qualified no-matching-record message, rather than claiming that no trial exists. Each also displayed related-paper and organisation sections. These checks validate lookup completion and presentation, not independent clinical review of every candidate.

In the installed extension:

- All three articles displayed their saved results, including the earlier-check date. UI timings above are upper bounds from clicking the toolbar button to observing the answer, including automation overhead; they are not exact paint times.
- **Search again** on the hearing-loss article bypassed the saved result. It was searching at the 5.344-second observation and complete by 20.316 seconds. There was an observation gap while independent source probes ran, so 20.316 seconds must not be reported as its actual search duration.
- Closing and reopening that popup displayed the saved hearing-loss result by 1.108 seconds.
- The [tracked ScienceAlert melanoma-vaccine report](https://www.sciencealert.com/world-first-cancer-vaccine-cuts-melanoma-recurrence-or-death-risk-by-42-in-landmark-trial) displayed its existing claim/status by 1.046 seconds without a fresh lookup.
- Test articles were opened in a separate Safari window; existing user windows and tabs were preserved.

Together with the original tinnitus check, the sample showed no indefinite spinner. It does not establish that every publisher or every cold search is fast. The current 45-second popup limit remains an escape from stalls, not an acceptable speed target.

### Independent source probes

Using the same local article reader, including robots checks, publisher reads took 616 ms, 153 ms and 508 ms for the three articles above. Separate Europe PMC probes took 108 ms, 23 ms and 13 ms, all HTTP 200. The hearing-loss paper resolved to `NCT05901480`; the other two supplied no trial number. One primary-name ClinicalTrials.gov search per article took 153 ms, 125 ms and 114 ms respectively.

These are local probes, not production-stage measurements: they exclude the model calls, additional search phrases, scoring and optional research enrichment. Production's fresh responses had empty `paper_numbers`, so the successful local paper resolution must not be taken as proof that the deployed paper step succeeded identically. The original diagnosis saw Europe PMC failures; these later probes demonstrate its variability, not removal of the need for deadlines. There is no production trace here that apportions the remaining 8–10 seconds among stages.

### Prioritised opportunities

These are recommendations, not additional deployed behavior changes. Targets below are proposed acceptance criteria, not measured guarantees.

1. **Make an earlier result immediately useful.** The service already answers shared-cache hits in approximately 0.1 seconds. `extension/src/controller.js` waits for the index, then page reading/media inspection and fingerprinting, before probing the shared cache. Start the safe URL lookup alongside local collection, render an explicitly dated earlier result as soon as it is eligible, and validate current content before treating it as reusable. Preserve selected-text behavior, consent, private-window exclusion, navigation guards and content-change invalidation. Save eligible shared hits into the local result cache once the current fingerprint is known; the current shared-hit branch only renders them. Target: a previously checked page visible within 300 ms locally or 750 ms with a shared result on a normal connection, measured in the browser.

2. **Stop repeating an already successful negative identification.** Both `extension/src/results.js` and `site/worker/results.mjs` deliberately retain only `about_a_treatment: true`. The original tinnitus report therefore cannot benefit from either result cache. Add a bounded, fingerprinted local cache for completed non-treatment outcomes; keep errors, incomplete reads and timeouts separate. A shared version would still require independent public verification and retain only structured outcomes. Also distinguish a readable article with an illustrative photo from content whose claim genuinely lives in its image. The current `visualCandidate` plus a negative text result always causes a second model call. Tighten that distinction with image-only and misleading-caption regression cases, retaining the explicit Screenshot action and genuine automatic image fallback.

3. **Show the core result before optional enrichment finishes.** `lookUp()` waits for `research.search()` before returning, even when the trial result is ready. Deliver a correctly labelled core answer first, then append related papers and organisations. The UI must distinguish searching, complete and unavailable; it must never display “no matching trial” while core searches are outstanding. Start optional enrichment as soon as treatment extraction completes rather than after linked-paper requests. Target: useful first result within 2–3 seconds for common uncached articles; separately measure full completion.

4. **Shorten the serial critical path and cache public metadata.** Positive treatment lookups still wait for all linked-paper requests before beginning name-based registry searches. Up to three papers are read sequentially at five seconds each: a 15-second dependency budget despite the non-treatment early return. Registry numbers, a named trial and search terms are also processed serially, with up to ten seconds per HTTP request and potentially multiple requests per term. Start independent work earlier, enforce one aggregate paper allowance, reuse versioned DOI/PubMed-to-trial and registry responses across articles, and share in-flight requests. Preserve source rate limits, exact-ID provenance, and the distinction between unavailable and no match. Do not stop after the first plausible trial if that would silently omit the report's actual trial.

5. **Increase fast-path coverage and measure before changing models.** The tracked control already avoids the live pipeline. Extend public, verified precomputation and safe exact-paper mappings for commonly encountered reports; ambiguous papers still need treatment/condition disambiguation. A network miss currently costs a separate cache probe plus a full request, both counted against the five-per-minute reader limit. Consolidate that protocol or give cache-only reads a separate inexpensive allowance while keeping model calls protected. Add privacy-safe durations and counts for collection, cache, public proof, extraction, papers, registry, scoring, enrichment and first render; record no text, images, URLs, credentials or reader identifiers. Use those measurements to decide whether reducing model input or scoring work is worthwhile. No model, service tier or spending allowance was changed for these checks.

The next performance change should target dated-result rendering, safe reuse and unnecessary second reads first. Fresh model-assisted searches cannot honestly be promised subsecond under the current all-or-nothing response design. Measure saved-result first paint and cold-search first useful result separately, with p50/p95, cache-hit rate, correct-outcome parity and stalled-source tests across the article corpus.

Only URLs, identifiers, derived timings and structured test findings are recorded here. Temporary article payloads were removed after testing; article text and images were not committed.

## Delegation and integration cost

Implementation used the existing Claude subscription with explicit `claude-opus-5-5`, high effort, in an isolated offline source snapshot. The successful worker run took 315.4 seconds (317.8 seconds including evaluation), with a 5,500-character handoff and 1,212-character summary. Reported usage was 54 input, 79,131 cache-creation input, 1,360,701 cache-read input and 33,531 output tokens. All three evaluator checks passed and isolation was verified.

Preparation incurred two runtime/path preflight corrections and a 53.2-second unsuccessful worker run due to omitted recorded research fixtures; that run changed no files and used 3,375 output tokens. The missing fixtures were supplied without relaxing checks. Codex inspected and integrated eleven candidate files, added two persistent regression tests, updated specifications and ran full site/extension validation. No implementation rewrite was needed. These overheads are recorded; no net quota saving is claimed.
