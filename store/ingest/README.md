# store/ingest

The ingest service: a Cloudflare Worker, in JavaScript, with bindings for the store (D1, `STORE`), raw payloads (R2, `PAYLOADS`) and the work queue (`WORK`). It is the one address a writer outside Cloudflare hands records to. It holds no rule of the tracker: every record enters the store by the statements of `store/merge.sql`, bundled unchanged and sent as one D1 batch. Design: `openspec/changes/cloudflare-source-of-truth/design.md`, decisions 12 and 19.

Nothing here is deployed, and nothing here creates or names a real Cloudflare resource. `wrangler.jsonc` names each resource by binding; the ids are given at deployment by the operator and are not committed.

## Run it locally

```bash
make store-test                                   # every test, on D1's local engine
cp store/ingest/.dev.vars.example store/ingest/.dev.vars && node store/ingest/scripts/new-token.mjs device mini
make store-dev                                    # http://localhost:8787, after adding the token's entry to .dev.vars
```

`make store-dev` applies `migrations/` with `wrangler d1 migrations apply STORE --local` and starts `wrangler dev --local`. No account and no network are used.

## What is in it

| Path | What it is |
| --- | --- |
| `migrations/*.sql` | Applied in order, they make `store/schema.sql`; a test and `pnpm run generate -- --check` fail when they do not. `0001` is the schema as first applied and is never rewritten: a change to `store/schema.sql` is a new migration |
| `migrations/0002_ingest_service.sql` | The service's own bookkeeping: one row for each chunk a run handed over. Not a record of the tracker |
| `src/sql.generated.mjs` | The statements of `merge.sql`, `preview.sql` and `ingest.sql`, and every field a statement reads. Generated; the same test covers it |
| `src/store.mjs` | Register, stage, merge, report, report without applying, as functions of the D1 binding. The site's Worker can call these in-process for a lookup |
| `src/index.mjs` | The HTTP routes |
| `src/auth.mjs` | Tokens and what each kind may do |
| `src/check.mjs` | What a staged record must be at the door |
| `src/limits.mjs` | The bounds, each with the Cloudflare page it was read from on 2026-11-17 |

After changing `store/schema.sql`, `store/merge.sql`, `store/preview.sql` or `store/ingest.sql`, run `pnpm --dir store/ingest run generate`. Once a real store exists, a schema change is a new migration, not a regenerated first one.

## How a writer hands over a run

Every request carries `Authorization: Bearer <token>`. Without a token nothing answers.

1. `PUT /payloads/<sha256>` for each payload over 16 KB (`application/octet-stream`). The body is hashed; one that is not what its checksum says is refused and nothing is stored. A payload already held is not stored again.
2. `POST /runs` with `{id, writer, commit, steps, counts, checksum}` (and `request_class` for a lookup). The service sets the time, a day only for a lookup. Registering a run again writes nothing: it answers 200 when the run is the one registered (same writer, device, checksum, steps and counts) and 409 otherwise. The device is the token's.
3. `POST /runs/<id>/records`, once a chunk: a JSON list of `{kind, key, body}` with the header `X-Content-SHA256`, the SHA-256 of the body sent.
4. `POST /runs/<id>/merge`. The answer's `status` is `merged` (with the report: resolved, added, conflicts and matched for each kind), `refused` (an older step version, with the reason), `undone` (a statement failed and D1 rolled the batch back; the run still waits and can be dropped) or `not_merged` (the chunks that arrived are not the ones stated).
5. `GET /runs/<id>` reads the report again. `DELETE /runs/<id>` drops a run that was not merged.

`POST /runs/<id>/preview` in place of step 4 reports without applying, says what it cannot see (`not_checked`), and drops the run.

A run's `checksum` is the SHA-256 of its chunks' checksums, sorted and joined by a line feed. Sending a chunk twice, registering a run twice and merging a run twice each add nothing.

The consumer's queue is `POST /work/lease`, `/work/finish` and `/work/fail`; a device's slices are `POST /slices/take` and `/slices/release`.

## Tokens and scopes

The secret `INGEST_TOKENS` is a JSON list of `{name, role, device?, sha256}`. The service knows a token only by its SHA-256; `node scripts/new-token.mjs <role> [device]` makes a token and its entry. Revoking a token is removing its entry. A secret holds 5 KB, which is about 35 entries.

| Role | Registers | May stage | May also |
| --- | --- | --- | --- |
| `device` | `device` runs, for its own device | Every kind but `action`; decisions by rule or seed only; an approved claim only with its audit hold, unless the store already holds it approved and released | Put payloads, take and release slices |
| `daily` | `daily` runs | Every kind but `action`, and no decision by a person or an assistant | Put payloads |
| `lookup` | `lookup` runs | A link lead (with no `claim_slug`), its share, a payload, a registry trial, a reading, usage, an unlisted domain | Put payloads |
| `consumer` | `consumer` runs | Every kind but `action`, decisions by rule only | Put payloads, lease work |
| `export` | `export` runs | The action `publish`, by rule | Nothing |
| `operator` | `operator` and `migration` runs | Everything, every action | All of the above |

The `daily` and `operator` tokens may also read and clear the inbox.

A token reaches only runs it could have registered; any other run answers as if it did not exist.

A person's or an assistant's decision (`reviewed_by`, `decided_by`, `labelled_by` of `human` or `assistant`, and a `human_label`) travels only with the operator's token. A device runs scripts, and a script's decision is never recorded as a person's.

