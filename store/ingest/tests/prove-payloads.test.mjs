// F04: the cut-over's payloads stage proves every distinct object the hot and the bulk
// file refer to, by key and SHA-256, in the bucket, on the local engine and remote; a
// missing payload folder passes only when the bucket's bytes are proved.
import assert from "node:assert/strict";
import { existsSync, mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { test } from "node:test";
import { provePayloads, referenced } from "../scripts/payload-proof.mjs";
import { external, putObject, scratch, script, sha, storeFile } from "./helpers.mjs";

const inline = { sha256: sha("small"), bytes: 5, body: "small" };
// A build: a hot file referring to A and S, a bulk file to B and S (S in both tiers),
// each tier's folder holding its objects, and the local engine's bucket holding all.
function build(t, { folders = ["hot", "bulk"], bucket: inBucket = ["A", "B", "S"] } = {}) {
  const root = scratch(t), bucket = join(root, "bucket"), dir = join(root, "build");
  const objects = { A: external("A"), B: external("B"), S: external("S") };
  mkdirSync(dir);
  const hot = storeFile(join(dir, "store.hot.sqlite"), [inline, objects.A.row, objects.S.row]);
  const bulk = storeFile(join(dir, "store.bulk.sqlite"), [objects.B.row, objects.S.row]);
  const tiers = { hot: ["A", "S"], bulk: ["B", "S"] };
  for (const tier of folders) {
    mkdirSync(join(dir, "payloads", tier, "payload"), { recursive: true });
    for (const name of tiers[tier]) writeFileSync(join(dir, "payloads", tier, "payload", objects[name].row.sha256), objects[name].bytes);
  }
  for (const name of inBucket) putObject(bucket, `payload/${objects[name].row.sha256}`, objects[name].bytes);
  const prove = (...more) => script("prove-payloads.mjs", "--hot", hot, "--bulk", bulk,
    ...folders.flatMap((tier) => ["--payloads", join(dir, "payloads", tier)]), "--persist-to", bucket, ...more);
  return { root, bucket, dir, hot, bulk, objects, prove };
}

test("every distinct object of both tiers is proved in the bucket: S, in both files, once", (t) => {
  const { prove } = build(t);
  const done = prove();
  assert.equal(done.code, 0, done.text);
  assert.match(done.out, /^3 payload object\(s\) referenced by the hot and bulk file\(s\): 3 proved .*local engine.*\(3 with a copy in the build's folders, 0 only in the bucket\), 0 failed/m);
});

test("missing payload folders pass when the bucket holds every object, proved (preuploaded)", (t) => {
  const { prove } = build(t, { folders: [] });
  const done = prove();
  assert.equal(done.code, 0, done.text);
  assert.match(done.out, /3 proved .*\(0 with a copy in the build's folders, 3 only in the bucket\)/);
});

test("a missing bulk folder and an object of the bulk file missing from the bucket fail", (t) => {
  const { prove, objects } = build(t, { folders: ["hot"], bucket: ["A", "S"] });
  const done = prove();
  assert.equal(done.code, 1, done.text);
  assert.match(done.err, new RegExp(`FAILED payload/${objects.B.row.sha256.slice(0, 12)}…: \\(bulk\\) MISSING from the bucket, and not in the build's payload folders`));
});

test("an object in its folder but not in the bucket fails (nothing was sent)", (t) => {
  const { prove } = build(t, { bucket: ["A", "B"] });
  const done = prove();
  assert.equal(done.code, 1, done.text);
  assert.match(done.err, /\((bulk,hot|hot,bulk)\) MISSING from the bucket/);
});

test("a corrupt object in the bucket fails, though the build's copy is right", (t) => {
  const { prove, bucket, objects } = build(t);
  putObject(bucket, `payload/${objects.A.row.sha256}`, Buffer.from(objects.A.bytes).fill(0x41, 0, 1).fill(0x42, 1, 2));
  const done = prove();
  assert.equal(done.code, 1, done.text);
  assert.match(done.err, /\(hot\) the bucket's object DIFFERS/);
});

test("a short object in the bucket fails", (t) => {
  const { prove, bucket, objects } = build(t);
  putObject(bucket, `payload/${objects.B.row.sha256}`, objects.B.bytes.subarray(1));
  assert.match(prove().err, /\(bulk\) the bucket's object DIFFERS/);
});

test("a corrupt copy in the build's folder fails, though the bucket's is right", (t) => {
  const { prove, dir, objects } = build(t);
  writeFileSync(join(dir, "payloads", "bulk", "payload", objects.B.row.sha256), Buffer.from(objects.B.bytes).fill(0x5a, 0, 3));
  const done = prove();
  assert.equal(done.code, 1, done.text);
  assert.match(done.err, /\(bulk\) the copy in .*payloads\/bulk\/payload is not its checksum's bytes/);
});

test("a row whose key is not payload/<its sha256> fails, though its object is there", (t) => {
  const root = scratch(t), bucket = join(root, "bucket");
  const A = external("A");
  const hot = storeFile(join(root, "hot.sqlite"), [{ ...A.row, r2_key: `payloads/${A.row.sha256}` }]);
  const bulk = storeFile(join(root, "bulk.sqlite"), []);
  putObject(bucket, `payload/${A.row.sha256}`, A.bytes);
  putObject(bucket, `payloads/${A.row.sha256}`, A.bytes);
  const done = script("prove-payloads.mjs", "--hot", hot, "--bulk", bulk, "--persist-to", bucket);
  assert.equal(done.code, 1, done.text);
  assert.match(done.err, /its key is "payloads\//);
});

test("the tiers disagreeing on one payload's size fail", (t) => {
  const root = scratch(t), bucket = join(root, "bucket");
  const A = external("A");
  const hot = storeFile(join(root, "hot.sqlite"), [A.row]);
  const bulk = storeFile(join(root, "bulk.sqlite"), [{ ...A.row, bytes: A.row.bytes + 1 }]);
  putObject(bucket, `payload/${A.row.sha256}`, A.bytes);
  const done = script("prove-payloads.mjs", "--hot", hot, "--bulk", bulk, "--persist-to", bucket);
  assert.equal(done.code, 1, done.text);
  assert.match(done.err, /disagree/);
});

test("inline payloads are not external objects", (t) => {
  const root = scratch(t);
  const hot = storeFile(join(root, "hot.sqlite"), [inline]);
  assert.deepEqual([...referenced([{ tier: "hot", path: hot }])], []);
});

test("a missing payload table stops cutover before it can certify an empty inventory", (t) => {
  const { bulk, prove } = build(t);
  const db = new DatabaseSync(bulk);
  db.exec("DROP TABLE payload");
  db.close();
  const result = prove();
  assert.equal(result.code, 1, result.text);
  assert.match(result.err, /bulk file has no payload table/);
});

// Remote: the same proof against a bucket that answers as Wrangler's remote does, a stub
// that serves stored bytes, says "absent", or fails as a 503.
function remoteStub(objects, failing = new Set()) {
  return { label: "thenwhat-payloads (remote, jurisdiction eu)", remote: true, async get(key, path) {
    if (failing.has(key)) throw new Error("ERROR HTTP 503 service unavailable");
    if (!objects.has(key)) return false;
    writeFileSync(path, objects.get(key)); return true;
  } };
}
test("remote: every referenced object of both tiers is read back; corrupt, missing and unreadable fail", async (t) => {
  const { hot, bulk, dir, objects } = build(t);
  const files = [{ tier: "hot", path: hot }, { tier: "bulk", path: bulk }];
  const folders = ["hot", "bulk"].map((tier) => join(dir, "payloads", tier));
  const key = (name) => `payload/${objects[name].row.sha256}`;
  const quiet = () => {};
  const whole = new Map(["A", "B", "S"].map((name) => [key(name), objects[name].bytes]));
  const good = await provePayloads({ files, folders, store: remoteStub(whole), log: quiet });
  assert.equal(good.ok, true, good.failures.join("\n"));
  assert.equal(good.proved, 3);

  const corrupt = new Map(whole); corrupt.set(key("B"), Buffer.from("not B"));
  const bad = await provePayloads({ files, folders, store: remoteStub(corrupt), log: quiet });
  assert.equal(bad.ok, false);
  assert.match(bad.failures.join("\n"), /\(bulk\) the bucket's object DIFFERS/);

  const missing = new Map(whole); missing.delete(key("S"));
  const gone = await provePayloads({ files, folders: [], store: remoteStub(missing), log: quiet });
  assert.equal(gone.failed, 1);
  assert.match(gone.failures[0], /\((bulk,hot|hot,bulk)\) MISSING from the bucket, and not in the build's payload folders/);

  const down = await provePayloads({ files, folders, store: remoteStub(whole, new Set([key("A")])), log: quiet });
  assert.equal(down.ok, false);
  assert.match(down.failures.join("\n"), /could not be read from the bucket: .*503/);
});

test("cutover's plan names a missing payload folder and what lets it pass", (t) => {
  const { dir } = build(t, { folders: ["hot"] });
  const done = script("cutover.mjs", "--env", "local", "--store-dir", dir, "--dry-run");
  assert.equal(done.code, 0, done.text);
  assert.match(done.out, /payloads\/bulk \(allowed only when the bucket holds every object the files refer to, proved\)/);
  assert.match(done.out, /9 payloads +the payload objects of both tiers, each one referenced proved in the bucket/);
  assert.ok(!existsSync(join(dir, "cutover")));
});
