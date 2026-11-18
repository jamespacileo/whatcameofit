# Proposal

## Why

The project's records live in one private Postgres database. The public site is a static build from a JSON export of it, committed to the repository (`docs/deploy.md`). The Worker that answers a reader's lookup computes its answer and keeps nothing (`openspec/changes/archive/2026-11-18-live-lookup`).

On 2026-11-16 the operator said this is not the intended shape:

- The database that powers the site is meant to be on the Cloudflare platform and to be the source of truth.
- Rows are meant to be created and updated on demand, many of them because a reader used the Safari or Chrome extension or entered an address on the landing page.
- Databases on the operator's devices are meant to be ephemeral: places to process data that is then upserted into the one on Cloudflare.

Three things follow from the present shape that the operator does not want. A lookup's work is thrown away, so the tracker learns nothing from what readers ask about. Only the machine that holds the private database can add to the tracker. And the database turned out to be on one laptop: the Compose database on the Mac mini holds one claim and no link leads, and the real one, with 829 claims and 2,686,680 link leads, was found on the MacBook Pro on 2026-11-16 only by asking a session there to count. Of those leads, 2,328,716 are on unlisted outlets and have never been scored, read, labelled or linked.

## What Changes

- **A truth store on Cloudflare.** One database on the Cloudflare platform holds claims, source articles, evidence events, registry trials, papers, entities, decisions, usage and link leads. **BREAKING**: the private Postgres database stops being the source of truth.
- **The store is D1, with raw payloads in R2.** Decided by the operator on 2026-11-16 after a spike met five stated criteria (`docs/adr/0008`). A hosted Postgres reached through Hyperdrive is the fallback.
- **One merge path for every writer.** A reader's lookup, a backfill pushed from a device and a scheduled refresh all hand records to the same merge, which matches by natural key, is safe to repeat, and applies the same conflict rules.
- **Lookups leave records.** **BREAKING** for `live-lookup`: a lookup of an article the tracker does not hold stores the article's address, outlet, title and date and the registry records found, as records awaiting the rules. It still stores no text and nothing about who asked.
- **A claim a reader's lookup starts is published by rule, without the audit hold.** Decided by the operator on 2026-11-16 (`docs/adr/0009`). It is approved only by the rules that approve any claim (`docs/adr/0001`) and is marked as not checked by a person. The audit hold of `docs/adr/0007` stays for backfill batches. Processing is queued and finishes within minutes; the reader's answer never waits on it.
- **The store is in the European Union jurisdiction**, set when it is created.
- **The site is still a static build**, from an export taken from the truth store when it is built, not from a file committed by hand. **BREAKING** for `deployment`.
- **Every write says where it came from**: which run, which device or which kind of reader request, which code.
- **Processing stays in Python.** Whether any of it runs on Cloudflare is a question for the spike.

Not in this change:

- How a device processes a dataset. That is `file-based-backfill`, which pushes to this change's merge path.
- Rendering pages from the database on each request. Pages stay built.
- Subscriber emails. None is collected before Phase 2 and none goes in this store under this change.
- Porting status rules to JavaScript. Status is derived where the Python rules run.

## Capabilities

### New Capabilities

- `truth-store`: the one store on Cloudflare, what it holds, where raw payloads are kept, how it is backed up and restored, and that no other database is authoritative.
- `ingest-merge`: how any writer's records are accepted: registration of a run, natural keys, idempotence, refusals, conflict rules, reconciliation.
- `on-demand-records`: what a reader's lookup may create and update, what it never stores, and what must be true before any of it is public.

### Modified Capabilities

- `deployment`: the build takes its export from the truth store; the committed snapshot is no longer what is deployed.
- `live-lookup`: a lookup keeps structured public records of the article and the trials found, and still keeps no text and nothing of the reader. This capability is specified in `openspec/changes/archive/2026-11-18-live-lookup`, not yet synced; the delta is written against that text.

`site-publishing` is not modified: the publication gate and the build from the export alone stand as written.

## Impact

- **Decisions to record (ADRs):** supersede "the pipeline and database stay private" and "nothing public is served from the home network" as they apply to the database; amend `0001` and `0007` for records a lookup makes; amend `0005` because the page reader at home is now on a path that writes.
- **Guardrails restated:** no article text and no post text in the store; nothing that says who asked; raw payload and fetch time for every evidence event; no model decides a status.
- **Code:** `site/worker/` gains a store binding and the merge call; `pipeline/src/thenwhat/db/` and `export/` change to match the chosen store; `site/scripts/deploy.mjs` and the CI workflow take the export from the store.
- **Data:** the present Postgres database (`thenwhat` on the MacBook Pro, 3,912 MB) is migrated once, without its HTTP cache, the link steps' ledger entries and the leads on unlisted outlets, which together are about 3 GB of it.
- **Cost:** on the paid Workers plan the operator already has, D1 adds about nothing at the present size; a hosted Postgres adds roughly 5 to 45 US dollars a month. Read from the providers' pages on 2026-11-16; to be noted in `docs/sources.md` before use.
- **Other changes:** `portable-backfill-promotion` is withdrawn in favour of this change and `file-based-backfill`.
