# Proposal

## Why

Every interventional study on ClinicalTrials.gov was loaded into `registry_trial` on 16 Nov 2026 (467,064 trials, 468 requests). Trials change state, phase and results every day, and the daily run (`scripts/daily-run.sh`) did nothing to keep them current: its `refresh` step only reads the registries again for published claims. The job also needed a database address that no file gave it: the settings file has no `DATABASE_URL`, because Compose gives its containers their own, and on the Mac mini it was added to the installed property list by hand.

## What Changes

- The daily run gains a `trials` step before `refresh`: `thenwhat backfill load-trials --trials interventional --changes-only`. It calls no model; each request is claimed against the registry's allowance. Its counts of new and already stored trials go in the summary.
- `load-trials` stops cleanly when the registry may not be asked (allowance used up, or "too many requests"): it prints what it stored and a `Stopped:` line, exits 0, and is not recorded as completed, so the next changes-only load asks from the same date. Before, it exited 1 with no counts.
- The daily run never starts `news_search`. A trial the load adds, or whose searched name or indication changed, becomes due for it, and waits for a run started by hand or by the separate backfill job.
- `sh scripts/daily-run.sh plist` puts `DAILY_RUN_DATABASE_URL` into the property list as `DATABASE_URL`. A run takes `DATABASE_URL` from its environment, else `DAILY_RUN_DATABASE_URL`, else `DATABASE_URL` in `.env`, and with none stops before its first step and says so. Only where the address came from is logged.

## Impact

- `pipeline/src/thenwhat/backfill/registry_load.py`, `pipeline/src/thenwhat/cli/backfill.py`, their tests.
- `scripts/daily-run.sh`, `scripts/com.thenwhat.daily-run.plist`, `scripts/tests/daily-run.test.sh`, `docs/daily-run.md`, `.env.example`.
- Modifies "Registry terms" in `registry-corpus`. Adds `daily-run`, which has no spec yet; only what this change touches is specified.
