# store

The store is a D1 database on Cloudflare. It holds the bundles of pairs the site is built from (`store/ingest/migrations/0011_pairs.sql`, openspec `pairs-site`).

| Path | What it is |
| --- | --- |
| `ingest/migrations/` | The database's migrations, applied in order. Migrations 0001 to 0010 made the claims store, which was removed with claims on 2026-11-20. They stay because a database that has applied them keeps that history; their tables are dropped at the cutover, on the operator's word, not before |
| `ingest/scripts/load-pairs.mjs` | Loads one bundle of the lab's page files into the pair tables, checked against its manifest first |
| `ingest/scripts/export-pairs.mjs` | Writes one bundle version back out of the pair tables as the folder it was loaded from: the site is built from that folder |
| `ingest/scripts/bundle-manifest.mjs` | Writes and checks a bundle's manifest: its files' counts and checksum |
| `ingest/scripts/d1.mjs`, `preview-config.mjs` | How the scripts reach the database with Wrangler: the local engine, or the preview database through the git-ignored `wrangler.preview.jsonc` |
| `ingest/tests/` | A bundle loaded and read back on D1's local engine (`make store-test`) |

No Worker is deployed from here. The ingest service that once stood in front of the store, its SQL (`schema.sql`, `merge.sql`, `preview.sql`, `ingest.sql`), its proof and its cut-over were removed with claims; their text stays in git history.
