// Writes one bundle version back out of the store's pair tables as the folder it was loaded
// from (openspec pairs-site, task 2.1c): `p12_<page>/<key>.json` and `schemas/<Model>.json`.
// The site is built from that folder, so the build reads exactly the version D1 holds.
//
//   node scripts/export-pairs.mjs <out folder>                      the current version, this machine's local engine
//   node scripts/export-pairs.mjs <out folder> --remote             the preview database's current version
//   node scripts/export-pairs.mjs <out folder> --version <version> [--remote]
//
// The folder must not exist. It is written whole, its version worked out again from what was
// written, and removed if that is not the version asked for. Nothing is ever written to D1.
import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import { SCHEMA_MODEL, bundleVersion } from "./load-pairs.mjs";

const PREFIX = "p12_";
// Rows read at a time: each part is at most 10,000 characters (load-pairs.mjs).
const PAGE_ROWS = 200;
const quote = (value) => `'${String(value).replaceAll("'", "''")}'`;

/** A page model's folder: `PairPage` is `p12_pair_page`; a schema's is `schemas`. */
export function folderOf(model) {
  if (model === SCHEMA_MODEL) return "schemas";
  return PREFIX + model.replace(/[A-Z]/g, (letter, at) => `${at ? "_" : ""}${letter.toLowerCase()}`);
}

/**
 * Write a version's files into a new folder.
 * @param {(sql: string) => Promise<object[]>} read rows of one SELECT
 * @param {string} out a folder that does not exist yet
 * @param {string | null} version the version to write, or null for the current one
 * @returns the version written and how many files of each folder
 */
export async function exportBundle(read, out, version = null) {
  if (existsSync(out)) throw new Error(`${out} exists: give a folder that does not, so nothing is mixed into it`);
  const wanted = version ?? (await read("SELECT version FROM pair_bundle WHERE current = 1"))[0]?.version;
  if (!wanted) throw new Error("the store holds no current bundle");
  if (!(await read(`SELECT 1 AS held FROM pair_bundle WHERE version = ${quote(wanted)}`)).length) {
    throw new Error(`the store holds no bundle ${wanted}`);
  }
  const counts = {};
  let file = null;
  const flush = () => {
    if (!file) return;
    const folder = join(out, folderOf(file.model));
    mkdirSync(folder, { recursive: true });
    writeFileSync(join(folder, `${file.key}.json`), `${JSON.stringify(JSON.parse(file.body), null, 1)}\n`);
    counts[folderOf(file.model)] = (counts[folderOf(file.model)] ?? 0) + 1;
    file = null;
  };
  mkdirSync(out, { recursive: true });
  try {
    let after = null;
    for (;;) {
      const from = after ? `AND (model, key, part) > (${quote(after.model)}, ${quote(after.key)}, ${after.part})` : "";
      const rows = await read(
        `SELECT model, key, part, body FROM pair_page WHERE version = ${quote(wanted)} ${from} ORDER BY model, key, part LIMIT ${PAGE_ROWS}`,
      );
      for (const row of rows) {
        if (file && (file.model !== row.model || file.key !== row.key)) flush();
        if (!file) {
          if (row.part !== 0) throw new Error(`${row.model} ${row.key} starts at part ${row.part}: the version is not whole`);
          file = { model: row.model, key: row.key, body: "", next: 0 };
        }
        if (row.part !== file.next) throw new Error(`${row.model} ${row.key} misses part ${file.next}: the version is not whole`);
        file.body += row.body;
        file.next += 1;
      }
      if (rows.length < PAGE_ROWS) break;
      after = rows.at(-1);
    }
    flush();
    const written = bundleVersion(out);
    if (written !== wanted) throw new Error(`the folder written has version ${written}, not ${wanted}: it is removed`);
    return { version: wanted, counts };
  } catch (error) {
    rmSync(out, { recursive: true, force: true });
    throw error;
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const [out, ...argv] = process.argv.slice(2);
  if (!out || out.startsWith("--")) {
    console.error("usage: node scripts/export-pairs.mjs <out folder> [--version <version>] [--remote [--config <file>] [--production <database name>]]");
    process.exit(1);
  }
  try {
    const { execute, target } = await import("./d1.mjs");
    const to = target(argv);
    const version = argv.includes("--version") ? argv[argv.indexOf("--version") + 1] : null;
    const read = async (sql) => (await execute(to, "--command", sql))[0]?.results ?? [];
    const done = await exportBundle(read, out, version);
    console.log(`bundle ${done.version} written to ${out}: ${Object.entries(done.counts).map(([folder, n]) => `${n} in ${folder}`).join(", ")}`);
  } catch (error) {
    console.error(String(error.message || error));
    process.exit(1);
  }
}
