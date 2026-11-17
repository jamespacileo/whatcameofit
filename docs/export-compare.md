# Comparing the two exports, and rehearsing an export from the store

Until the cut-over the site is built from the committed snapshot, which comes from the pipeline's Postgres database. The truth store (`store/`) has to give the same export first. `thenwhat export-compare` holds the two side by side; `make store-export-rehearsal` is what CI will do after the cut-over, run today without changing anything.

Both only read: the database in a read-only transaction that is rolled back, a store file opened read-only, the D1 database through `SELECT`s.

## The comparison

```bash
make export-compare
```

With nothing else, it makes a store file from the database through the pipeline's natural-key mapping and `store/merge.sql`, takes both exports at one moment and compares them. This shows the store *can* hold the records. About three minutes and 320 MB of scratch space for 2,000 claims. `ARGS="--every 5"` compares every fifth claim.

To compare with a store that exists:

| Against | How |
|---|---|
| A store file somebody built (`thenwhat store build`) | `make export-compare ARGS="--store store.db --payloads objects"` |
| The D1 database itself | `make export-compare ARGS="--d1 thenwhat-store-preview --payloads objects --r2-bucket thenwhat-payloads-preview --keep work"` |

`--d1` fetches the rows an export reads with `wrangler d1 execute --remote --json`, a page of a table at a time. `wrangler d1 export` is not used: D1 cannot export a database that has virtual tables, and the store has its search tables. Wrangler runs in `store/ingest` as whoever is signed in, or with `CLOUDFLARE_API_TOKEN`; `--wrangler-config` names a configuration when the database is not found by name. A payload kept as an object is taken from `--payloads` when it is there and from `--r2-bucket` otherwise, one request an object (thousands for the whole store, so point `--payloads` at the folder the store was built from when you have it). Every payload is checked against the checksum the store names, wherever it came from.

Each page of a table starts after the last row's key, aims at about 1 MB of answer and is halved when a read fails; one line a table says its rows and seconds. Of `payload` only the rows an evidence event names are fetched, of `source_record` only terms, organisations and papers, of `decision_log` only the three steps an export reads. Measured on 2026-11-17 against a D1 engine on this machine holding the hot tables of the real store (970 published claims): 216,781 rows in 359 queries, 8 minutes with the export, 230 seconds of it the 20,734 payload rows. The export it gave was the same, byte for byte, as the export read from the store file. Against Cloudflare each query also crosses the network.

A store file built in tiers keeps its hot payload objects in `payloads/hot`: give that folder to `--payloads`.

`--d1-local` reads the database Wrangler keeps on this machine (`make store-dev`) instead of Cloudflare's.

What an export reads of the store is 16 tables, listed with their columns as `COLUMNS_READ` in `pipeline/src/thenwhat/export/store_records.py`. That is the store's hot tier as far as the export goes: no registry trial, lead, share, ledger entry, usage or measure is read, and a trial's facts on a claim's page come from the raw payload of the claim's own evidence event. A store file or database with only those tables gives the same export; one missing a table or a column is refused by name.

The command exits with 1 when the exports differ and names each claim and the places in it. Where it can, it names the cause:

- **the data**: the database holds two source articles of one claim at one address key. The store holds one and gives it the statements of both. Fold the pair in the database.
- **the store's merge**: the intervention holds the same names in another order.

`--allow-named` exits with 0 when every difference has a named cause. For duplicate articles it checks the exact URLs, the article the store kept and the promises, statements and organisation links reassigned to it. A change to the retained article or the claim's status still fails the comparison. `--report file.json` writes the comparison, with `unexplained` as the count that needs a person.

Canonical form looks past only the time the export was made, the ids each store gives its own events, and the order of entries that tie.

## The rehearsal

```bash
STORE_D1=thenwhat-store-preview STORE_R2_BUCKET=thenwhat-payloads-preview make store-export-rehearsal
```

Fetches the store into `.store-rehearsal/`, writes `export.json` there with `thenwhat export --d1 … --store …`, then:

1. holds it to `site/export.schema.json` and fails on an export with no claim;
2. says how its claims compare with `site/data/published-export.json` (a count, not a failure: the store may have moved on);
3. stages it as a snapshot under `.store-rehearsal/`, which runs the checks a published snapshot must pass.

Nothing under `site/data/` is touched.

In CI the same target is the job `store-export` in `.github/workflows/ci.yml`. It runs only on `main` and only when the repository variable `EXPORT_FROM_STORE` is `true`. It needs the variables `STORE_D1` and `STORE_R2_BUCKET` and the secret `STORE_READ_API_TOKEN`, a Cloudflare token that can read that database and bucket and nothing else. The deploy job does not wait for it.

The export's settings (the score bands) come from the environment, as for any export. A rehearsal with other settings than the pipeline's gives another export.
