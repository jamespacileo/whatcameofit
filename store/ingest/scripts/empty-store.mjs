// Deletes every row of the store's tables and leaves the schema and the record of applied
// migrations: for clearing trial rows before a real load. It cannot be undone except by
// D1's Time Travel, so note the bookmark first (`wrangler d1 time-travel info`).
//
//   node scripts/empty-store.mjs --empty thenwhat-store-preview [--persist-to <folder>]   the local engine
//   node scripts/empty-store.mjs --empty thenwhat-store-preview --remote                  the preview database
//
// The database must be named, and only a preview database is taken: this script never
// empties production. Children are emptied before parents; the search tables are emptied
// by the schema's triggers.
import { mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { execute, sum, target } from "./d1.mjs";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const name = process.argv.includes("--empty") ? process.argv[process.argv.indexOf("--empty") + 1] : null;
const bound = /"database_name":\s*"([^"]+)"/.exec(readFileSync(here("../wrangler.jsonc"), "utf8"))?.[1];
if (!name || name !== bound || !name.endsWith("-preview")) {
  console.error(`name the database to empty: --empty ${bound}. Only the preview database this service is bound to is taken.`);
  process.exit(2);
}
const to = target(process.argv);
// The tables, as the migrations create them, last first.
const created = readdirSync(here("../migrations")).sort().flatMap((file) =>
  [...readFileSync(here(`../migrations/${file}`), "utf8").matchAll(/^CREATE TABLE (?:IF NOT EXISTS )?"?(\w+)"?/gm)].map(([, table]) => table));
const dir = mkdtempSync(join(tmpdir(), "thenwhat-empty-"));
const file = join(dir, "empty.sql");
writeFileSync(file, ["PRAGMA defer_foreign_keys = true;", ...created.reverse().map((table) => `DELETE FROM "${table}";`)].join("\n") + "\n");
try {
  const started = Date.now();
  const answer = await execute(to, "--file", file);
  console.log(`emptied ${created.length} tables of ${name} (${to.remote ? "preview database" : "local engine"}) in ${((Date.now() - started) / 1000).toFixed(1)} s, rows_written ${sum(answer, "rows_written") ?? "not said"}`);
  const [{ results: [left] }] = await execute(to, "--command", `SELECT ${created.map((table) => `(SELECT count(*) FROM "${table}")`).join(" + ")} AS rows`);
  console.log(`rows left: ${left.rows}`);
  process.exit(left.rows ? 1 : 0);
} catch (error) { console.error(`FAILED\n${error.message}`); process.exit(1); } finally { rmSync(dir, { recursive: true, force: true }); }
