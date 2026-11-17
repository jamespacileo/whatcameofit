// F02: a day's delta is listed and kept without losing the list or writing over an object,
// through a 503, a 404, an object left by a run that stopped, and a run again.
import assert from "node:assert/strict";
import { existsSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { test } from "node:test";
import { putObject, readObject, scratch, script, sha, snapshot } from "./helpers.mjs";

const DAY = "2026-11-17";
function setup(t) {
  const root = scratch(t), bucket = join(root, "bucket"), build = join(bucket, "bulk", "demo");
  putObject(bucket, "bulk/demo/manifest.json", "{}");
  const upload = (text, ...more) => {
    const file = join(root, "candidate.json");
    writeFileSync(file, text);
    return script("upload-delta.mjs", file, "--build", "demo", "--date", DAY, "--persist-to", bucket, ...more);
  };
  const list = () => JSON.parse(readObject(bucket, "bulk/demo/deltas.json"));
  return { root, bucket, build, upload, list };
}

test("a 503 on the list stops the run before anything is written; a run again lists both", (t) => {
  const { bucket, build, upload, list } = setup(t);
  assert.equal(upload("one").code, 0);
  const before = snapshot(build);
  writeFileSync(join(bucket, "outage"), "");
  const failed = upload("two");
  assert.notEqual(failed.code, 0, "a 503 was taken for an absent list");
  assert.match(failed.err, /503|could not read/);
  assert.deepEqual(snapshot(build), before, "the bucket changed during the outage");
  rmSync(join(bucket, "outage"));
  assert.equal(upload("two").code, 0);
  const again = upload("two");
  assert.equal(again.code, 0);
  assert.match(again.out, /already there: bulk\/demo\/delta-2026-11-17-2\.json/);
  assert.deepEqual(list().deltas.map((delta) => readObject(bucket, `bulk/demo/${delta.name}`).toString()), ["one", "two"]);
});

test("a build that is not there (404 on its manifest) gets no delta and no list", (t) => {
  const { bucket, build, upload } = setup(t);
  rmSync(join(build, "manifest.json"));
  const done = upload("one");
  assert.equal(done.code, 1, done.text);
  assert.match(done.err, /no build demo/);
  assert.deepEqual(Object.keys(snapshot(build)), []);
  assert.ok(!existsSync(join(bucket, "bulk/demo/deltas.json")));
});

test("a same-day object left unlisted with other bytes is not written over; the next name is taken", (t) => {
  const { bucket, upload, list } = setup(t);
  assert.equal(upload("one").code, 0);
  putObject(bucket, `bulk/demo/delta-${DAY}-2.json`, "orphan from a run that stopped");
  const done = upload("two");
  assert.equal(done.code, 0, done.text);
  assert.match(done.out, /left as it is/);
  assert.equal(readObject(bucket, `bulk/demo/delta-${DAY}-2.json`).toString(), "orphan from a run that stopped");
  assert.deepEqual(list().deltas.map((delta) => delta.name), [`delta-${DAY}-1.json`, `delta-${DAY}-3.json`]);
  assert.equal(readObject(bucket, `bulk/demo/delta-${DAY}-3.json`).toString(), "two");
});

test("a run again after the delta was sent but the list was not: listed as it is, not sent again", (t) => {
  const { bucket, build, upload, list } = setup(t);
  assert.equal(upload("one").code, 0);
  // What a run that stopped between the delta and the list leaves.
  putObject(bucket, `bulk/demo/delta-${DAY}-2.json`, "two");
  const left = snapshot(build)[`delta-${DAY}-2.json`];
  const done = upload("two", "--through", "41");
  assert.equal(done.code, 0, done.text);
  assert.match(done.out, /already these bytes/);
  assert.deepEqual(snapshot(build)[`delta-${DAY}-2.json`], left, "the object was sent again");
  const entry = list().deltas.at(-1);
  assert.deepEqual(entry, { name: `delta-${DAY}-2.json`, date: DAY, bytes: 3, sha256: sha("two"), through: 41 });
});

test("the names a list already has are kept, as they are, and a new one never reuses a day's number", (t) => {
  const { bucket, upload, list } = setup(t);
  const old = { build: "demo", note: "kept", deltas: [
    { name: `delta-2026-11-16-1.sqlite.zst`, date: "2026-11-16", bytes: 1, sha256: sha("a"), through: 3 },
    { name: `delta-${DAY}-1.sqlite.zst`, date: DAY, bytes: 1, sha256: sha("b"), through: null },
    { name: `delta-${DAY}-3.zst`, date: DAY, bytes: 1, sha256: sha("c"), through: null, extra: true },
  ] };
  putObject(bucket, "bulk/demo/deltas.json", JSON.stringify(old));
  for (const [delta, bytes] of [[old.deltas[0], "a"], [old.deltas[1], "b"], [old.deltas[2], "c"]]) putObject(bucket, `bulk/demo/${delta.name}`, bytes);
  const done = upload("d");
  assert.equal(done.code, 0, done.text);
  const now = list();
  assert.equal(now.note, "kept");
  assert.deepEqual(now.deltas.slice(0, 3), old.deltas);
  assert.equal(now.deltas[3].name, `delta-${DAY}-4.json`);
  for (const [delta, bytes] of [[old.deltas[0], "a"], [old.deltas[1], "b"], [old.deltas[2], "c"]]) assert.equal(readObject(bucket, `bulk/demo/${delta.name}`).toString(), bytes);
});

test("two deltas on one day are -1 and -2; the same bytes again are not listed twice", (t) => {
  const { upload, list } = setup(t);
  assert.equal(upload("one").code, 0);
  assert.equal(upload("two").code, 0);
  assert.equal(upload("one").code, 0);
  assert.deepEqual(list().deltas.map((delta) => delta.name), [`delta-${DAY}-1.json`, `delta-${DAY}-2.json`]);
});

test("a list that is not JSON, or is another build's, is left as it is and nothing is sent", (t) => {
  for (const text of ["{not json", JSON.stringify({ build: "other", deltas: [] }), JSON.stringify({ build: "demo" })]) {
    const { bucket, build, upload } = setup(t);
    putObject(bucket, "bulk/demo/deltas.json", text);
    const before = snapshot(build);
    const done = upload("one");
    assert.equal(done.code, 1, done.text);
    assert.deepEqual(snapshot(build), before);
  }
});

test("download-deltas fails on a list it cannot read, never reporting a build without deltas", (t) => {
  const { root, bucket, upload } = setup(t);
  assert.equal(upload("one").code, 0);
  writeFileSync(join(bucket, "outage"), "");
  const out = join(root, "out");
  const done = script("download-deltas.mjs", "demo", out, "--persist-to", bucket);
  assert.equal(done.code, 1, done.text);
  assert.doesNotMatch(done.out, /has no delta/);
});

test("download-deltas brings back each listed delta, proved", (t) => {
  const { root, bucket, upload } = setup(t);
  assert.equal(upload("one").code, 0);
  assert.equal(upload("two").code, 0);
  const out = join(root, "out");
  mkdirSync(out);
  const done = script("download-deltas.mjs", "demo", out, "--persist-to", bucket);
  assert.equal(done.code, 0, done.text);
  assert.ok(existsSync(join(out, `delta-${DAY}-2.json`)));
});
