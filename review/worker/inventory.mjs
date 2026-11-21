// The model inventory: for each catalogued model, whether an environment's store holds it and
// how many records, and the records themselves a page at a time. Every statement is built here
// from the catalogue's fixed table names, never from a request, and goes through `read`.
import { MODELS, TABLES, modelById, notAModel, PAGE_MODELS } from "./catalogue.mjs";
import { allow, read } from "./reads.mjs";

export const PAGE_ROWS = 50;

// Tables whose hidden columns are large: they are left out by the statement itself, rather
// than read and dropped, and their size is shown instead.
const NARROW = {
  pair_page: "SELECT version, model, key, part, length(body) AS body_chars FROM pair_page",
  payload: "SELECT sha256, bytes, r2_key, added_run, length(body) AS body_chars FROM payload",
};

const S = {
  tables: allow("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name"),
  columns: allow("SELECT name, pk FROM pragma_table_info(?) ORDER BY cid"),
  current: allow("SELECT version, loaded_at FROM pair_bundle WHERE current = 1"),
  held: allow("SELECT version, loaded_at, current FROM pair_bundle WHERE version = ?"),
  pageCounts: allow("SELECT model, COUNT(*) AS n FROM pair_page WHERE version = ? AND part = 0 GROUP BY model"),
  pageCount: allow("SELECT COUNT(*) AS n FROM pair_page WHERE version = ? AND model = ? AND part = 0"),
  pageKeys: allow("SELECT key FROM pair_page WHERE version = ? AND model = ? AND part = 0 ORDER BY key LIMIT ? OFFSET ?"),
  pageParts: allow("SELECT body FROM pair_page WHERE version = ? AND model = ? AND key = ? ORDER BY part"),
  count: {},
  countIn: {},
  rows: {},
  rowsIn: {},
  record: {},
};

for (const { table, versioned, key } of TABLES) {
  const select = NARROW[table] ?? `SELECT * FROM ${table}`;
  // Paged in primary-key order, so an offset names the same records from one page to the next.
  const order = `ORDER BY ${key.join(", ")}`;
  S.count[table] = allow(`SELECT COUNT(*) AS n FROM ${table}`);
  S.rows[table] = allow(`${select} ${order} LIMIT ? OFFSET ?`);
  S.record[table] = allow(`${select} WHERE ${key.map((column) => `${column} = ?`).join(" AND ")}`);
  if (versioned) {
    S.countIn[table] = allow(`SELECT COUNT(*) AS n FROM ${table} WHERE version = ?`);
    S.rowsIn[table] = allow(`${select} WHERE version = ? ${order} LIMIT ? OFFSET ?`);
  }
}

export async function present(db) {
  return new Set((await read(db, S.tables)).map((row) => row.name));
}

async function currentBundle(db, tables) {
  if (!tables.has("pair_bundle")) return null;
  return (await read(db, S.current))[0] ?? null;
}

/** Every catalogued model with its state in one environment's store, plus any table the store
 * holds that the catalogue does not list (shown so, never dropped). */
export async function inventory(db) {
  const tables = await present(db);
  const bundle = await currentBundle(db, tables);
  const pages = bundle && tables.has("pair_page")
    ? new Map((await read(db, S.pageCounts, bundle.version)).map((row) => [row.model, row.n]))
    : new Map();
  const states = {};
  for (const model of MODELS) {
    if (model.kind === "table") {
      if (!tables.has(model.table)) {
        states[model.id] = { status: "absent", reason: `no ${model.table} table: ${model.migration} not applied` };
        continue;
      }
      const rows = (await read(db, S.count[model.table]))[0].n;
      const inCurrent = model.versioned && bundle ? (await read(db, S.countIn[model.table], bundle.version))[0].n : null;
      states[model.id] = { status: "present", rows, inCurrent, version: model.versioned ? bundle?.version ?? null : null };
    } else {
      const records = pages.get(model.model) ?? 0;
      const schema = pages.has("$schema") ? await hasSchema(db, bundle.version, model.model) : false;
      states[model.id] = records || schema
        ? { status: "present", rows: records, version: bundle.version, schema }
        : { status: "absent", reason: bundle ? `bundle ${bundle.version} has no ${model.model} files` : "no current bundle" };
    }
  }
  const listed = new Set(TABLES.map((t) => t.table));
  const unlisted = [...tables].filter((name) => !notAModel(name) && !listed.has(name));
  // A page model the bundle holds that the catalogue does not name is shown, as a table is: a new
  // model from the lab must not go unseen until someone adds it here.
  const catalogued = new Set(PAGE_MODELS.map((m) => m.model));
  const schemas = bundle && pages.has("$schema") ? (await read(db, S.pageKeys, bundle.version, "$schema", 1000, 0)).map((row) => row.key) : [];
  const unlistedPages = [...new Set([...pages.keys(), ...schemas])]
    .filter((name) => !name.startsWith("$") && !catalogued.has(name)).sort();
  return { bundle, states, unlisted, unlistedPages };
}

async function hasSchema(db, version, model) {
  return (await read(db, S.pageParts, version, "$schema", model)).length > 0;
}

export function joined(parts) {
  return JSON.parse(parts.map((row) => row.body).join(""));
}

