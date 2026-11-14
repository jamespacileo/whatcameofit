# Design

## Context

The Astro site is built offline from a public export. Its Worker already owns dynamic requests and has a ClinicalTrials.gov API v2 client and optional KV binding. See proposal.md for the verified cookie failure.

## Goals / Non-Goals

Deliver a server-rendered, cookie-independent reader using the established Read surface. Do not change claim-status rules, broaden publication, call models, create a general registry proxy, or publish during this work.

## Decisions

- Serve `/trials/{NCT_ID}` through a small Worker module. Reuse `makeRegistry().fetch()` for public API access with an eight-second deadline. A server route avoids both browser cookie dependence and an extra build-time network dependency.
- Build `/trial-index.json` from official ClinicalTrials.gov URLs in the export; use it as an allowlist and for links back to claims. Share URL recognition between that index and the claim page.
- Build a `/trial-reader` HTML template with the existing Base layout. Replace explicit title, canonical identifier and content markers with escaped output on the server. Trial copy pages are noindex. The template uses global styles scoped under `.trial-reader` because inserted content is not Astro-compiled. The normal layout owns fonts, navigation, footer and notices.
- Cache validated raw API records and retrieval timestamps under a separate key prefix in `LOOKUP_RESULTS`: fresh for 24 hours, retained seven days. A stale copy is only for transient errors and retains its original date. KV failure must not prevent a successful live response.
- Use a dedicated `TRIAL_RECORD_READS` limit for uncached upstream requests; do not spend model/lookup quota. Require `CONTACT_EMAIL` for upstream access. Never forward reader headers.
- Keep UI restrained: plain secondary links beside the original sources; a title, provenance note, facts and readable sections on the reader. Preserve Figtree, navy, existing spacing and mobile targets. No new dashboard cards, score visuals, new palette or consent flow.

## Risks / Trade-offs

- Registry outage → explicit dated stale-copy notice or a 503 with recovery links.
- Cache and external data are untrusted → validate identifiers and timestamps and escape every text field.
- Public trial details can change independently of claim summaries → label them as registry details, not a new claim status.
- Pure Astro preview does not run the Worker → use loopback-only Wrangler dev for the final preview and real Safari check.

## Migration Plan

No data migration or package changes. Build the template and index with the existing assets, and deploy the Worker and assets together only after user approval. Rollback is the previous deployment; trial cache keys are versioned and do not affect existing lookup entries.
