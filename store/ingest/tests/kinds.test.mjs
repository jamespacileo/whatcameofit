// The lists that say where a kind of record goes agree with one another: the kinds the
// door takes (src/kinds.mjs), the tier each is pushed to (the pipeline's
// pipeline/src/thenwhat/store/tiers.py, read here as text), the kinds the inbox keeps,
// and the rows clearing the inbox deletes (src/store.mjs). The pipeline holds the same
// in pipeline/tests/test_store_kinds.py; a new kind has to pass both.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { INBOX_KINDS, KINDS } from "../src/kinds.mjs";

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8");
const tiers = read("../../../pipeline/src/thenwhat/store/tiers.py");
const set = (name) => {
  const found = new RegExp(`^${name} = frozenset\\(\\s*\\{([^}]*)\\}`, "m").exec(tiers);
  assert.ok(found, `${name} in tiers.py`);
  return new Set([...found[1].matchAll(/"([a-z_]+)"/g)].map(([, kind]) => kind));
};
const HOT = set("HOT_KINDS"), BULK = set("BULK_KINDS"), FOLLOWING = set("FOLLOWING_KINDS");

test("every kind the door takes is in exactly one of the pipeline's tier lists", () => {
  assert.equal(new Set(KINDS).size, KINDS.length);
  for (const kind of KINDS) {
    assert.equal([HOT, BULK, FOLLOWING].filter((list) => list.has(kind)).length, 1, `${kind} must be in exactly one of HOT_KINDS, BULK_KINDS and FOLLOWING_KINDS`);
  }
  for (const kind of [...HOT, ...BULK, ...FOLLOWING]) assert.ok(KINDS.includes(kind), `a tier names ${kind}, which the door does not take`);
});

test("the inbox keeps exactly the bulk kinds", () => {
  assert.deepEqual([...INBOX_KINDS].sort(), [...BULK].sort());
});

test("clearing the inbox never deletes a row from under another", () => {
  // Whatever references a table the clearing deletes from is deleted first, or the
  // clearing leaves alone the rows it references (`NOT EXISTS (SELECT 1 FROM <it> ...`).
  // Otherwise the clearing fails on a foreign key every time it is tried.
  const clearing = /const FOLDED = [\s\S]*?const CLEAR = \[([\s\S]*?)\n\];/.exec(read("../src/store.mjs"));
  const clear = clearing[1];
  const cleared = [...clear.matchAll(/DELETE FROM (\w+)/g)].map(([, table]) => table).filter((table) => !["inbox", "inbox_folded"].includes(table));
  const db = new DatabaseSync(":memory:");
  db.exec(read("../../schema.sql"));
  const tables = db.prepare("SELECT name FROM sqlite_master WHERE type = 'table'").all().map((row) => row.name);
  for (const parent of cleared) {
    for (const child of tables) {
      if (child === parent || !db.prepare(`PRAGMA foreign_key_list(${child})`).all().some((key) => key.table === parent)) continue;
      if (clearing[0].includes(`NOT EXISTS (SELECT 1 FROM ${child} `)) continue;
      assert.ok(cleared.includes(child), `${child} references ${parent} and is never cleared`);
      assert.ok(cleared.indexOf(child) < cleared.indexOf(parent), `${child} is cleared after ${parent}`);
    }
  }
  db.close();
});