/**
 * The bundle a read is bound to: the version asked for, when the store still holds it, or the
 * current one when none is asked for. A list and the records opened from it name the same
 * version, so a bundle made current in between never changes what they show (the operator's
 * QA, 2026-11-21). `{ gone }` when the version asked for is no longer held.
 */
export async function bundleFor(db, tables, version) {
  if (!tables.has("pair_bundle")) return version ? { gone: version } : null;
  if (!version) return (await read(db, S.current))[0] ?? null;
  return (await read(db, S.held, version))[0] ?? { gone: version };
}

export const VERSION = /^[a-f0-9]{16}$/;

/** One page of a model's records in one environment, with its columns as the store has them.
 * Versioned tables and page models are read from the bundle `version` names. */
export async function rowsOf(db, id, { offset = 0, version = null } = {}) {
  const model = modelById.get(id);
  if (!model) return null;
  if (version !== null && !VERSION.test(version)) return { bad: "version" };
  const tables = await present(db);
  const empty = { columns: [], rows: [], total: 0, offset, limit: PAGE_ROWS };
  if (model.kind === "page-model") {
    const bundle = await bundleFor(db, tables, version);
    if (bundle?.gone) return bundle;
    if (!bundle) return empty;
    const keys = await read(db, S.pageKeys, bundle.version, model.model, PAGE_ROWS, offset);
    const total = (await read(db, S.pageCount, bundle.version, model.model))[0].n;
    return { columns: [{ name: "key", key: true }], key: ["key"], rows: keys, total, offset, limit: PAGE_ROWS, version: bundle.version };
  }
  if (!tables.has(model.table)) return { ...empty, absent: true };
  const columns = await columnsOf(db, model);
  let rows;
  let total;
  let bound = null;
  if (model.versioned) {
    const bundle = await bundleFor(db, tables, version);
    if (bundle?.gone) return bundle;
    bound = bundle?.version ?? null;
    rows = bound ? await read(db, S.rowsIn[model.table], bound, PAGE_ROWS, offset) : [];
    total = bound ? (await read(db, S.countIn[model.table], bound))[0].n : 0;
  } else {
    rows = await read(db, S.rows[model.table], PAGE_ROWS, offset);
    total = (await read(db, S.count[model.table]))[0].n;
  }
  return { columns, key: model.key, hiddenColumns: model.hidden ?? [], rows: rows.map((row) => shown(model, row)), total, offset, limit: PAGE_ROWS, version: bound };
}

async function columnsOf(db, model) {
  const hidden = new Set(model.hidden ?? []);
  const columns = (await read(db, S.columns, model.table))
    .filter((c) => !hidden.has(c.name))
    .map((c) => ({ name: c.name, key: c.pk > 0 }));
  if (NARROW[model.table]) columns.push({ name: "body_chars", key: false });
  return columns;
}

function shown(model, row) {
  for (const name of model.hidden ?? []) delete row[name];
  return row;
}

/** One table record, addressed by its primary key's values in key order. For a versioned
 * table the key begins with the version, which must still be held. */
export async function tableRecord(db, id, key) {
  const model = modelById.get(id);
  if (!model || model.kind !== "table") return null;
  if (!Array.isArray(key) || key.length !== model.key.length || !key.every((v) => ["string", "number"].includes(typeof v))) return { bad: "key" };
  const tables = await present(db);
  if (!tables.has(model.table)) return null;
  if (model.versioned) {
    const bundle = await bundleFor(db, tables, String(key[0]));
    if (bundle?.gone) return bundle;
  }
  const [row] = await read(db, S.record[model.table], ...key);
  if (!row) return null;
  return { table: model.table, key: model.key, values: key, version: model.versioned ? key[0] : null, columns: await columnsOf(db, model), row: shown(model, row) };
}

/** One page model's record from the bundle `version` names: its page file, the schema it was
 * checked against, and the bundle's provenance from its manifest. */
export async function pageRecord(db, id, key, version = null) {
  const model = modelById.get(id);
  if (!model || model.kind !== "page-model") return null;
  if (version !== null && !VERSION.test(version)) return { bad: "version" };
  const tables = await present(db);
  const bundle = await bundleFor(db, tables, version);
  if (bundle?.gone) return bundle;
  if (!bundle) return null;
  const parts = await read(db, S.pageParts, bundle.version, model.model, key);
  if (!parts.length) return null;
  const schemaParts = await read(db, S.pageParts, bundle.version, "$schema", model.model);
  const manifestParts = await read(db, S.pageParts, bundle.version, "$manifest", "manifest");
  const manifest = manifestParts.length ? joined(manifestParts) : null;
  return {
    model: model.model,
    key,
    version: bundle.version,
    loaded_at: bundle.loaded_at,
    current: bundle.current === undefined ? true : bundle.current === 1,
    body: joined(parts),
    schema: schemaParts.length ? joined(schemaParts) : null,
    manifest: manifest && {
      made_at: manifest.made_at ?? null,
      checksum: manifest.checksum ?? null,
      lab_commit: manifest.lab_commit ?? null,
      snapshot: manifest.snapshot ?? null,
    },
  };
}
