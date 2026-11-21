// The model inventory: for each catalogued model, whether an environment's store holds it and
// how many records, and the records themselves a page at a time. Every statement is built here
// from the catalogue's fixed table names, never from a request, and goes through `read`.
import { MODELS, TABLES, modelById, notAModel } from "./catalogue.mjs";
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
  pageCounts: allow("SELECT model, COUNT(*) AS n FROM pair_page WHERE version = ? AND part = 0 GROUP BY model"),
  pageKeys: allow("SELECT key FROM pair_page WHERE version = ? AND model = ? AND part = 0 ORDER BY key LIMIT ? OFFSET ?"),
  pageParts: allow("SELECT body FROM pair_page WHERE version = ? AND model = ? AND key = ? ORDER BY part"),
  count: {},
  countIn: {},
  rows: {},
  rowsIn: {},
};

for (const { table, versioned } of TABLES) {
  const select = NARROW[table] ?? `SELECT * FROM ${table}`;
  S.count[table] = allow(`SELECT COUNT(*) AS n FROM ${table}`);
  S.rows[table] = allow(`${select} LIMIT ? OFFSET ?`);
  if (versioned) {
    S.countIn[table] = allow(`SELECT COUNT(*) AS n FROM ${table} WHERE version = ?`);
    S.rowsIn[table] = allow(`${select} WHERE version = ? LIMIT ? OFFSET ?`);
  }
}

async function present(db) {
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
  return { bundle, states, unlisted };
}

async function hasSchema(db, version, model) {
  return (await read(db, S.pageParts, version, "$schema", model)).length > 0;
}

function joined(parts) {
  return JSON.parse(parts.map((row) => row.body).join(""));
}

/** One page of a model's records in one environment, with its columns as the store has them. */
export async function rowsOf(db, id, offset = 0) {
  const model = modelById.get(id);
  if (!model) return null;
  const tables = await present(db);
  if (model.kind === "page-model") {
    const bundle = await currentBundle(db, tables);
    if (!bundle) return { columns: [], rows: [], total: 0, offset, limit: PAGE_ROWS };
    const counts = new Map((await read(db, S.pageCounts, bundle.version)).map((row) => [row.model, row.n]));
    const keys = await read(db, S.pageKeys, bundle.version, model.model, PAGE_ROWS, offset);
    return { columns: [{ name: "key", key: true }], rows: keys, total: counts.get(model.model) ?? 0, offset, limit: PAGE_ROWS, version: bundle.version };
  }
  if (!tables.has(model.table)) return { columns: [], rows: [], total: 0, offset, limit: PAGE_ROWS, absent: true };
  const hidden = new Set(model.hidden ?? []);
  const columns = (await read(db, S.columns, model.table))
    .filter((c) => !(NARROW[model.table] && hidden.has(c.name)))
    .map((c) => ({ name: c.name, key: c.pk > 0, hidden: hidden.has(c.name) }));
  if (NARROW[model.table]) columns.push({ name: "body_chars", key: false, hidden: false });
  let rows;
  let total;
  let version = null;
  if (model.versioned) {
    const bundle = await currentBundle(db, tables);
    version = bundle?.version ?? null;
    rows = version ? await read(db, S.rowsIn[model.table], version, PAGE_ROWS, offset) : [];
    total = version ? (await read(db, S.countIn[model.table], version))[0].n : 0;
  } else {
    rows = await read(db, S.rows[model.table], PAGE_ROWS, offset);
    total = (await read(db, S.count[model.table]))[0].n;
  }
  for (const row of rows) for (const name of hidden) delete row[name];
  return { columns: columns.filter((c) => !c.hidden), hiddenColumns: [...hidden], rows, total, offset, limit: PAGE_ROWS, version };
}

/** One page model's record: its page file, the schema it was checked against, and the
 * bundle's provenance from its manifest. */
export async function pageRecord(db, id, key) {
  const model = modelById.get(id);
  if (!model || model.kind !== "page-model") return null;
  const tables = await present(db);
  const bundle = await currentBundle(db, tables);
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
