# Proposal

## Why

ClinicalTrials.gov's study pages can display 403 when their browser session lacks `ncbi_sid`, preventing readers from checking the evidence. Its public API returns the same records without browser cookies, so the site can provide a readable alternative.

## What Changes

- Retain official registry links and add a quiet local trial-details link beside ClinicalTrials.gov records in claim timelines and matched records.
- Serve readable trial records using the existing public API client, the site's normal layout, and server-side caching.
- Show provenance, retrieval and registry update dates, explicit stale-data notices, and useful unavailable states.
- Verify the three baxdrostat records in Safari without registry cookies and provide a loopback-only local preview. Publication is excluded pending the user's review.

## Capabilities

### New Capabilities

- `trial-records`: local, source-attributed access to publicly cited trial registry records, including caching and failure behavior.

### Modified Capabilities

None. Existing canonical evidence links and claim-status rules remain intact.

## Impact

Claim-page links, a built registry-record index and shared reader template, Worker routing, a dedicated registry-read rate limiter, and the existing public API/KV bindings. No new package dependencies, model calls, export schema changes, or medical interpretation.
