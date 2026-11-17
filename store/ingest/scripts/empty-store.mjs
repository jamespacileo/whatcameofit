// Deletes every row of the store's tables and leaves the schema and the record of applied
// migrations: for clearing trial rows before a real load. It cannot be undone except by
// D1's Time Travel, so note the bookmark first (`wrangler d1 time-travel info`).
//
//   node scripts/empty-store.mjs --empty thenwhat-store-preview --persist-to <folder>     the local engine
//   node scripts/empty-store.mjs --empty thenwhat-store-preview --remote                  the preview database
//
// The database must be named, and only a preview database is taken: this script never
// empties production.
//
// It is for a small store. On 17 November 2026 one file of DELETEs against the fully
// loaded preview (2.7 million rows, 2.3 GB) failed after 60 s with "Upstream service
// unavailable [code: 7009]". So rows now go in batches (`--batch N`, 20,000 by default),
// one request each; and a store of more than 200,000 rows is refused, because emptying
// it row by row is slow and every deleted row is a billed write: replace the database
// instead (docs/deploy.md, "Resetting the preview store"). `--anyway` empties it all the
// same. Tables a database behind on its migrations does not have are passed over.
// Children are emptied before parents; the search tables are emptied by the schema's
// triggers.
import { readFileSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { execute, sum, target } from "./d1.mjs";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const argv = process.argv.slice(2);
const value = (flag) => (argv.includes(flag) ? argv[argv.indexOf(flag) + 1] : null);
const name = value("--empty");
// The database is the one the configuration in use names, not the one this file's
// neighbour names: `--config` may point anywhere. It must be a preview database, and the
// one named on the command line.
let to;
try { to = target(process.argv, { previewOnly: true }); } catch (error) { console.error(error.message); process.exit(2); }
if (!name || name !== to.database) {
  console.error(`name the database to empty: --empty ${to.database}. Only the preview database of the configuration in use is taken.`);
  process.exit(2);
}
const LARGE = 200_000;
const batch = Math.min(Math.max(Number(value("--batch")) || 20_000, 1), 100_000);
const quote = (table) => `"${table}"`;
const first = async (sql) => (await execute(to, "--command", sql))[0].results;

try {
  // The tables the migrations create, last first, and of those the ones this database has.
  const created = readdirSync(here("../migrations")).sort().flatMap((file) =>
    [...readFileSync(here(`../migrations/${file}`), "utf8").matchAll(/^CREATE TABLE (?:IF NOT EXISTS )?"?(\w+)"?/gm)].map(([, table]) => table))
    // A table a later migration makes again keeps the place it first had, among its
    // parents and children: the first time it was made is where it belongs.
    .filter((table, at, all) => all.indexOf(table) === at).reverse();
  const there = new Set((await first("SELECT name FROM sqlite_master WHERE type = 'table'")).map((row) => row.name));
  const tables = created.filter((table) => there.has(table));
  const absent = created.filter((table) => !there.has(table));
  if (absent.length) console.log(`not in this database, passed over: ${absent.join(", ")}`);
  if (!tables.length) { console.log("the database has none of the store's tables: nothing to empty"); process.exit(0); }

  const [counts] = await first(`SELECT ${tables.map((table) => `(SELECT count(*) FROM ${quote(table)}) AS ${quote(table)}`).join(", ")}`);
  const total = tables.reduce((n, table) => n + counts[table], 0);
  if (total > LARGE && !argv.includes("--anyway")) {
    console.error(`${name} holds ${total} rows, over ${LARGE}: emptying it row by row is slow, and each deleted row is a billed write.`);
    console.error("Replace the database instead (docs/deploy.md, \"Resetting the preview store\"), or pass --anyway.");
    process.exit(1);
  }

  const started = Date.now();
  let written = 0, requests = 0;
  for (const table of tables) {
    if (!counts[table]) continue;
    // A row that points at another of its own table would hold that one back: untie first.
    const own = (await first(`PRAGMA foreign_key_list(${quote(table)})`)).filter((key) => key.table === table).map((key) => key.from);
    for (const column of new Set(own)) { await execute(to, "--command", `UPDATE ${quote(table)} SET ${quote(column)} = NULL WHERE ${quote(column)} IS NOT NULL`); requests += 1; }
    // A batch is found by the table's primary key, or by rowid where it has none.
    const keys = (await first(`PRAGMA table_info(${quote(table)})`)).filter((column) => column.pk > 0).map((column) => quote(column.name));
    const by = keys.length ? `(${keys.join(", ")})` : "rowid";
    const sql = `DELETE FROM ${quote(table)} WHERE ${by} IN (SELECT ${keys.length ? keys.join(", ") : "rowid"} FROM ${quote(table)} LIMIT ${batch})`;
    for (let left = counts[table]; left > 0; left -= batch) {
      const answer = await execute(to, "--command", sql);
      written += sum(answer, "rows_written") || 0; requests += 1;
    }
  }
  const [after] = await first(`SELECT ${tables.map((table) => `(SELECT count(*) FROM ${quote(table)})`).join(" + ")} AS rows`);
  console.log(`emptied ${tables.length} tables of ${name} (${to.remote ? "preview database" : "local engine"}): ${total} rows in ${requests} requests, ${((Date.now() - started) / 1000).toFixed(1)} s, rows_written ${written || "not said"}`);
  console.log(`rows left: ${after.rows}`);
  process.exit(after.rows ? 1 : 0);
} catch (error) {
  console.error(`FAILED\n${error.message}`);
  process.exit(1);
}
