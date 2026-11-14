# Design

## Context

See `proposal.md` for the motivation and the sample figures.

What exists today, as read in the code on 2026-11-14:

- Every table hangs off a claim. `entity`, `entity_match`, `evidence_event` and `source_article` all carry a `claim_id`. There is no place for a trial that no claim refers to.
- `thenwhat prepare` works out what a claim needs by looking at its own rows (an article with no content hash is unread) and runs each step as a separate command. That is a per-claim plan, not a record of work done, and it knows three fixed steps.
- Source clients share an in-process `Pacer` (`sources/base.py`). It keeps threads of one process to a source's rate. Two processes do not see each other.
- Model spend already has the shape wanted here: `llm_usage` rows and one ceiling checked at every call (`llm/ledger.py`). Requests to sources have nothing like it.
- `http_cache` stores payloads by request key with an expiry. It avoids repeat requests but does not say whether a record has been processed.

Constraints that shape the approach: the pipeline and database stay private on the operator's machine; tests use the real test database and recorded fixtures, with no live calls; article text is never stored, including in fixtures and logs; a source's terms are read and written into `docs/sources.md` before its client is written.

## Goals / Non-Goals

**Goals:**

- A run of tens of thousands of records can be stopped at any point and resumed without repeating finished work.
- A new step is one module plus one registration line, and runs only where it has not run.
- The operator sees the size and duration of a run before it starts.
- Several processes share one source's limit correctly.
- Steps stay plain functions, so they can be wrapped by an orchestrator later without being rewritten.

**Non-Goals:**

- No orchestrator, scheduler, queue service or worker daemon. `cron` and the command line are enough for one operator.
- No change to how claims are prepared. `thenwhat prepare` keeps working as it does; moving its three steps onto the ledger is a possible later change.
- No conversion of leads into claims, and no model calls anywhere in this change.
- No general plug-in system. Steps are modules in this repository.

## Decisions

### 1. The ledger is one table, and "due" is a query

One table, `work_entry`, with a unique key on (`record_kind`, `record_id`, `step`, `step_version`) and the columns the spec lists. Due work for a step is the records in scope with no finished entry at the current version, or with a different fingerprint: an anti-join, computed when asked.

*Why not a queue of pending rows?* A queue has to be filled, and filling it is a second thing that can be stale or half done. With an anti-join, adding a step or raising a version needs no enqueue pass: the work is due because the entry is absent. At 43,000 records, or 600,000, the query is cheap with the unique index.

*Why not Dagster partitions or assets?* It would give a UI and lineage, at the price of a second service, its own metadata database and a deployment to keep alive on a private machine. The ledger gives the one property needed now. A Dagster asset can call the same step function later, with the ledger still the source of truth.

### 2. Records are addressed by kind and id, without a foreign key

`record_kind` is a short text (`registry_trial` now; `claim`, `source_article`, `organisation` later) and `record_id` is that table's id. No foreign key, because the column points at several tables.

*Alternative:* one ledger table per record kind. Rejected: every new kind would need a migration and its own copy of the runner's queries. The cost of the chosen form is that deleting a record can leave entries behind; nothing in the pipeline deletes these records, and archiving is a flag.

### 3. No "claimed" state: the record's row lock is the claim

A worker selects a batch of due records with `FOR UPDATE SKIP LOCKED` on the record's own row, processes one, writes the step's result and the ledger entry, and commits. A second worker skips rows the first has locked. A worker that dies releases its locks with its connection, so nothing is stuck and there is no timeout to tune.

*Alternative:* a `claimed_at` column with a lease. Rejected as more states to get wrong for no gain at this size. The cost is one open transaction per record while its request is in flight, which is fine at a handful of workers.

Each record commits on its own. That is what makes "result and entry are saved together" true and keeps a failure with its record.

### 4. Fingerprint from declared inputs

A step declares which fields of a record it reads (the news search reads the name it searches by and the indication). The fingerprint is a hash of those values. A reload of the registry that changes a trial's enrolment count leaves the fingerprint, and so the ledger, alone.

A fingerprint is computed in Python, so "due" cannot compare it in SQL. Whatever writes a record calls one function that recomputes the fingerprint for each step of that record's kind and marks the entry stale when it differs. Due work is then: no finished entry at the current version, or a stale one.

The name a trial is searched by is worked out once, by rule, when the trial is loaded, and stored on the trial. That lets a step's scope ("has a usable name") be a plain query condition, and keeps the name rule in one place for every later step that works from trials.

### 5. A step is a small object with a fixed shape

A step provides: `name`, `version`, `record_kind`, a scope (a query condition), `inputs(record)`, `source`, `requests_per_record`, and `run(session, record, source_client) -> outcome`. It is registered in one list. The runner knows nothing else about it.

Outcomes are `done`, `nothing_found` and `failed`. "Nothing found" is finished work and must be distinct from failure, or every trial with no coverage would be retried for ever.

The package is `thenwhat/backfill/` with `steps/` inside it. It is not named "ledger", because `llm/ledger.py` already means the spend ledger.

### 6. Source allowances live in the database and are claimed in one statement

The allowance itself (requests per period, least interval, pause after a refusal) is configuration: `SOURCE_ALLOWANCES` in the environment, with a default for ClinicalTrials.gov only. What is used is one row per source in `source_allowance_use` (period start, requests used, time of last request, paused until). Before each request a worker runs one short transaction of its own that locks the source's row, waits out the least interval, checks the count and the pause, and increments. The row lock is what spaces requests across processes, and because the transaction is separate from the record's, a request stays counted even when the record it was for fails.

