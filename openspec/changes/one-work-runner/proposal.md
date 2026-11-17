# Proposal

## Why

The pipeline runs work in two ways. Link leads go through the work ledger, which resumes cleanly. A claim's preparation (`resolve`, `fetch`, `readings`, `terms`) runs as one process per step outside the ledger, with "finished" implied by what happens to be stored. A review on 17 November 2026 of the database as it stood on 16 November found that both ways turn a passing failure into a final answer:

- A site that answers 202, 429, 503 or 504 is recorded as never readable, like a 404. Only a 401 has a way back.
- A lead refused for a cause that was later fixed (no publication date read from the page, an outlet with no display name, a threshold since changed) is never read again short of raising the step's version, which reads every lead again.
- A lead that fails three times is skipped for good, and a model outage during a read counts as a failure of each lead it touches.
- `resolve` exits as succeeded when its lookups of a substance, an organisation or papers failed, so the claim is decided on a search that did not run. A claim never searched and a claim searched with no result both stand at "no trial record found": 83 live claims stood there, and 52 were archived for it.
- A claim is decided when its terms failed and nothing proposes them again: 206 of 594 live claims had no terms.
- Requests to registries are made inside the lock that keeps two reads from drafting one story, so reads that reach it wait on each other's network calls.

Each was fixed, where it was fixed, by a rule beside the one before. The rules about treatments and conditions are sound and measured; the layer that runs them is what repeats itself. This change rebuilds that layer once, as one module, and moves both ways of working onto it.

## What Changes

- One module owns how work runs: the outcome of a step, when a record is due again, how a source or a model is asked, and what is done when it cannot be.
- An outcome says which of three things it is: final, to be tried again after a stated time, or waiting for something to be fixed. Each carries a reason code, not prose.
- `thenwhat work requeue` makes due again the records that share a step and a reason. `thenwhat backfill retry-outlet` becomes one use of it.
- A model or a source that cannot be asked stops the run in every step, with no attempt counted against any record, as triage already does.
- A claim's preparation becomes ledger steps over claims: substance, registry search, papers, fetch, readings, terms, the records an article's page names, and the decision. `thenwhat prepare` keeps its name and runs them. **BREAKING** for scripts that read the per-step output of `prepare` or call the per-step commands for a pending claim.
- A claim is decided only when its substance lookup, its registry search and its fetch finished. Papers, readings and terms no longer hold the decision and stay due until done, so the daily run completes them.
- Each registry search leaves a record: what was asked, when, how many records came back, how many were kept, and whether a limit cut the rest.
- One call policy for registries, literature indexes and model calls: bounded retries, a stated wait honoured in either form, a ceiling on any wait, and a pause that every process sees.
- A lead's screening is due again when its outlet's listing changes.
- The requests for records an article's page names move out of the lock that settles which claim an article reports.

Unchanged: every rule about names, classes, conditions and duplicates; every prompt and threshold; which claims are approved, rejected or held for audit; the export and the site.

Not in this change, and left room for: storing a paid result for reuse under one key (`work-reuse-and-metrics` 4.3), keeping a read's draft when a later part fails and withdrawing only unscored candidates (`idempotent-runs-and-one-address` 5.3 and 5.5), and candidates for the same-claim decision (`same-story-candidates`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `work-ledger`: the outcomes an entry can hold, when a record is due, what a failure counts, a run stopped by a provider, making records due by reason, and steps whose record is a claim.
- `source-clients`: a wait the source states is honoured in either form and bounded, and a pause is shared by every process.
- `decision-steps`: a model that cannot be asked stops the step that asked.
- `entity-resolution`: a registry search leaves a record, a failed lookup is not a finished search, and a claim never searched is told apart from one searched with no result.
- `claim-extraction`: "Preparing many claims" becomes steps of the ledger, and says which steps a decision waits for.
- `lead-reading`: a site that cannot serve a page now is asked again, and a refusal for a cause that can be fixed is recorded as one. Defined by `openspec/changes/social-link-backfill`, not yet archived, so this delta adds requirements.
- `lead-screening`: a lead is screened again when its outlet's listing changes. Defined by the same change; this delta adds a requirement.

## Impact

- New package `pipeline/src/thenwhat/work/`. `backfill/runner.py`, `backfill/ledger.py`, `backfill/steps.py`, `backfill/allowance.py` and `backfill/outlet_hold.py` move into it or are replaced by it.
- `backfill/link_read.py`, `backfill/link_triage.py`, `backfill/link_screen.py`, `backfill/news_search.py`: return the new outcomes.
- `prepare.py`, `cli/prepare.py`, `cli/resolve.py`, `cli/readings.py`, `cli/terms.py`, `events/fetch.py`: the claim steps. The process-per-step runner in `cli/prepare.py` goes.
- `sources/base.py`, `llm/client.py`, `llm/decisions.py`: the one call policy.
- Database: new columns on `work_entry`, one new table for registry searches, a data migration of stored lead outcomes to reason codes. Migrations are added, not regenerated. They run on the writer only.
- `scripts/daily-run.sh`: reads the new report of `prepare`.
- One new dependency for retries (`tenacity`), and `respx` and `time-machine` for tests.
- `GLOSSARY.md`, `docs/url-to-claim.md`, `docs/daily-run.md`, `docs/backfill-loop.md`, `docs/sources.md`.
- No change to the export's shape, the site or the extension.
