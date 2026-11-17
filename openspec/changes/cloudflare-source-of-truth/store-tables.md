# Where each Postgres table goes

Read with `store/schema.sql`. Row counts and sizes are of the working database `thenwhat` on 2026-11-16 (Alembic revision `0026`, 3,094 MB), measured by read-only queries. Brought up to revision `0032` on 2026-11-17: what that changed is said in the rows for `claim`, `claim_change` and `registry_trial`, and the sizes under "What the sample showed" were measured again that day. Sizes include indexes. Counts of the tables under 15,000 rows are the planner's estimates.

**As is**: same columns, with JSON and arrays as JSON text and row ids replaced by natural keys in what a writer sends. **Reshaped**: the table or its key changed. **Local**: stays on a device and is not migrated. **Dropped**: not kept anywhere.

| Postgres table | Rows | Size | Goes | Store table | Tier | Reason |
| --- | ---: | ---: | --- | --- | --- | --- |
| `claim` | 1,795 | 1.6 MB | Reshaped | `claim`, `claim_action`, `claim_alias`, `work_item` | hot: Read by the export | `merged_into_id` is `merged_into`. `registry_search_due_at` is not a column: a claim due to be searched again is a `work_item` due for `prepare`. Gains `origin` (a reader's claim publishes without the hold, a backfill's waits), `merged_into`, and the run that added and changed it. Holds, clears, archives, merges and renames are also written to `claim_action`, which the list of claims published from readers' leads reads |
| `claim_change` | 0 | | Reshaped | `claim_action`, `claim_alias` | hot: Read by the export (as actions and aliases) | Added on main by migration `0032`. A merge or a rename is a row of `claim_action` with what was done; a former slug is a row of `claim_alias`. Its `record`, the rows a merge moved by id, has no counterpart yet, so a merge cannot be undone in the store (task 4.7) |
| `source_article` | 2,469 | 1.4 MB | Reshaped | `source_article` | hot: Read by the export | Unique on claim and address key, not claim and address as written. By a rough copy of the address key, 8 articles are held twice by one claim today; the migration keeps the first of each |
| `promise` | 834 | 0.2 MB | Reshaped | `promise` | hot: Read by the export | Had no natural key; now unique on article and description. No two promises share that key today |
| `reported_statement` | 10,257 | 5.5 MB | As is | `reported_statement` | hot: Read by the export | Already keyed by article and text key. `decision_ref` is rewritten from a row id to a natural key |
| `entity` | 14,913 | 2.8 MB | Reshaped | `entity` | hot: Read by the export | Had no natural key; now unique on claim, type and name. No two entities share that key today |
| `entity_article` | 4,720 | 0.4 MB | As is | `entity_article` | hot: Read by the export | |
| `entity_match` | 44,955 | 21 MB | As is | `entity_match` | hot: Read by the export; names its record by source and identifier, as text | Indexed by record, so a trial's page finds the claims that name it |
| `claim_term` | 2,158 | 0.9 MB | As is | `claim_term` | hot: Read by the export | |
| `term_record` | 791 | 1.6 MB | Reshaped | `source_record` | hot: Read by the export (`source_record`) | One table for a source's own record of a thing, kept once: the four tables had the same columns and the same rule (the later fetch wins) |
| `organisation_record` | 1,031 | 2.6 MB | Reshaped | `source_record` | hot: Read by the export (`source_record`) | As above |
| `paper_record` | 6,247 | 15 MB | Reshaped | `source_record` | hot: Read by the export (`source_record`) | As above. Its payload is already reduced (no abstract, no authors) and is what the export reads, so it stays in the row |
| `entity_substance` | 371 | 2.2 MB | Reshaped | `entity_substance`, `source_record`, payload in R2 | hot: read by nothing, but it hangs from an entity (472 rows) | The substance's record is up to 664 KB, the largest row the spike found. The link from entity to substance and the codes stay in the row; the record is a payload |
| `evidence_event` | 31,862 | 312 MB | Reshaped | `evidence_event`, payload in R2 | hot: Read by the export; names its trial by registry and identifier, as text, never by row | The raw payload leaves the row for R2, once per checksum: 19,723 distinct payloads, 333 MB, the largest 2.4 MB. Gains `content_sha256`: see the finding below |
| `failure_flag` | 0 | | As is | `failure_flag` | hot: Read by the export | |
| `trial_read` | 4,958 | 1.4 MB | Reshaped | `trial_read` | hot: Read by the export; names its trial by source and identifier, as text | Takes its readings in as a JSON column |
| `reading` | 12,784 | 2.8 MB | Reshaped | `trial_read.readings` | — | Readings are replaced as a set with their read, and nothing asks for one alone |
| `registry_trial` | 467,064 | 637 MB | Reshaped | `registry_trial`, `registry_trial_status`, `registry_trial_fts`, `payload` | bulk: Read by nothing on Cloudflare until phase 5 (tasks 7.1 to 7.3) moves it to hot | All of them move, with the eleven columns of activity and results that migration `0031` added. The columns are what the plain page shows. The payload (1,711 bytes on average since `0031`; 32 are over 16 KB and go to R2) is kept in `payload`, in the row. Gains `checked_at`, a history of states, and a search index |
| `registry_load` | 1 | | As is | `registry_load` | bulk: Read by the daily job on a device | Lets any device or the daily job ask the registry only for what changed |
| `trial_paper` | not counted | | Reshaped | `trial_paper`, `payload` | Added to the store on 2026-11-17 for the progressive load of trials (migration `0006`). bulk, proposed: it references its trial, and trials are bulk; the pipeline's tier list decides. Keyed by trial, index and the paper's number; `raw_payload` is a payload by checksum; the later fetch wins |
| `article_lead` | 44,166 | 45 MB | Reshaped | `article_lead` | bulk: Read by nothing on Cloudflare; references its trial | `raw_result` is dropped: it is the search service's listing fields, all of which are already columns. Keyed by address key |
| `link_lead` | 682,022 | 430 MB | Reshaped | `link_lead`, `link_lead_fts` | bulk: Read by nothing the export reads; a lookup adds new leads to D1 after the cut (design decision 20) | Only leads on listed outlets that were scored, read, labelled or tied to a claim: 414,477. The other 267,545 stay in a device's run files. `outlet_kind` cannot be `unknown` in the store |
| `link_share` | 826,187 | 165 MB | Reshaped | `link_share` | bulk: With its lead | The shares of the leads kept: 507,906. A reader's asking is a share with a date and nothing else, which a CHECK holds |
| `link_lead_link` | 11,595 | 3.4 MB | Reshaped | `link_lead_link` | bulk: With its lead | Names the record by natural key, not by row id |
| `link_lead_label` | 560 | 0.1 MB | As is | `link_lead_label` | bulk: With its lead | |
| `decision_log` | 456,537 | 171 MB | Reshaped | `decision_log` | hot: Read by the export (a match's and a stage's decisions) | Keyed by run and place in the run; `input_ref` rewritten to natural keys. **The 420,115 `lead_triage` decisions stay local**, decided by the operator on 2026-11-16 (`design.md` decision 16): the lead already holds its score and version |
| `llm_usage` | 49,910 | 6.9 MB | Reshaped | `llm_usage` | bulk: Read by nothing on Cloudflare yet (task 4.5) | Keyed by run and place in the run. The run says which device or which readers spent it |
| `work_entry` | 1,104,014 | 283 MB | Reshaped, mostly dropped | `work_entry`, `work_item` | bulk: the registry route's ledger, read by a device's backfill only; work the store itself is to do is `work_item`, hot | The 1,100,282 link-step entries are dropped: a lead's own columns say what was scored and read. The 3,732 `news_search` entries move, named by natural key. Work the store itself is to do is `work_item` |
| `measure_daily` | 0 | | As is | `measure_daily` | bulk: Read by nothing on Cloudflare | A merge adds a run's totals to the day's |
| `measure_claim` | 0 | | As is | `measure_claim` | bulk: Read by nothing on Cloudflare; references its claim | |
| `measure_rolled_day` | 0 | | Local | | — | Says which days a device has already added up. A run is merged once, which does that job in the store |
| `outlet_icon` | 131 | 0.5 MB | As is | `outlet_icon` | hot: Read by the export | Small enough to stay a BLOB in the row |
| `source_allowance_use` | 75 | 0.1 MB | Local | | — | A device's own pacing of a source. The store-side consumer needs its own; see open question in `design.md` |
| `http_cache` | 44,663 | 761 MB | Local | | — | A device's cache |
| `alembic_version` | 1 | | Dropped | | — | D1 keeps its own record of migrations applied |

