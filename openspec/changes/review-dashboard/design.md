## Context

The public site reads pairs from D1 (`store/ingest/migrations/0011_pairs.sql`): staging from `thenwhat-store-preview` in the Palladio account, production still from legacy files while it waits for cutover. The operator wants a private view over both, signed in with a Cloudflare account.

## Decisions

### Cloudflare Access with the Cloudflare identity provider, checked again in the Worker

Access supports Cloudflare itself as an identity provider since May 2026, with a "Restrict to account members" option and a "Cloudflare Account Member" policy selector (https://developers.cloudflare.com/changelog/post/2026-05-19-cloudflare-as-identity-provider/). One Access application covers the whole host, pages, assets and API alike.

The Worker runs before every file and verifies `Cf-Access-Jwt-Assertion` with `jose` against the team's key set (`/cdn-cgi/access/certs`), with issuer = team domain and audience = the application's AUD tag, as Cloudflare's guide does (https://developers.cloudflare.com/cloudflare-one/access-controls/applications/http-apps/authorization-cookie/validating-json/). The token's email must also be on `OPERATOR_EMAILS`. A missing setting answers 503 to everyone. `workers_dev` and preview URLs stay off, so no address skips Access. One-click Access for Workers covers only workers.dev and preview URLs, so it is not used.

Alternatives: GitHub or Google as identity provider (works, but is not the operator's Cloudflare login); one-time PIN (email only, weaker); an app-level OAuth login (more code, a second session to manage).

### satnaing/shadcn-admin as the shell

MIT; Vite 8, React 19, TanStack Router, Table and Query, Tailwind 4, which build to static files the Worker serves. Its Clerk example, demo features and sign-in pages are removed. marmelab/shadcn-admin-kit was the close second: its react-admin data layer suits editing more than a read-only review. Refine is a framework to adopt for more than this needs.

### Read-only by listed statements, and by credentials for production

A D1 binding can write. `worker/reads.mjs` holds every statement the site may send; `read` refuses any other text, and a test checks each listed statement is one SELECT. Production will be read through the D1 REST API with a token that holds D1 Read alone, which also covers the case where production's store sits in another account than the Worker.

### Generic model views

Each page model in a bundle carries its JSON Schema (`$schema` rows of `pair_page`), so later phases show any model from its schema instead of a screen per model.

## Risks

- The Access token's `email` claim is assumed present for the Cloudflare identity provider. If it is not, the allowlist check refuses everyone, which fails closed; the check then moves to the claim Access does send.
- Tests sign tokens with a key made for the run and serve its key set where the Worker asks for Access's. They prove the checks, not Access's policy, which is set in the dashboard.
