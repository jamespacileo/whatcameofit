# Lookup speed release verification — 14–15 November 2026

## Comparison method

The same four transient article inputs are used before and after release. Each input has a SHA-256 digest; neither article text nor screenshots are included in this record. Fresh-result cache is bypassed with `refresh: true`. Before release, the ordinary JSON response is timed through body consumption. After release, streaming measures both the completed clinical core and full optional-enrichment completion. Public source caches may be warm in either run; this is a user-visible fresh-result comparison, not a claim that every upstream source is cold. Three runs per article are paced without automatic paid retries.

The current production baseline includes the newer unchecked-paper warning added after the earlier single-run report. Native Safari times are observed upper bounds and include automation overhead; API timings exclude page collection and rendering.

## Baseline before this release

| Article | Median complete result | Three runs |
| --- | ---: | --- |
| ScienceDaily brain-tumour CAR-T | 6.596 s | 6.596, 7.027, 6.039 s |
| ScienceDaily hearing-loss gene therapy | 10.226 s | 10.226, 8.085, 11.446 s |
| King’s College London lab-grown teeth | 8.075 s | 8.075, 8.644, 7.188 s |
| ScienceAlert tinnitus biomarker | 3.520 s | 3.742, 3.520, 3.122 s |

All 12 baseline calls returned HTTP 200. Four treatment lookups reported an unchecked paper across the three rounds; those incomplete answers must remain visibly qualified and ineligible for result caching. Model extraction and candidate ordering varied between runs, which is why the comparison retains repeated timings and uses deterministic regression checks for matching parity.

## Release verification

Implementation accepted with eight protected checks; full site suite (508 tests), extension suite (155 tests), deployment rehearsal, strict OpenSpec validation and unsigned Safari build passed before independent review. Review found two edge cases: interrupted streaming after navigation and variable cache latency bunching paper origin starts. Both were reproduced and fixed, and stage timing semantics were corrected. The affected 62-test suite passes, including four navigation-tail regressions, two source pacing/cancellation regressions and a deterministic stage-duration check. Both reviewers rechecked the fixes without further findings. The final merged revision passed CI: 1,180 pipeline tests, 571 site tests and 159 extension tests, production build rehearsal, deployment and live smoke checks.

The isolated subscription worker used Opus 5.5 for 1,194 s (1,199 s including verification), 62 turns, a 7,758-character handoff and a 1,136-character return summary. Reported usage: 112 input, 248,017 cache-creation, 8,310,791 cache-read and 123,427 output tokens. An initial local Python preflight failed before invoking the worker and was corrected using the installed Homebrew interpreter. Codex handled protected acceptance, full-suite verification, independent review and the three targeted review corrections. These measurements describe handoff/rework cost and do not establish subscription quota savings.


## Released milestones

