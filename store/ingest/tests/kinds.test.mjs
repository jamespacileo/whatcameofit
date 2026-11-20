// The rows clearing the inbox deletes (src/store.mjs) never sit under another row. The
// kinds were once also held to the claims pipeline's tier lists; the pipeline was removed
// on 2026-11-20 (James, "Delete it now"), so the door's own lists are the only ones.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";
import { fileURLToPath } from "node:url";
import { INBOX_KINDS, KINDS } from "../src/kinds.mjs";

const read = (path) => readFileSync(fileURLToPath(new URL(path, import.meta.url)), "utf8");

test("the door takes each kind once, and the inbox keeps only kinds the door takes", () => {
  assert.equal(new Set(KINDS).size, KINDS.length);
  for (const kind of INBOX_KINDS) assert.ok(KINDS.includes(kind), kind);
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
