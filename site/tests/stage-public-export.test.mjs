import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

test("only reviewed data replaces the public snapshot; failures preserve its previous contents", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-stage-"));
  try {
    const source = path.join(temporary, "source.json");
    const target = path.join(temporary, "published.json");
    const history = path.join(temporary, "topics.json");
    fs.writeFileSync(history, '["retired-topic"]');
    const run = () => spawnSync(process.execPath, ["scripts/stage-public-export.mjs", source, target, history], { encoding: "utf8" });
    for (const data of [
      { preview: true, claims: [{ slug: "unreviewed", checked_by_person: true }] },
      { preview: false, claims: [{ slug: "unreviewed", checked_by_person: false }] },
      { preview: false, claims: [] },
      null,
    ]) {
      fs.writeFileSync(source, JSON.stringify(data));
      fs.writeFileSync(target, "previous snapshot");
      assert.notEqual(run().status, 0);
      assert.equal(fs.readFileSync(target, "utf8"), "previous snapshot");
      assert.deepEqual(JSON.parse(fs.readFileSync(history, "utf8")), ["retired-topic"]);
    }
    fs.writeFileSync(source, "invalid JSON");
    assert.notEqual(run().status, 0);
    assert.equal(fs.readFileSync(target, "utf8"), "previous snapshot");
    const good = { schema_version: 1, preview: false, claims: [{ slug: "reviewed", checked_by_person: true }], verticals: [{ slug: "new-topic" }] };
    fs.writeFileSync(source, JSON.stringify(good));
    const result = run();
    assert.equal(result.status, 0, result.stderr);
    assert.deepEqual(JSON.parse(fs.readFileSync(target, "utf8")), good);
    assert.deepEqual(JSON.parse(fs.readFileSync(history, "utf8")), ["new-topic", "retired-topic"]);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});
