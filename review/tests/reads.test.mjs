// The review site's statements only read, and nothing else can be sent.
import { test } from "node:test";
import assert from "node:assert/strict";
import { STATEMENTS, read } from "../worker/reads.mjs";

test("every listed statement is one SELECT", () => {
  for (const [name, sql] of Object.entries(STATEMENTS)) {
    assert.match(sql, /^SELECT /, name);
    assert.doesNotMatch(sql, /;|\b(INSERT|UPDATE|DELETE|REPLACE|CREATE|DROP|ALTER|ATTACH|PRAGMA|VACUUM)\b/i, name);
  }
});

test("a statement that is not listed is refused before it reaches the store", async () => {
  const store = { prepare: () => assert.fail("the store was asked") };
  await assert.rejects(read(store, "DELETE FROM pair"), /only its listed statements/);
  await assert.rejects(read(store, `${STATEMENTS.current} OR 1 = 1`), /only its listed statements/);
});
