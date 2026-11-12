# Proposal

## Why

A claim with no approved trial event was always given the status "preclinical only". The recent-headlines and dental runs (2026-11-11) showed five claims where that is untrue: their first reports described a study in people, the reviewer confirmed the evidence stage as early human, and no trial was matched because the treatment has no name a registry search can use (a gene therapy named only by its delivery method, a diet, a skin stamp, a printed scaffold, a phage therapy). "Preclinical only" on those pages says the work never reached people. The registries only show that no record was found.

## What Changes

- A new status, `no_trial_found`, for a claim with no approved trial event whose confirmed evidence stage is early human or late human.
- "Preclinical only" is kept for a claim with no approved trial event whose stage is in vitro, animal, or not yet confirmed.
- The new status can carry the no-signal overlay, like every status still open to further evidence.
- Confirming or correcting a claim's evidence stage brings its stored status up to date.
- The site words the new status "No trial record found", explains both no-trial statuses, and shows the new one in words only, off the stage track: where such a claim sits on the path is not known.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `status-derivation`: the confirmed evidence stage becomes an input, used only when no trial is found.
- `review`: confirming a stage refreshes the status.
- `site`: wording for the new status.

## Impact

- `status/rules.py` (pure), `claims/status.py`, `review/queue.py` (`confirm_stage` now takes the time), `cli/review.py`.
- Migration `0005` widens the status check and moves the claims stored as preclinical only with a stage in people.
- `site/export.schema.json`, `site/src/lib/status.ts`, `site/src/lib/export.ts`, the method page, `GLOSSARY.md`, `PRODUCT.md`, `CLAUDE.md`.
- Status is still decided by fixed rules. The stage is suggested by a model and set only in review; a stage the assistant set keeps the claim out of a normal export, as before.