Rules that main's migrations `0029` and `0030` put in Postgres, and where they are here: one intervention a claim, an article never without its claim on a lead, and counts and amounts that are not negative are CHECKs or unique indexes in `store/schema.sql`. That a row naming an article and a claim names the article's own claim is held by the merge, which finds the article through its claim. Not held: that a lead read into a claim names the claim, because a lead's outcome and its tie to the claim are taken by two statements.

**Tier** (operator's decision of 2026-11-17, `design.md` decision 20, `docs/adr/0010`): **hot** is loaded into D1, because something on Cloudflare reads it; **bulk** is kept as one SQLite file in R2 and restored by downloading it. The tier of every table of `store/schema.sql` is `TIER` in `pipeline/src/thenwhat/store/tiers.py`, and a test fails when a table has none or a hot table references a bulk one. Of the store's own tables: the run tables (`run`, `run_step`, `run_stated`) are in both files, because every row names the run that added it; `payload` follows what points at it; `stg`, `merging`, `merge_report`, `merge_guard`, `store_step`, `work_item`, `work_slice`, `deployment`, `evidence_conflict`, `claim_fts` and `unlisted_domain_count` are hot; the bulk file also keeps a copy of `claim`, `claim_alias`, `claim_action` and `source_article`, the hot rows bulk rows hang from, which the daily job's merge into it refreshes; `registry_trial_status`, `registry_trial_fts`, `link_lead_fts` and `lead_reading` are bulk with the tables they belong to.

`trial_slice` is new with the progressive load too (migration `0006`): one row a slice of trials (a rule, a year, a number), saying how far it has come, which the site's progress reads; so it is hot. A merge keeps the later of each stage's time and the larger of each count, so a slice never goes back a stage.

New in the store, with no Postgres table behind them: `run`, `run_step`, `run_stated`, `stg`, `merging`, `merge_report`, `merge_guard`, `store_step` (the merge); `payload`; `evidence_conflict`; `lead_reading` (a lookup's reading, awaiting the rules); `work_slice`; `work_item`; `unlisted_domain_count`; `deployment`; `claim_fts`.

## What the sample showed

- **Size.** Measured again on 2026-11-17 at revision `0032`: the sample (55,096 records) is 48.2 MB as SQLite. Projected to the whole database: **1.67 GB**, 17% of D1's 10 GB. The largest parts are trial payloads in rows (670 MB), trials (415 MB), leads (213 MB) and shares (70 MB). On 2026-11-16, before the wider trial record, it was 1.20 GB. With trial payloads in R2 instead it would be about 1.0 GB.
- **Largest value in a row:** 29,956 bytes, against 2,000,000.
- **Longest statement:** 2,827 bytes, against 100,000. Most bound parameters: 8, against 100.
- **Not sampled:** `article_lead` (about 15 MB at 350 bytes a row) and `outlet_icon`. Neither changes the picture.

## A finding that changes the design: what "differs" means for evidence

The spike compared an event's payload checksum. On the real data that would be wrong: the daily job fetches a trial's record again, the record has changed somewhere (an enrolment figure, a contact), and every approved event read from it would count as differing. Each published claim with a trial would be held for audit on the next refresh.

So an event carries two checksums. `payload_sha256` is of the record as fetched. `content_sha256` is of the fields a status is derived from: type, date, state, phases, outcome and identifier. Only a different **content** under the same key is a conflict. A different payload with the same content is the same event from a newer fetch, and the event then points at the newer payload, which is what `trial-facts` already asks for ("using the record fetched most recently"). Scenarios 11 and 20 to 24 of the proof cover both.

How often content really differs under one key is not known. It is to be counted during the parallel run before the hold is trusted on published claims.
