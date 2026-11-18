# store

The truth store's SQL: the D1 schema and the one merge path every writer uses. A draft for review (`openspec/changes/cloudflare-source-of-truth`). Nothing here is deployed, and nothing here creates a Cloudflare resource.

| File | What it is |
| --- | --- |
| `schema.sql` | Tables, natural keys, CHECK guards, the FTS5 indexes, and the views that find a staged record's parent |
| `merge.sql` | The merge: 102 fixed statements sent as one D1 batch, each with its conflict rule above it |
| `preview.sql` | The report without the merge: what a run would add, match and put in conflict, counted and not tried |
| `ingest.sql` | What surrounds a merge: registering a run, staging records, reading the report, dropping a previewed run, the work queue, slices |
| `proof/` | A local proof in plain SQLite, and a check on D1's local engine |
| `ingest/` | The ingest service: the Worker that runs these statements for a writer holding a token. Its own `README.md` says how to run it locally |

Which Postgres table became what, and why: `openspec/changes/cloudflare-source-of-truth/store-tables.md`.

## Run the proof

```bash
python3 store/proof/proof.py --scenarios
```

Builds the schema in memory and runs 63 scenarios through `merge.sql` as a D1 batch runs it: every statement in one transaction, nothing read in between. The first 14 are the spike's. Before every merge it also takes the report without applying (`preview.sql`) and holds it to what the merge then reports.

```bash
docker exec -i thenwhat-db-1 psql -U thenwhat -d thenwhat -q -f - < store/proof/export_sample.sql > store/proof/sample/records.jsonl
```

Exports a sample from the working Postgres in natural-key form: every fifth claim with its records, about 5,900 trials, 2,500 scored leads. The session is read-only (`default_transaction_read_only`). It takes about four minutes, most of it checksums. Create `store/proof/sample/` first; it is not committed.

```bash
python3 store/proof/proof.py
```

Runs the scenarios, then loads the sample through the same merge in runs of 20,000 records, pushes the first run again to show nothing is added, and prints each table's size projected to the whole database against D1's limits.

Optional, and offline: `store/proof/d1_local.sh` applies the schema, one preview and one merge on D1's own local engine through `wrangler d1 execute --local`. It found one thing plain SQLite did not: D1 refuses a compound SELECT of many terms, so the report is several statements.

## How a writer hands over records

1. `register_run`, `state_steps`, `state_counts` (in `ingest.sql`).
2. `stage`, once per chunk: a JSON array of `{kind, key, body}`. `key` is the record's natural key as one string. `body` names parents by natural key, never by a row id.
3. The statements of `merge.sql`, in order, as one batch, with the run as `?1`.
4. `report`.

For a report without applying, step 3 is the statements of `preview.sql` instead, followed by `discard_run`. A D1 batch cannot be undone on request, so the report is counted from the staged records and the store, not by running the merge and taking it back.

A payload over 524,288 bytes (512 KiB) is put in R2 under `payload/<sha256>` before the merge; the staged `payload` record then carries `r2_key` and no `body`.

## Kinds and the keys their bodies carry

A staged record's `key` is its natural key as one string, parts joined by `|`. Five are relied on by `preview.sql`, which looks a parent up by them: a claim's is its slug, a source article's `slug|url_key`, an entity's `slug|type|name`, a link lead's its address key, a trial's `registry|number`.

| Kind | Parent named by | Its own key |
| --- | --- | --- |
| `payload` | | `sha256` |
| `claim` | | `slug` |
| `source_article` | `slug` | `url_key` |
| `promise`, `reported_statement` | `slug`, `url_key` | `description`; `text_key` |
| `entity` | `slug` | `type`, `name` |
| `entity_match`, `entity_substance`, `entity_article` | `slug`, `entity_type`, `entity_name` | `source_name`, `external_id`; none; `url_key` |
| `claim_term` | `slug` | `role`, `source_name`, `external_id` |
| `source_record` | | `kind`, `source_name`, `external_id` |
| `evidence_event`, `failure_flag` | `slug` | `dedupe_key`; `trial_external_id` |
| `trial_read` | | `source_name`, `trial_id` |
| `registry_trial`, `registry_load` | | `registry_name`, `external_id`; `registry_name`, `condition` |
| `article_lead` | `registry_name`, `trial_id` | `url_key` |
| `trial_paper` | `registry_name`, `trial_id` | `source_name`, `pubmed_id` |
| `trial_slice` | | `rule`, `year`, `number` |
| `link_lead` | | `url_key` |
| `link_share`, `link_lead_link`, `link_lead_label`, `lead_reading` | `lead_url_key` | place and time; record and reason; `labelled_by`; none |
| `decision`, `usage` | the run | `seq` |
| `measure_daily`, `measure_claim`, `work_entry`, `outlet_icon`, `work_slice`, `unlisted_domain` | | as their tables' primary keys |
| `action` | `slug` | `action`: `audit_clear`, `archive`, `unarchive`, `rename`, `merge`, `conflict_accept`, `conflict_dismiss`, `publish` |

A `rename` carries any of `new_slug`, and `old_name` with `new_name` (and `keep_old_name`, true unless stated). A `merge` carries `into_slug` and `gains`, the names the kept intervention gains, which the pipeline's rule chooses.

## Reading the SQL

- A statement in `merge.sql` ends at a line holding only `;`.
- Every statement after the first two reads `staged` or a `staged_of_*` view. Those are empty unless the run is in `merging`, so a refused run changes nothing.
- A record whose parent is not in the store is absent from its view, so it is neither stored nor counted. The counts then differ from what the run stated, `merge_guard`'s CHECK fails, and the whole batch is undone.

## Changing a table that holds rows

SQLite cannot alter a CHECK or a column's type, so such a change makes the table again. `ingest/migrations/0007_payload_inline_limit.sql` does this for `payload`, in one transaction, and is for an empty store only: on the loaded preview D1 stopped it after 38 s for its CPU time (17 November 2026, code 7429). A migration that makes a table again carries the line `-- rebuilds: <table>`; the cut-over (`ingest/scripts/cutover.mjs`) empties or replaces a preview store before it applies migrations and refuses to apply such a migration to a store that holds rows. A change that must reach a loaded store copies in batches across several migrations, or is designed not to need the table made again. See `docs/deploy.md`, "Cut-over: one command".

Migration `0008_work_entry_waits.sql` extends the work ledger to keep waiting claims and their retry details. A local bulk file upgrades in one transaction on its next merge, preserving earlier entries. For D1, build the new snapshot and use the existing [cut-over procedure](../docs/deploy.md#cut-over-one-command) to load it into a migrated store.
