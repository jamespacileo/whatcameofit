# Public lookup integration verification

2026-11-13. Scope: tasks 9.1–9.6, public on-demand lookup; private pipeline candidate approval/origin tasks remain open.

- Existing site suite: 216 passed before the three review regressions were added. Targeted research suite: 12 passed, including recorded provider payloads, missing contact/key, paid/unknown/exhausted allowance refusal, 429 cooldown, empty cache, seven-day expiry, malformed source isolation, request/body timeout and stalled cache. Worker tests preserve identical clinical candidates with and without enrichment.
- Extension: 114 tests passed. Shared research wording carries no clinical confidence; source sections start collapsed and links work. Build version 0.9.0.
- Pipeline regression: 609 tests passed; ruff and ty passed.
- Live provider probe through the Worker request handler (injected model/registry, real OpenAlex and ROR): HTTP 200, ten papers for median nerve stimulation/Tourette syndrome, University of Nottingham ROR 01ee9ar58. A second lookup made zero API requests. A full production-model lookup is the post-deployment check.
- OpenAlex account usage after initial live probe: $0.002 of $1/day, prepaid $0. Recorded fixture capture uses one additional $0.001 free query. Authenticated allowance is nested under `rate_limit`; fixtures preserve that observed envelope. No key occurs in any tracked/unignored file.
- Browser: website route exercised with the real metadata response, panels initially closed, five paper links displayed, no horizontal overflow at 390/768/1440px. Extension renderer exercised at 380px, panels open by keyboard/mouse with focusable links and no overflow. Browser renders are outside Git in the project devcache.
- Manual UI detector: no findings. Deployment rehearsal built all 84 published claims (306 pages), passed publication guards and Wrangler dry-run.
- Review fixes: per-provider error boundaries preserve sibling data; metadata cache operations time out after 200ms; nested ROR fields are validated; recorded public source fixtures replace synthetic success fixtures.

## Cloudflare runtime follow-up

The first production-model check returned clinical candidates but both research sources were unavailable. Cloudflare Workers does not implement Fetch's `redirect: "error"` mode. Use `manual` and refuse the returned 3xx, preserving the rule that an authenticated request never follows a redirect. Node mocks did not catch the runtime difference.

