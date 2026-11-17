// Tries a dump (scripts/dump-for-import.mjs) before it is sent anywhere: loads its files
// into a scratch SQLite file that has migrations/ applied, the way D1 was seen to take
// them: a file at a time, each statement on its own, foreign keys checked at once and
// never deferred. Then counts each table against the manifest. Nothing leaves this machine.
//
//   node scripts/check-dump.mjs <folder> [--scratch <file.sqlite>] [--keep-pragmas]
//
// Exit 1 on the first statement that fails, naming the file and its tables, or on a count
// that differs. `--keep-pragmas` runs a file's own PRAGMA lines, which are otherwise
// left out so that an order that only works with checks deferred fails here.
import { createReadStream, mkdtempSync, readFileSync, readdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { createInterface } from "node:readline";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";

const here = (path) => fileURLToPath(new URL(path, import.meta.url));
const folder = process.argv[2];
if (!folder || folder.startsWith("--")) { console.error("usage: check-dump.mjs <folder> [--scratch <file.sqlite>] [--keep-pragmas]"); process.exit(2); }
const given = process.argv.includes("--scratch") ? process.argv[process.argv.indexOf("--scratch") + 1] : null;
const keep = process.argv.includes("--keep-pragmas");
const dir = given ? null : mkdtempSync(join(tmpdir(), "thenwhat-check-"));
const path = given || join(dir, "scratch.sqlite");
rmSync(path, { force: true });
const db = new DatabaseSync(path);
for (const file of readdirSync(here("../migrations")).sort()) db.exec(readFileSync(here(`../migrations/${file}`), "utf8"));
db.exec("PRAGMA foreign_keys = ON; PRAGMA synchronous = OFF; PRAGMA journal_mode = MEMORY");

const manifest = JSON.parse(readFileSync(join(folder, "manifest.json"), "utf8"));
const files = readdirSync(folder).filter((name) => name.endsWith(".sql")).sort();
let failed = false;
const began = Date.now();
for (const name of files) {
  const started = Date.now(), tables = new Set();
  let statement = "", statements = 0;
  const run = () => {
    if (!statement.trim()) return;
    const table = /^(?:INSERT INTO|UPDATE) "?([A-Za-z0-9_]+)"?/.exec(statement)?.[1];
    if (table) tables.add(table);
    if (keep || !statement.startsWith("PRAGMA")) { db.exec(statement); statements += 1; }
    statement = "";
  };
  try {
    // A statement ends at `;` before a line that begins the next one.
    for await (const line of createInterface({ input: createReadStream(join(folder, name)), crlfDelay: Infinity })) {
      if (statement.endsWith(";") && /^(INSERT INTO|UPDATE|PRAGMA) /.test(line)) run();
      statement += (statement ? "\n" : "") + line;
    }
    run();
    console.log(`${name}  ${statements} statements  ${((Date.now() - started) / 1000).toFixed(1)} s`);
  } catch (error) {
    const table = /^(?:INSERT INTO|UPDATE) "?([A-Za-z0-9_]+)"?/.exec(statement)?.[1];
    console.error(`FAILED ${name} at statement ${statements + 1}, on ${table || "?"}: ${error.message}\nits tables so far: ${[...tables, table].filter(Boolean).join(", ")}`);
    failed = true;
    break;
  }
}
if (!failed) {
  const differ = Object.entries(manifest.tables).filter(([table, rows]) => Number(db.prepare(`SELECT count(*) AS n FROM "${table}"`).get().n) !== rows);
  for (const [table, rows] of differ) console.error(`COUNT DIFFERS ${table}: the manifest says ${rows}`);
  const broken = db.prepare("PRAGMA foreign_key_check").all().length;
  console.log(differ.length || broken ? `${differ.length} table(s) differ, ${broken} foreign key(s) broken` : `all ${Object.keys(manifest.tables).length} tables hold what the manifest says (${manifest.rows} rows), no foreign key broken, in ${((Date.now() - began) / 1000).toFixed(1)} s`);
  failed = Boolean(differ.length || broken);
}
db.close();
if (dir) rmSync(dir, { recursive: true, force: true });
process.exit(failed ? 1 : 0);