## The inbox of the bulk tier

The bulk kinds (registry trials, leads and what hangs from them, usage, measures) have their truth in the bulk file in R2, which only the daily job writes (`design.md` decision 20). The inbox is for what a reader's lookup and the store-side consumer create: when a `lookup` or `consumer` run hands such a record over, the service keeps it as it was staged, with the payload records it names, in its own table `inbox`, in the same batch as the merge. A run the merge refuses or undoes leaves nothing there.

- `GET /inbox?after=<seq>&limit=<n>` gives `{records: [{seq, run, kind, key, body}], through, more}`, oldest first, at most 2,000 records or about 4 MB. A record is exactly what a writer stages, so `thenwhat store merge-bulk` takes it as it is.
- `POST /inbox/folded` with `{object}` records a fold. `object` is the key of the delta that holds what was folded, `bulk/<build id>/delta-...`. It must be in the bucket and listed in its build's `deltas.json`, where `scripts/upload-delta.mjs --through <seq>` wrote how far it folded: the service reads `through` from that list, not from the caller. A `through` sent as well must agree (409 `through_differs`). The answer is what is recorded for that object, `{recorded, recorded_at, again, folded_through}`; recording an object again changes nothing.
- `POST /inbox/clear` with `{through}` removes the records up to there, and is refused (409 `not_folded`) for a `through` past the furthest fold recorded. So no record leaves D1 before its delta is in R2. For each run folded whole it also removes the rows that run added to D1's copies of the bulk tables, in one batch. A reader's lead the store-side consumer has not yet processed (its `lead_process` work is still due) is held back with its shares and reading, and the answer counts it in `leads_held`; a later clearing removes it once that work is done or has failed for good. Clearing twice changes nothing else. A device's, the daily job's and the operator's runs are not kept in the inbox: a slice of trials pushed on purpose stays in D1. A trial a lookup added is also left in D1 once a paper has been stored for it.

A payload over 16 KB that an inbox record names is in the bucket under `payload/<sha256>`; the service has no route that serves it.

## Progress of a backfill

- A slice's state is a record of the store, kind `trial_slice`, written only by the merge (`store/merge.sql`): a rule, the year it was chosen in, the slice's number, its group, how many trials it holds, and a count and a time for each stage. The pipeline hands every planned slice over, and again as each stage is reached; the merge keeps the larger count and the later time. The service has no route of its own that writes progress.
- `GET /progress` (operator, daily) reads it and answers `{stages, groups, sets: [{rule, year, total_slices, total_trials, stages: {<stage>: {slices, trials}}, counts, groups, slices, changed_at}], runs, rows, at}`: a set's totals are its slices'. Counts, group names and times, nothing of a record.
- `GET /progress/page` is a self-contained page of the same. It is served without a token and holds no count; it asks `/progress` with a token typed into it, kept for the tab only and sent as a header.

## Asked too often

Where the platform's rate-limit bindings are bound (`wrangler.jsonc`), a caller with no known token is answered 429 past 60 requests a minute from one address, and a token past 600 a minute. The counts are approximate and kept in each Cloudflare location on its own. On this machine there are none.

## One reading of a record

What is staged is the checked value written out again, never the bytes that arrived. JavaScript reads the last of a key given twice and SQLite the first, so the bytes could say one thing to the door and another to the store. A body that is not UTF-8, and a string holding half a character or a NUL, are refused for the same reason.

## Times

Every time in a record (`at`, and any field ending `_at`) is `YYYY-MM-DDTHH:MM:SS.ffffff+00:00`: UTC, to the microsecond, with its offset, as `pipeline/src/thenwhat/store/form.py` writes it. The merge compares times as text, so one form is the only safe one; any other is refused. A day alone (`YYYY-MM-DD`) is taken, for a reader's lookup. The service writes its own times the same way. One time is not in this form: `run.merged_at`, which `store/merge.sql` writes to the second with `Z`. Nothing compares it.

## What is refused at the door

- A body with no stated length, of the wrong content type, or over its bound: a chunk of 1.9 MB or 5,000 records, a run of 20,000 records, a payload of 8 MB (settings in `wrangler.jsonc`).
- A record of an unknown kind, without its natural key, or with a field that no statement reading that kind of record reads.
- A string longer than 2,000 characters (200 for a reported statement, as the schema says), anywhere in a record but the fields that hold a source's structured record on the one kind they belong to. A trial's `intervention_names`, its arms' names joined, may hold 20,000. The store keeps no article text, and a refusal never repeats what was sent.
- A payload whose body is not what its checksum and size say, or whose R2 object was never put.
- A ClinicalTrials.gov record that still names a person, in a `payload` record, a `source_record` or an object put to `/payloads`: officials, contacts, a site's contacts, an investigator's name, a sponsor or collaborator who is a person, the results' point of contact, any `email` or `phone`. The refusal names the kinds of field (`people`), never who. A writer removes them first (`pipeline/src/thenwhat/sources/people.py`); `src/people.mjs` is the same test and the two must agree. Other sources' records are not examined.

Nothing is logged: not a token, not a record, not a payload.

## Not built yet

These wait for the real resources or belong to another task: the export's snapshot read and the reference file (tasks 4.3 and 4.6), D1's restore bookmark on a large run (3.8), the run size set from timings on D1 itself (3.5), and a deploy target with its jurisdiction check (3.3).
