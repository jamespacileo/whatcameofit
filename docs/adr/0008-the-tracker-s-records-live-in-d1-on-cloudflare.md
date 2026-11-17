# 8. The tracker's records live in one D1 database on Cloudflare, with raw payloads in R2

Date: 2026-11-16. Status: accepted; not in effect until the migration of `openspec/changes/cloudflare-source-of-truth` has run. Change: `openspec/changes/cloudflare-source-of-truth`.

## Context

The tracker's records were in a Postgres database on one laptop. The site was a static build from a JSON export of it, committed to the repository. The Worker that answers a reader's lookup kept nothing. On 2026-11-16 the operator said this was not the intended shape: the database that powers the site is to be on the Cloudflare platform and be the source of truth, rows are to be created and updated on demand as readers use the extension and the landing page, and a database on a device is ephemeral, a place to process data that is then upserted.

Two stores were considered: D1, Cloudflare's own database with SQLite's semantics, and a Postgres hosted elsewhere and reached through Hyperdrive. Cloudflare offers no Postgres of its own. The assistant first recommended Postgres, because the schema, its migrations and its Postgres-only code already exist. The operator asked for D1 to be looked at again, for what staying inside one platform gives. Five criteria were set and tested the same day.

What the spike found (figures and method: `openspec/changes/cloudflare-source-of-truth/tasks.md`, section 2):

| Criterion | Found |
| --- | --- |
| The database, with raw payloads outside it, is under 3 GB | 504 MB, against D1's limit of 10 GB. Left out: the HTTP cache, the link steps' ledger entries and 2,328,716 link leads on unlisted outlets that were never scored, read, labelled or linked. Those are about 3 GB of the 3.9 GB Postgres database |
| No row over 2 MB | Largest row 344 KB. One raw payload is 2.2 MB, so payloads cannot be rows |
| The merge works on SQLite | 18 fixed statements, one parameter. 14 of 14 scenarios pass, and the same cases pass on D1 |
| Name matching and the queue of due work need no Postgres-only feature | The same 322 leads by Postgres's regular expression, the Python rule and a full-text index. A lease on due work is one statement |
| Python can read and write the store on Cloudflare | A Python Worker ran the merge as one batch, and a Python Workflow ran two steps, locally and on a deployed preview: cold start 1.66 seconds, 22,000 rows merged in 0.63 seconds |

Cost, read from the providers' pages that day: on the paid Workers plan the operator already has, D1 at this size adds nothing and R2 holds the payloads inside its included 10 GB. A hosted Postgres would add about 5 to 45 US dollars a month and a second vendor.

## Decision

- The tracker's records are held in one D1 database on the Cloudflare platform. It is the only authority for them. No database on a device is authoritative, and losing a device loses no record the store holds.
- A raw payload is kept in R2, once for each distinct payload, under its checksum. The record that uses it holds the checksum and the fetch time. "Store the raw API payload and fetch timestamp for every evidence event" is met by the two together.
- The store is reached only through the Worker's binding and, for a device, an ingest address with that device's own token. It is never served as a database.
- Every writer enters records through one merge by natural key (`openspec/changes/cloudflare-source-of-truth/specs/ingest-merge`).
- Hosted Postgres through Hyperdrive stays the fallback. It is taken if D1's limits are reached or the build finds something the spike did not; the merge and its tests are written to hold for either.

## What this supersedes

- `CLAUDE.md`, conventions: "Nothing public is served from the home network. The pipeline and database stay private." The first sentence stands. The database is no longer on the home network and no longer private in the sense of being on the operator's own machines; it is private in that only the Worker's binding and a device's token reach it.
- `CLAUDE.md`, layout: the site's "only input is the pipeline's JSON export at `site/data/export.json`". The site is still built from one export, taken from the store when it is built and no longer committed.
- `CLAUDE.md`, working rules: "The initial migration has been regenerated in place while nothing is deployed." Once the store holds records, a schema change is a new migration.

`CLAUDE.md` is revised when the change is applied, not by this record.

## What does not change

- Status is derived by deterministic rules from approved evidence events. No model decides a status.
- Items are approved by rule and removed by archiving (`0001`). A claim a read drafted waits for its audit (`0007`).
- No article text, no post text and nothing that identifies a reader is stored anywhere.
- The site is a static build. The publication gate decides what an export contains.
- Processing is written in Python.

## What this does not decide

- Whether a reader's lookup leaves records, what it may create, and when it is processed. Decided later the same day in `0009`.
- Where subscriber emails will live in Phase 2.
- How a device processes a dataset (`openspec/changes/file-based-backfill`).

## Consequences

- The schema is ported to SQLite: JSON columns become text read with JSON functions, array columns become child tables or JSON, the eight upserts and two queue queries are rewritten, and Alembic's Postgres migrations are replaced.
- A batch in D1 is a list of statements with nothing read between them. Rules that branch have to be written as conditions inside statements, as the merge is. Evidence that differs from a stored event is kept in its own table, because events are unique by claim and key.
- One query at a time: D1 is single-threaded. Writes are sent in batches, and a large run is split.
- The migration is about 1.3 million rows and was not tried at that size.
- The Python SDK needed a private name to send a batch of prepared statements. If that stays so, the merge is written in JavaScript in the Worker and Python keeps the processing.
- The store can be restored to any minute of the last 30 days, which the laptop database could not.
- The operator's data is on Cloudflare, under Cloudflare's terms, which are to be noted in `docs/sources.md` before the store is created. The operator chose the European Union jurisdiction for the database and the bucket later the same day; it is set at creation and cannot be changed afterwards.
- The laptop database is kept, read-only, for 30 days after the migration. A dump of it taken on 2026-11-16 is held on two machines.

## Amended on 2026-11-16: small payloads stay in the store

Decided by the operator the same day, after the schema was drafted against the real data (`openspec/changes/cloudflare-source-of-truth/design.md`, decisions 2 and 16).

- A raw payload of 16 KB or less is kept in the D1 database, in the `payload` table, once for each distinct payload, under its checksum. Only a larger payload is an R2 object. This replaces "A raw payload is kept in R2" in the Decision above; the rest of that line stands: the record that uses a payload holds its checksum and the fetch time.
- Why: the registry corpus grew to 467,064 trials, each with a listing record of 642 bytes on average and 12 KB at most. In R2 that is half a million tiny objects to upload before the first merge, and a trial's plain page would need a second service to show its record. In the store they are 292 MB of a database projected at 1.20 GB, against the limit of 10 GB.
- What does not change: the payloads that forced R2, the registry records with posted results of up to 2.4 MB, are still objects. A payload that does not match its checksum is still reported and never used.