Two new offline tests run the actual workerd runtime through pinned Miniflare, using recorded outbound responses: both providers return results, real KV prevents repeat requests, and redirects are refused without forwarding the key. All 14 focused research tests pass after the fix. [Cloudflare Request documentation](https://developers.cloudflare.com/workers/runtime-apis/request/) documents the supported redirect modes.

## Production acceptance

- PRs [37](https://github.com/jamespacileo/whatcameofit/pull/37) and [42](https://github.com/jamespacileo/whatcameofit/pull/42) merged. Commit `3e15a6902e4e595050a2f7cd4daac1ef834bd7fc` passed tests/build, deployment rehearsal, production deployment and live-site checks in [run 43492354826](https://github.com/jamespacileo/whatcameofit/actions/runs/43492354826), completed 2026-11-13 19:29 UTC.
- A real lookup submitted through the published website (no mocked responses, production model and registries) returned HTTP 200, both research sources `ok`, twelve OpenAlex papers and University of Nottingham (`https://ror.org/01ee9ar58`). Trial candidates still included NCT05269953.
- The website displayed five paper links and one organisation link in initially collapsed sections. Both opened correctly, there was no horizontal overflow, and the browser reported no console errors.
- After verification, the authenticated OpenAlex allowance endpoint reported $0.006 used of $1/day, $0.994 remaining, and zero prepaid balance/remaining. No paid plan or top-up was enabled. The existing OpenAI $13 monthly controls were retained.
- Safari 0.9.0 was built, locally signed, verified and installed. Safari Settings confirmed that version enabled and the older signed copy disabled, leaving one active toolbar button. App Store submission 0.8.0 was not changed by this integration.

## Citation-independent discovery correction — 2026-11-14

Reported source: [King's lab-grown-teeth article](https://www.kcl.ac.uk/news/lab-grown-teeth-might-become-an-alternative-to-fillings-following-research-breakthrough). Expected research: [PMID 39532305](https://pubmed.ncbi.nlm.nih.gov/39532305/), OpenAlex W4404326590, DOI 10.1021/acsmacrolett.4c00520, *Generating Tooth Organoids Using Defined Bioorthogonally Cross-Linked Hydrogels* (2024).

Diagnosis: the page reader correctly extracts the PubMed identifier. `lookUp` previously supplied it only to Europe PMC for clinical-trial numbers, while OpenAlex received intervention/indication keywords. A read-only production cache check returned nineteen other papers and omitted this work. A fresh citation-free baseline returned twenty other papers, so cache reuse was not the root cause. Its queries were `lab-grown tooth regeneration Missing or damaged teeth` and `tooth tissue engineering Missing or damaged teeth`.

Two separate red tests were established before implementation: direct PubMed citation retrieval, and discovery with no citation or target identifier supplied. The latter also failed in the actual workerd runtime. News article text was never saved; fixtures hold structured extraction and public bibliographic metadata only.

After implementation, a fresh live extraction with all URLs, DOI strings and linked PubMed identifiers removed generated `tooth formation material` and `tooth cell communication`, naming Xuechen Zhang and Ana Angelova Volponi from the report. Four OpenAlex searches ran: the first topic separately scoped to each researcher, then both topics unscoped, all bounded by the report's 2025-04-14 date. The expected work ranked **1 of 20**. Its identifier was used only in the final assertion. The full title and DOI were not input to discovery. Separate real singleton lookups by DOI and PMID resolved to that same work and deduplicated to one result.

Repeat the opt-in live diagnostic from the repository root (uses configured providers; not run in CI):

```sh
rtk proxy node --env-file=.env site/scripts/check-paper-discovery.mjs \
  --url https://www.kcl.ac.uk/news/lab-grown-teeth-might-become-an-alternative-to-fillings-following-research-breakthrough \
  --expected https://doi.org/10.1021/acsmacrolett.4c00520
```

- Offline: 262 site tests passed, including 75 focused research/Worker tests and the citation-free workerd/KV regression; all 114 extension tests passed. The final site build and strict change validation passed. Clinical candidate behavior remains covered by the existing invariance test.
- Review corrections: reject overlong identifiers rather than truncating them; reject invalid timestamp bounds; report a failed citation-only provider lookup as unavailable. Each correction first failed a targeted test, then passed.
- OpenAlex allowance after the checks: $0.127 used account-wide of the $1 daily free allowance, $0.873 remaining, zero prepaid balance/remaining. This is an account snapshot, not a claim that this task used the entire amount. No paid features or additional model calls per lookup were introduced.
- Implementation delegation: isolated subscription worker `claude-opus-5-5`; 259.533 seconds overall, 6,258-character dispatched prompt and 1,371-character worker summary. Reported usage: 34 uncached input, 61,317 cache-creation input, 597,965 cache-read input and 24,297 output tokens. Protected regressions passed. Codex integrated three Worker modules and tests, renamed the worker's new test file to avoid an unrelated existing filename, and made the three review corrections above. These measurements do not establish quota savings.
- Scope: this fixes the extension's public on-demand lookup pipeline. The separate private Python paper-candidate scoring, origin selection and export were implemented on main while this correction was prepared and are unchanged by it. General retrieval quality beyond this case is not yet measured; papers remain unreviewed results. These checks preceded deployment; release acceptance is tracked in task 10.5. Existing shared/local answers require an explicit search again after release or cache expiry.
- Pre-merge review on current main found that a failed citation followed by a completed keyword search could be cached as a whole answer for 24 hours. The correction preserves OpenAlex's unavailability and excludes incomplete OpenAlex answers from shared-cache writes and reuse. An integration regression reproduces the outage, then verifies recovery and reuse of successful per-query metadata. Standards review found no other actionable issues; Spec review found no actionable issues.
