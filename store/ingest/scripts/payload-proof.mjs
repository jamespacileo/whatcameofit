// Proves that every payload object the store's files refer to is in the bucket under its
// key, with its bytes: what the cut-over's payloads stage holds a build to.
//
// The referenced objects are the `payload` rows of the hot and the bulk file whose body
// is an R2 object (`r2_key` set; store/schema.sql): each distinct (sha256, r2_key, bytes)
// of either file is proved once. For each:
//   * its key must be `payload/<sha256>`, its checksum 64 hex and its size above nothing;
//   * a copy in the build's payload folders, when there is one, must be those bytes;
//   * the bucket must hold it, read back, with that size and SHA-256.
// A folder that is missing (or an object a folder lacks) is allowed only because of the
// last: the bucket's bytes are proved. Nothing is held in memory but a page of rows and
// the first failures; the rows are made distinct by SQLite in a temporary file, and each
// object read back is one file at a time a worker, removed when it is hashed.
import { existsSync, mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { sha256 } from "./r2.mjs";

const HEX = /^[0-9a-f]{64}$/;
const SHOWN = 20;

// Where a folder keeps its objects: `<folder>/payload/<sha256>` or `<folder>/<sha256>`,
// as upload-payloads.mjs reads them.
const objectsOf = (folder) => (existsSync(join(folder, "payload")) ? join(folder, "payload") : folder);

// Each distinct external payload of the files, in checksum order, with the tiers that
// refer to it. Require both inventories before certifying their objects.
export function* referenced(files) {
  const db = new DatabaseSync(":memory:");
  try {
    db.exec("PRAGMA temp_store = FILE; PRAGMA cache_size = -16384");
    const parts = [];
    for (const [n, { tier, path }] of files.entries()) {
      if (!/^[a-z]+$/.test(tier)) throw new Error(`a tier is a word: ${tier}`);
      if (!existsSync(path)) throw new Error(`the ${tier} file is not at ${path}`);
      const schema = `f${n}`;
      db.prepare(`ATTACH DATABASE ? AS ${schema}`).run(`file:${encodeURI(resolve(path)).replace(/[?#]/g, encodeURIComponent)}?mode=ro`);
      const has = db.prepare(`SELECT count(*) AS n FROM ${schema}.sqlite_master WHERE type = 'table' AND name = 'payload'`).get().n;
      if (!has) throw new Error(`the ${tier} file has no payload table; its inventory cannot be verified`);
      parts.push(`SELECT sha256, r2_key, bytes, '${tier}' AS tier FROM ${schema}.payload WHERE r2_key IS NOT NULL`);
    }
    if (!parts.length) return;
    const rows = db.prepare(`SELECT sha256, r2_key, bytes, group_concat(DISTINCT tier) AS tiers FROM (${parts.join(" UNION ALL ")}) GROUP BY sha256, r2_key, bytes ORDER BY sha256, r2_key, bytes`);
    for (const row of rows.iterate()) yield row;
  } finally { db.close(); }
}

// `files` [{tier, path}], `folders` the build's payload folders that exist, `store` an
// object with `get(key, path)` (true, false when absent, or a throw) and `label`.
export async function provePayloads({ files, folders = [], store, jobs = 4, log = console.log }) {
  const from = folders.map(objectsOf);
  const found = { referenced: 0, local: 0, bucketOnly: 0, proved: 0, failed: 0 };
  const failures = [];
  const fail = (sha, why) => { found.failed += 1; if (failures.length < SHOWN) failures.push(`${String(sha).slice(0, 12)}…: ${why}`); };
  const scratch = mkdtempSync(join(tmpdir(), "thenwhat-proof-"));
  const rows = referenced(files);
  let last = null;
  // The next row, taken by one worker at a time (the iterator is synchronous).
  const take = () => {
    const next = rows.next();
    if (next.done) return null;
    const row = next.value;
    found.referenced += row.sha256 === last ? 0 : 1;
    if (row.sha256 === last) fail(row.sha256, "the files disagree on this payload's key or size");
    last = row.sha256;
    return row;
  };
  async function prove(row, n) {
    const { sha256: sum, r2_key: key, bytes, tiers } = row;
    if (typeof sum !== "string" || !HEX.test(sum)) return fail(sum, `(${tiers}) its checksum is not 64 hex`);
    if (key !== `payload/${sum}`) return fail(sum, `(${tiers}) its key is ${JSON.stringify(key)}, not payload/<its sha256>`);
    if (!(Number.isInteger(bytes) && bytes > 0)) return fail(sum, `(${tiers}) its size is ${bytes}`);
    let local = false;
    for (const folder of from) {
      const path = join(folder, sum);
      if (!existsSync(path)) continue;
      local = true;
      if (statSync(path).size !== bytes || (await sha256(path)) !== sum) return fail(sum, `(${tiers}) the copy in ${folder} is not its checksum's bytes`);
    }
    found[local ? "local" : "bucketOnly"] += 1;
    const back = join(scratch, `${n}`);
    try {
      let there;
      try { there = await store.get(key, back); } catch (error) { return fail(sum, `(${tiers}) could not be read from the bucket: ${error.message}`); }
      if (!there) return fail(sum, `(${tiers}) MISSING from the bucket${local ? "" : ", and not in the build's payload folders"}`);
      if (statSync(back).size !== bytes || (await sha256(back)) !== sum) return fail(sum, `(${tiers}) the bucket's object DIFFERS: not its checksum's bytes`);
      found.proved += 1;
    } finally { rmSync(back, { force: true }); }
  }
  try {
    await Promise.all(Array.from({ length: Math.min(Math.max(jobs, 1), 32) }, async (_, n) => {
      for (let row = take(); row; row = take()) await prove(row, n);
    }));
  } finally { rows.return(); rmSync(scratch, { recursive: true, force: true }); }
  log(`${found.referenced} payload object(s) referenced by the ${files.map((one) => one.tier).join(" and ")} file(s): ${found.proved} proved in ${store.label} by key and SHA-256 (${found.local} with a copy in the build's folders, ${found.bucketOnly} only in the bucket), ${found.failed} failed`);
  return { ...found, failures, ok: found.failed === 0 };
}
