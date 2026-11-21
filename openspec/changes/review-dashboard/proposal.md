## Why

The operator reviews staging and production content by opening pages one at a time and reading D1 by hand. The operator's proposal `private-content-review` (written with Codex, 2026-11-21) asks for a private review site: one place to see every model the site reads, every page it answers for, how staging and production differ, and what public search returns. This change is the implementation boundary for that proposal. It runs alongside `pairs-site` and the lab's rerun without touching either.

## What Changes

- A new package, `review/`: a Worker and its pages, served at review.whatcameofit.com, separate from the public site's Worker.
- Cloudflare Access guards the whole host, signed in with the Cloudflare identity provider and limited to Palladio account members. The Worker checks the Access token again on every request and keeps its own operator allowlist, so either check alone refuses a reader.
- The pages reuse satnaing/shadcn-admin (MIT), trimmed to a read-only shell: sidebar, command menu, tables, cards, sheets.
- Every store read is one of a listed set of SELECT statements. Production, when added, is read with a D1 Read token only.
- Drafts (source, reason, affected pages, base version), when added, live in the review site's own store and reach the public site only through the existing lab, review and release gates.

Phases (plan: https://claude.ai/artifact/LW8fruJG6wwLEApLiVGyBy): shell and auth with the staging overview; model inventory; pages and search; production read-only and comparisons; lab projection; drafts. Drafts need the operator's approval before they are built.

## Capabilities

### New Capabilities

- `review-site`: who may read the review site, what it reads, and that it never writes to a pair store.

### Modified Capabilities

None. The public site, the store and the extension are unchanged.

## Impact

- New: `review/` (Worker, pages, tests), Makefile targets `review-test`, `review-build`, `check-review`, a CI suite.
- Cloudflare (phase 0, the operator): the Cloudflare identity provider in Zero Trust, an Access application for review.whatcameofit.com, its AUD tag and team domain. No deploy happens before that application exists.
