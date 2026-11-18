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
