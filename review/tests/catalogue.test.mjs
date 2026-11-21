// The catalogue lists every table the store's migrations leave, and names the migration that
// made each one.
import { test, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
import { MODELS, TABLES, notAModel } from "../worker/catalogue.mjs";
import { MIGRATIONS, statementsOf } from "./store.mjs";

const mf = new Miniflare(convertV4MiniflareOptions({ modules: true, script: "export default { fetch() { return new Response(null, { status: 404 }); } };", compatibilityDate: "2026-10-01", d1Databases: ["STORE"] }));
after(() => mf.dispose());

test("every table the migrations leave is listed, with the migration that made it", async () => {
  const db = await mf.getD1Database("STORE");
  const madeBy = new Map();
  for (const file of fs.readdirSync(MIGRATIONS).filter((name) => name.endsWith(".sql")).sort()) {
    for (const sql of statementsOf(fs.readFileSync(path.join(MIGRATIONS, file), "utf8"))) await db.prepare(sql).run();
    const { results } = await db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all();
    const now = new Set(results.map((row) => row.name).filter((name) => !notAModel(name)));
    for (const name of now) if (!madeBy.has(name)) madeBy.set(name, file);
    // A table dropped and made again (0007's payload, 0008's work_entry) is made by the later file.
    for (const name of [...madeBy.keys()]) if (!now.has(name)) madeBy.delete(name);
    if (/DROP TABLE|RENAME TO/i.test(fs.readFileSync(path.join(MIGRATIONS, file), "utf8"))) {
      for (const sql of statementsOf(fs.readFileSync(path.join(MIGRATIONS, file), "utf8"))) {
        const made = /^CREATE TABLE (\w+)/i.exec(sql)?.[1];
        if (made && now.has(made)) madeBy.set(made, file);
      }
    }
  }
  for (const entry of TABLES) {
    const columns = (await db.prepare("SELECT name, pk FROM pragma_table_info(?)").bind(entry.table).all()).results;
    const key = columns.filter((c) => c.pk > 0).sort((a, b) => a.pk - b.pk).map((c) => c.name);
    assert.deepEqual(entry.key, key, `${entry.table}'s primary key`);
  }
  const listed = new Map(TABLES.map((entry) => [entry.table, entry.migration]));
  assert.deepEqual([...listed.keys()].sort(), [...madeBy.keys()].sort());
  for (const [name, file] of madeBy) assert.equal(listed.get(name), file, name);
});

test("every model has a readable name and a unique id", () => {
  const ids = new Set();
  for (const model of MODELS) {
    assert.ok(model.name && model.name !== model.table && model.name !== model.model, model.id);
    assert.ok(!ids.has(model.id), model.id);
    ids.add(model.id);
  }
});

test("the page models are the bundle's schemas", () => {
  const schemas = fs.readdirSync("../site/tests/bundle/schemas").map((name) => name.replace(/\.json$/, "")).sort();
  // A model the lab has started writing (`since`) is catalogued ahead of the tests' bundle.
  assert.deepEqual(MODELS.filter((m) => m.kind === "page-model" && !m.since).map((m) => m.model).sort(), schemas);
  for (const m of MODELS.filter((m) => m.since)) assert.ok(!schemas.includes(m.model), `${m.model} is in the tests' bundle now: drop its since`);
});