- [Service PR #109](https://github.com/jamespacileo/whatcameofit/pull/109), merged as `27ebb7413e1ce0e7eeb3d2fcc5f9770ce79dc640`.
- [Safari PR #110](https://github.com/jamespacileo/whatcameofit/pull/110), merged as `15e7d19b1eed95e3e56e54af9cbc336979c40561`.
- [Production CI](https://github.com/jamespacileo/whatcameofit/actions/runs/43655046794) deployed the combined revision at 23:52 UTC on 14 November. Worker version `96c020bf-492e-4609-834f-d68039f2316d`. The earlier service-only deploy correctly skipped its superseded revision.
- Installed `/Users/jay/Applications/WhatCameOfIt.app`, version **0.9.3 (12)**, preserving the existing Apple Development identity and entitlements. Both signatures verified; the universal Intel/Apple-silicon build's extension resources exactly matched the tested production bundle. Plugin registration points to this installed version. The previous 0.9.2 installation is retained as a rollback copy. Safari windows were restored; tests used a separate window. No App Store submission or permission expansion.

## After-release comparison

Each cell reports the median of the same three inputs/runs. “First result” means the completed clinical answer, after every clinical search and score. “Complete” additionally includes optional research and full response-body consumption.

| Article | Before complete | After first result | After complete | First-result change |
| --- | ---: | ---: | ---: | ---: |
| ScienceDaily brain-tumour CAR-T | 6.596 s | 6.333 s | 6.367 s | 4.0% faster |
| ScienceDaily hearing-loss gene therapy | 10.226 s | 7.785 s | 7.810 s | 23.9% faster |
| King’s College London lab-grown teeth | 8.075 s | 6.195 s | 6.265 s | 23.3% faster |
| ScienceAlert tinnitus biomarker | 3.520 s | 3.504 s | 3.549 s | Essentially unchanged |

After first-result runs: CAR-T 7.554/5.587/6.333 s; hearing 9.005/7.412/7.785 s; teeth 7.129/6.195/5.118 s; tinnitus 3.504/2.628/3.509 s. All 12 returned HTTP 200 and both expected stream events. SHA-256 input digests matched across all six before/after rounds. One KCL run reported an unchecked linked paper; later runs completed that source. Incomplete answers remain qualified and excluded from saved-result reuse.

Optional enrichment finished before the clinical answer on these live runs, so this sample demonstrates concurrency and reuse, not a large streaming-tail saving. Slow-enrichment and failed-tail behavior is covered by deterministic tests. Source caches became warm across rounds: paper mappings subsequently took 17–86 ms, while initial paper stages took 2.651–5.000 s. These are not fully cold-source benchmarks, and model extraction/candidate counts varied. The three-run comparison is descriptive, not statistical proof of a fixed percentage gain.

## Installed Safari checks

| Article / action | Observed completed display within | Outcome |
| --- | ---: | --- |
| Tracked ScienceAlert melanoma control | 1.087 s | Existing tracked claim appeared |
| CAR-T, repeat opening | 1.091 s | Dated previous result, related papers/organisation available |
| Hearing loss, shared result | 1.198 s | OTOF gene therapy, eight possible matches and research |
| Hearing loss, repeat opening | 1.107 s | Same dated saved answer |
| Lab-grown teeth, shared result | 1.100 s | Completed answer and research section; five links expanded successfully |
| Original ScienceAlert tinnitus URL, shared negative | 1.074 s | Correctly says no specific treatment was identified; registry not searched |
| ScienceAlert tinnitus, fresh browser lookup | 5.044 s | Reading transitioned to completed negative; no screenshot stage observed |
| ScienceAlert tinnitus, repeat after fresh lookup | 1.040 s | Dated negative answer reused |

These are automation observation upper bounds, not internal render timings. The first CAR-T shared-open observation occurred before rendering and is excluded. The fresh ScienceAlert check loaded the same report with the harmless numeric query `?story=20261115` to obtain a new cache key, after verifying the article title; the repeat used that same URL. The earlier 0.9.2 fresh Safari observation was 9.441 s (also a single upper-bound observation, not a controlled statistical comparison). The 12-run API comparison above used the original unchanged URLs.

After the third round, shared API lookups returned all four completed answers: CAR-T 247 ms, hearing 91 ms, teeth 93 ms, tinnitus 144 ms. Tinnitus now supports safe negative-result reuse. Prior shared API observations were 97–142 ms for the three treatment articles; no universal shared-network speedup is claimed. The improvement is avoiding unnecessary fresh/screenshot work and retaining eligible shared answers locally.

## Remaining latency and limits

Fresh treatment reading took 4.783–6.177 s in this sample, accounting for most remaining latency after source reuse. A first-ever uncached article is therefore not instantaneous. Existing tracked and saved-result paths are the near-instant paths; expanding independently prepared public coverage could extend them. A faster extraction strategy would require a separately evaluated accuracy/cost tradeoff. Model, prompts, matching thresholds, service tier, $13 monthly limit and background-reading permissions were unchanged.

No article text or screenshots are retained in this report or repository. Transient exact-input article payloads used for comparison were deleted after verification. Related-paper relevance remains a separate concern: the KCL enrichment section loaded, but some existing OpenAlex search matches were broad or unrelated; this release changes latency, not those relevance rules.
