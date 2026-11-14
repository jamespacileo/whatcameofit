# Lookup speed release verification — 14 November 2026

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

Implementation accepted with eight protected checks; full site suite (508 tests), extension suite (155 tests), deployment rehearsal, strict OpenSpec validation and unsigned Safari build passed before independent review. Review found two edge cases: interrupted streaming after navigation and variable cache latency bunching paper origin starts. Both were reproduced and fixed, and stage timing semantics were corrected. The affected 62-test suite passes, including four navigation-tail regressions, two source pacing/cancellation regressions and a deterministic stage-duration check. Final review, CI deployment, signed local Safari update and repeat measurements follow.

The isolated subscription worker used Opus 5.5 for 1,194 s (1,199 s including verification), 62 turns, a 7,758-character handoff and a 1,136-character return summary. Reported usage: 112 input, 248,017 cache-creation, 8,310,791 cache-read and 123,427 output tokens. An initial local Python preflight failed before invoking the worker and was corrected using the installed Homebrew interpreter. Codex handled protected acceptance, full-suite verification, independent review and the three targeted review corrections. These measurements describe handoff/rework cost and do not establish subscription quota savings.
