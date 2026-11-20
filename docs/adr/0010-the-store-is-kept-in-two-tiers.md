# 10. The store is kept in two tiers: what Cloudflare reads in D1, the rest as one file in R2

**Superseded on 2026-11-20.** The operator removed claims and the claims pipeline that day. Nothing in this repository acts on this decision any more; it is kept as the record of why the removed code worked as it did.

Date: 2026-11-17. Status: accepted. Change: `openspec/changes/cloudflare-source-of-truth` (`design.md` decision 20). Amends `docs/adr/0008`.

## Context

`0008` put every record of the tracker in one D1 database. On 2026-11-17 the whole working database was built into one store file through the store's own merge (5 min 47 s, 2,239 MB), dumped as SQL and loaded into the preview D1 in full. That showed the full load works. It also showed what the full load carries: most of its rows are registry trials, link leads and their shares, which nothing on Cloudflare reads today. The site's export reads claims and what hangs from them, the ingest service reads its runs and work, and a reader's lookup writes leads and counts. Every load, check and restore of D1 paid for the rows nothing reads.

## Decision

Decided by the operator on 2026-11-17.

- **The hot tier is D1.** It holds every table that the export of the site from the store, the ingest service's routes, the merge of a hot run or a reader's lookup reads. The list, with the reason for each table, is `store-tables.md`. The code that splits a build is `pipeline/src/thenwhat/store/tiers.py`.
- **The bulk tier is one SQLite file in R2.** It has the same schema and holds every other table: registry trials, article leads, link leads with their shares, links, labels and readings, the registry route's ledger, model spend and the measurements. It is not loaded into D1. Restoring it is downloading it.
- **A hot row never references a bulk row.** Foreign keys run from bulk to hot only. A hot record names a bulk one by its natural key as text: an event names its trial by registry and identifier. A test holds this against the schema.
- **Payloads go with what points at them.** A payload that rows of both tiers point at is kept in both.
- **A load is verified by checksum.** Each table gets one statement of aggregates, run alike on the file and on D1. D1 answers it in one row from one scan. The rows are not fetched back.
- **After the cut-over, the bulk file is the truth for bulk kinds.** The daily job is its one writer: it merges the day's bulk records into the file by the same `store/merge.sql`. It keeps the day as a delta object beside the last bulk build, a few megabytes against 1.9 GB. A restore replays the deltas onto the downloaded build. The day's hot records go through the ingest service to D1, as before.
- **A lookup's bulk records wait in D1.** Leads, shares, trials and readings that a reader's lookup creates go into D1's otherwise empty copies of those tables. The daily job folds them into the bulk file and clears them.
- **A hot row that needs a fact of a trial or a lead carries it itself.**

## Consequences

- **This gives up part of `0008`'s one source of truth.** The tracker's records now live in two places: D1 for the hot tables, and the bulk file with its deltas for the rest. The bulk file has one writer, and no Worker can query leads or stored trials. Going back is one full load: `thenwhat store build --tier all`, dumped and loaded. That loaded the whole store into the preview D1 in about 9 minutes on 2026-11-17.
- **A lookup does not see the bulk file.** A lookup's lead or trial is not matched against the bulk file until the daily fold. A lookup's share or reading whose lead is only in the bulk file does not resolve: its run is undone, and the reader still gets the answer.

- **The bulk tier cannot be queried from a Worker.** Serving a trial's page from the store (phase 5) first moves `registry_trial` and its search to the hot tier.
- **D1's lead tables hold only lookups' leads after the cut.** A reader's lookup still stages leads, shares and readings into D1, so D1's `link_lead`, `link_share` and `lead_reading` hold only what lookups add. The bulk file holds the history. A lookup of an article whose lead is only in the bulk file is answered as for a new lead.
- **A claim merge in D1 moves only the leads D1 holds.** The next bulk build carries the merge from Postgres.
- **A full load stays one command away.** `thenwhat store build --tier all` writes the whole store as one file. A table is moved between tiers by changing its line in `TIER`; the test then checks the references still run one way.
- **The checksum shows that a load arrived whole, and nothing more.** It is not cryptographic. It does not catch two rows swapping values, or a change inside a value that keeps its length and its first, middle and last characters.

## Amended 2026-11-17: the trial target set reaches D1 by slices

Decided by the operator and the coordinator later the same day. The trials of interest go to production progressively, with visible progress. The set is one rolling rule, `active-or-ended-this-year`, defined by `backfill/trial_sets.rule_of`.

- **A build does not split a kind by set.** `registry_trial` and `trial_paper` stay bulk, and the bulk file keeps every trial and its papers, the set's included. Nothing depends on D1 holding the whole set.
- **The set reaches D1 only by slice pushes.** It is pushed through the merge about 2,000 trials at a time, each slice as its own run with its trials, their payloads, their papers (`trial_paper`, without abstracts) and its state (`trial_slice`), using `thenwhat backfill slices run --push`. These trials are hot because a device or the operator pushed them. The ingest service never folds or clears them: only a lookup's and the consumer's records go to its inbox, and clearing never removes a trial.
- **The push state a build seeds holds only the hot tier's records.** A slice pushed after the base load therefore sends its trials, which that load did not hold, and none of the records it did.
- **A store loaded afresh holds none of the set's trials.** A slice's `in_store` is bound to the build its push state names, so a push state from a new build makes every slice due again. `--again` does the same by hand. The coverage report reads "in D1" from the store's own `trial_slice` rows.
- **A trial that leaves the set**, next year or by a change of status, keeps its rows in D1. No step deletes a fact the store has been given.
