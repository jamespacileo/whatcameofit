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

Production deployment and smoke results are recorded after publication.

## Cloudflare runtime follow-up

The first production-model check returned clinical candidates but both research sources were unavailable. Cloudflare Workers does not implement Fetch's `redirect: "error"` mode. Use `manual` and refuse the returned 3xx, preserving the rule that an authenticated request never follows a redirect. Node mocks did not catch the runtime difference.

Two new offline tests run the actual workerd runtime through pinned Miniflare, using recorded outbound responses: both providers return results, real KV prevents repeat requests, and redirects are refused without forwarding the key. All 14 focused research tests pass after the fix. [Cloudflare Request documentation](https://developers.cloudflare.com/workers/runtime-apis/request/) documents the supported redirect modes.
