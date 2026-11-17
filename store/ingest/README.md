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
| `migrations/0001_store_schema.sql` | `store/schema.sql`, byte for byte. Written by `pnpm run generate`; a test fails when the two differ |
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
2. `POST /runs` with `{id, writer, commit, steps, counts, checksum}` (and `request_class` for a lookup). The service sets the time, a day only for a lookup. The device is the token's.
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
| `device` | `device` runs, for its own device | Every kind but `action` | Put payloads, take and release slices |
| `daily` | `daily` runs | Every kind but `action`, and no decision by a person or an assistant | Put payloads |
| `lookup` | `lookup` runs | A link lead, its share, a payload, a registry trial, a reading, usage, an unlisted domain | Put payloads |
| `consumer` | `consumer` runs | Every kind but `action`, decisions by rule only | Put payloads, lease work |
| `export` | `export` runs | The action `publish`, by rule | Nothing |
| `operator` | `operator` and `migration` runs | Everything, every action | All of the above |

A token reaches only runs it could have registered; any other run answers as if it did not exist.

## What is refused at the door

- A body with no stated length, of the wrong content type, or over its bound: a chunk of 1.9 MB or 5,000 records, a run of 20,000 records, a payload of 8 MB (settings in `wrangler.jsonc`).
- A record of an unknown kind, without its natural key, or with a field no statement reads.
- A string longer than 2,000 characters (200 for a reported statement, as the schema says), anywhere in a record but the fields that hold a source's structured record on the one kind they belong to. The store keeps no article text, and a refusal never repeats what was sent.
- A payload whose body is not what its checksum and size say, or whose R2 object was never put.

Nothing is logged: not a token, not a record, not a payload.

## Not built yet

These wait for the real resources or belong to another task: the export's snapshot read and the reference file (tasks 4.3 and 4.6), D1's restore bookmark on a large run (3.8), the run size set from timings on D1 itself (3.5), and a deploy target with its jurisdiction check (3.3).