*Alternative:* keep the in-process `Pacer` and tell the operator to run one process. Rejected because it is exactly what failed in the sample: four workers, one allowance, no shared count.

Existing registry clients keep their `Pacer` for claim-level commands. Only steps go through the database allowance. Merging the two is left for later so this change touches no existing client behavior.

A too-many-requests answer sets `paused_until` and leaves the record due without counting an attempt: a refusal says something about the source, not about the record.

### 7. The registry corpus is loaded through the list endpoint

ClinicalTrials.gov's list endpoint returns up to 1,000 studies per page with a chosen set of fields. The whole phase 3 drug and biological frame is 44 requests, and the whole registry about 620. That is already in use for single lookups, so no new source or terms are involved beyond noting the bulk use in `docs/sources.md`.

*Alternative:* the registry's downloadable archive, or the AACT database copy. Rejected for now: a second format and a second set of terms to check, to save a few hundred requests.

Trials go in a new `registry_trial` table with the fields the spec lists as columns and the full payload as JSONB. Columns exist for what scopes and reports filter on (phase, intervention type, status, start date, sponsor class). A load of changes uses the registry's last-update date as its filter, with the previous load's completion time kept in a small state row.

### 8. The news index is Media Cloud, chosen by a gate at the start

The sample showed that the two obvious routes do not scale: the GDELT live interface refused the operator's address, and a search tool's allowance covers hundreds of records, not tens of thousands. The first task group read the terms, authentication, rate and coverage of GDELT's bulk datasets, Media Cloud and Common Crawl's news crawl on 2026-11-14 and recorded them in `docs/sources.md`.

**Decision (2026-11-14): Media Cloud.** It is the only candidate that returns exactly an address, outlet, title and date for a query of two terms, and it never releases article text, so none can reach the pipeline. It is free with an account and a key.

- **Allowance:** 4,000 requests a week by default, so the allowance is 4,000 in 168 hours with 30 seconds between requests. The 43,320 phase 3 trials take at least 11 weeks unless Media Cloud grants more.
- **What the operator must set up:** create the account and accept its terms, put the key in `.env` as `MEDIACLOUD_API_KEY`, check in Media Cloud's directory that the clinical trade press is covered and from when, and, if 11 weeks is too slow, email Media Cloud to ask for a larger allowance. None of this is done by the pipeline or by an assistant.
- **Until the key exists** the step is built and tested against synthetic fixtures and refuses to run live, naming the missing key.

*Alternatives:* GDELT on BigQuery matches keywords only from 2020, needs a paid cloud project, and its matching table carries fragments of article text that would have to be discarded; it stays the fallback if Media Cloud's coverage of the trade press proves thin. Common Crawl's news crawl has no search and would mean holding about 47 TiB of article pages, which this project never does.

The spec does not depend on the choice: it describes a search by intervention and indication that returns address, outlet, title and date.

### 9. Outlet kind by rule from the domain

A checked-in list maps domains to general news, trade press or press release; anything else is unknown. `docs/outlets.md` and `docs/outlets-articles.csv` already describe outlets for the site; the task checks whether that list can carry the kind before a second list is created. No model classifies outlets: the split between general news and trade press is the figure the operator needs to decide whether a registry-first backfill is worth running, and it has to be reproducible.

### 10. Migration

One new Alembic migration, `0013`, adds all five tables (the ledger, allowance use, registry trials, the load state and article leads), so the models and the migrations never disagree part way through the change. The initial migration is not regenerated: databases with real claims exist.

## Risks / Trade-offs

- [No news index permits bulk search on acceptable terms] → The gate in decision 8. The ledger, allowances and corpus are useful without it, and the step is ready for whichever source later qualifies.
- [Registry names are messy: codes, combinations, doses, descriptions] → The step's scope excludes trials with no usable name, and the plan reports how many are excluded so the loss is visible. The sample's rule-based cleaning found a usable name for 178 of 200 trials.
- [A hit means "an article names this intervention and indication", not "an article is about this trial"] → Leads are unreviewed and never published. The sample put trial-specific coverage at about two in five hits; deciding what a lead becomes is a later change.
- [An index may count trade press as news and inflate the hit rate] → Outlet kind is stored per lead and the report splits by it.
- [One open transaction per in-flight record] → Workers are capped at a small number, as `prepare` caps at 8. Request timeouts bound how long a row stays locked.
- [Entries pointing at records without a foreign key can be orphaned] → Records are not deleted in this pipeline. The plan counts entries only through a join to the record table, so an orphan is never counted as work done.
- [A step's version is raised by mistake and 43,000 records become due] → The plan shows the count and the hours before a run, and old entries are kept, so lowering the version back restores the previous state.

## Migration Plan

1. Apply the new migration. It only adds tables.
2. Load the phase 3 drug and biological trials.
3. Run `backfill plan`, then the news search with a limit of 200, and compare the hit rate report with the sample's 52% (31% after one search per trial).
4. Only after that comparison, run without a limit.

Rollback: the new tables can be dropped without affecting claims, matches, events or the export. No existing table or command changes.

## Open Questions

- How long an article lead is kept if no claim ever uses it. Nothing depends on this yet; leads are small and hold no text.
- Whether `thenwhat prepare`'s three steps should move onto the ledger. Deferred until a second record kind is in use.
