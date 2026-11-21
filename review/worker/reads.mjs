// Every statement the review site may send to a pair store. The site is read-only: a D1
// binding could write, so nothing outside this list is ever prepared (`read` refuses it), and
// tests/reads.test.mjs checks that each statement here only reads. Production, when it comes
// (phase 4), is read with an API token that holds D1 Read alone, so Cloudflare enforces it too.

/** The pair tables of migration 0011 (store/ingest/migrations/0011_pairs.sql). */
export const PAIR_TABLES = Object.freeze([
  "pair_bundle",
  "pair_page",
  "pair",
  "pair_intervention",
  "pair_intervention_name",
  "pair_condition",
  "pair_trial",
  "pair_trial_facts",
  "pair_status_change",
]);

export const STATEMENTS = Object.freeze({
  current: "SELECT version, loaded_at, counts FROM pair_bundle WHERE current = 1",
  versions: "SELECT version, loaded_at, current FROM pair_bundle ORDER BY loaded_at DESC, version DESC LIMIT 20",
  ...Object.fromEntries(PAIR_TABLES.map((table) => [`rows:${table}`, `SELECT COUNT(*) AS n FROM ${table}`])),
});

const allowed = new Set(Object.values(STATEMENTS));

/** Adds one statement to the listed set and returns it. Only modules of this Worker call it,
 * at load, with text built from the catalogue's fixed names, never from a request. Each one is
 * checked to be a single SELECT, as tests/reads.test.mjs checks the rest. */
export function allow(sql) {
  if (!/^SELECT /.test(sql) || /;|\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|ATTACH|DETACH|VACUUM)\b/i.test(sql)) {
    throw new Error(`not a read: ${sql}`);
  }
  allowed.add(sql);
  return sql;
}

/** Every statement in the listed set, for the test that checks each one only reads. */
export const listed = () => [...allowed];

/** Rows of one listed statement. */
export async function read(db, sql, ...binds) {
  if (!allowed.has(sql)) throw new Error("the review site sends only its listed statements");
  const { results } = await db.prepare(sql).bind(...binds).all();
  return results;
}

/** Rows of a table, or null when the store has no such table (a store from before 0011). */
async function rowsOf(db, table) {
  try {
    return (await read(db, STATEMENTS[`rows:${table}`]))[0].n;
  } catch (error) {
    if (/no such table/i.test(String(error?.message ?? error))) return null;
    throw error;
  }
}

/** The store at a glance: current bundle, loaded versions, rows per pair table. */
export async function overview(db, environment) {
  const tables = [];
  for (const name of PAIR_TABLES) tables.push({ name, rows: await rowsOf(db, name) });
  if (tables[0].rows === null) return { environment, current: null, versions: [], tables };
  const [current] = await read(db, STATEMENTS.current);
  const versions = await read(db, STATEMENTS.versions);
  return {
    environment,
    current: current ? { version: current.version, loaded_at: current.loaded_at, counts: JSON.parse(current.counts) } : null,
    versions: versions.map((v) => ({ version: v.version, loaded_at: v.loaded_at, current: v.current === 1 })),
    tables,
  };
}
