# Proposal

## Why

The pipeline and site from `phase-1-backfill` are built, and 25 candidate claims are checked in, but none has been run through the pipeline or reviewed. The site shows only the seeded example. This change is the content work that fills the first topic: it was planned as the last group of `phase-1-backfill` and moved here by the operator on 2026-11-11, because it needs live model calls and a person's review time, not code.

## What Changes

- Import the 25 dental regeneration candidates in `data/seed/claims.csv` as pending drafts.
- Run extract, resolve and fetch for each claim, live, for the first time.
- The operator reviews every draft claim, candidate match, follow-up paper and manual event, and confirms each evidence stage.
- Export and rebuild the site with the approved claims.
- Hand-check five published pages against their sources.
- Review the seeded USAG-1 claim, which was compiled without a person's review.

No behavior changes. If the live runs or the review show that a rule gives a misleading result, that is recorded and proposed as a separate change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. This change sets `skip_specs: true`: it uses the system as specified and changes no requirement.

## Impact

- **Needs before it can start:** a model key, the model's two prices and a contact address in `.env`.
- **Cost:** model calls for 25 extractions and the match scoring that follows, under the monthly ceiling.
- **People:** the operator's review time. Review decisions must be the operator's own.
- **External services:** first live requests to ClinicalTrials.gov, Europe PMC, Crossref and news sites, at the configured rates and with the contact address.
- **Data:** the local database gains real claims. From then on, schema changes need new migrations.
