# Proposal

## Why

The operator dropped claims on 2026-11-19 for tracked treatment and condition pairs, which the separate data lab makes. On 2026-11-20 he asked that legacy claims be removed completely ("we need to completely remove/prune legacy claims and any remaining references and code, as we're not using claims anymore", 14:09), and chose to delete the claims pipeline at once (15:01). The site has been built from the lab's bundle of pairs alone since pull request 400, so nothing reads the pipeline's export.

## What Changes

- **BREAKING** The Python pipeline (`pipeline/`), its seed data, export schema, daily and backfill jobs, Docker setup and CI suites are removed (pull request 402).
- The specs of capabilities that only the pipeline implemented are removed from `openspec/specs/`, since no code in this repository has that behavior any more: `article-leads`, `claim-extraction`, `daily-run`, `decision-steps`, `entity-resolution`, `evidence-events`, `knowledge-cards`, `lead-evaluation`, `lead-reading`, `lead-screening`, `lead-triage`, `link-leads`, `llm-usage`, `organisations`, `paper-facts`, `processing-metrics`, `record-readings`, `registry-corpus`, `related-research`, `reported-statements`, `review`, `source-allowances`, `source-clients`, `status-derivation`, `trial-facts` and `work-ledger`. Their text stays in git history. One requirement of `related-research`, "Public on-demand research context", describes the lookup service and the extension, not the pipeline, and was moved to `live-lookup`. A pair's status is derived in the lab by the same rules, which the site's method page states.
- The open changes that built on the pipeline are closed as superseded: `headline-funnel`, `idempotent-runs-and-one-address`, `trial-first-route` and `work-reuse-and-metrics`.

## What Does Not Change Here

- The site's specs that still name claims (`claims`, `open-data`, `anniversaries`, `source-pages`, `sharing`, `landing-pages`, `health-areas`, `clinical-classification`, `deployment`, and parts of `site-publishing`) are revised by `pairs-site` task 1.2, against the pair page models.
- `cloudflare-source-of-truth` (the store) stays open until the store's claim tables are settled at the cutover.
- The released extension's wire format, including the `claims` key of `lookup.json`, is unchanged.

## Impact

No reader-facing behavior changes: the pipeline published nothing since pull request 400. The operator unloaded both launchd jobs on 2026-11-20.
