// Disposable fixtures for the tests here: a bucket on the local engine (the fake Wrangler
// in node_modules keeps an object at <persist dir>/<key>), store files made from
// store/schema.sql, and the scripts run as the operator runs them.
import { after } from "node:test";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { cpSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { DatabaseSync } from "node:sqlite";
import { fileURLToPath } from "node:url";

// Run the unmodified CLIs beside a filesystem-backed Wrangler in a disposable checkout.
const fixture = mkdtempSync(join(tmpdir(), "thenwhat-r2-cli-"));
after(() => rmSync(fixture, {recursive: true, force: true}));
const scripts = join(fixture, "scripts");
cpSync(fileURLToPath(new URL("../scripts/", import.meta.url)), scripts, {recursive: true});
cpSync(fileURLToPath(new URL("../wrangler.jsonc", import.meta.url)), join(fixture, "wrangler.jsonc"));
mkdirSync(join(fixture, "node_modules/.bin"), {recursive: true});
writeFileSync(join(fixture, "node_modules/.bin/wrangler"), `#!/usr/bin/env node
const fs = require("node:fs"), path = require("node:path");
const args = process.argv.slice(2), option = k => args[args.indexOf(k)+1];
const dir = option("--persist-to"), key = args[3].split("/").slice(1).join("/");
const object = path.join(dir, key), file = option("--file");
if (args[2] === "get") {
  if (key.endsWith("/deltas.json") && fs.existsSync(path.join(dir, "outage"))) {
    console.error("ERROR HTTP 503 service unavailable"); process.exit(1);
  }
  if (!fs.existsSync(object)) {console.error("The specified key does not exist. (NoSuchKey)"); process.exit(1);}
  fs.copyFileSync(object, file);
} else if (args[2] === "put") {
  fs.mkdirSync(path.dirname(object), {recursive:true}); fs.copyFileSync(file, object);
} else process.exit(2);
`, {mode: 0o755});
const schema = fileURLToPath(new URL("../../schema.sql", import.meta.url));

export const sha = (bytes) => createHash("sha256").update(bytes).digest("hex");
export function scratch(t) {
  const dir = mkdtempSync(join(tmpdir(), "thenwhat-test-"));
  t.after(() => rmSync(dir, { recursive: true, force: true }));
  return dir;
}
export function script(name, ...args) {
  const done = spawnSync(process.execPath, [join(scripts, name), ...args], { encoding: "utf8", timeout: 120_000 });
  return { code: done.status, out: done.stdout, err: done.stderr, text: `${done.stdout}\n${done.stderr}` };
}
// An object in the local engine's bucket, put there as another run would have left it.
export function putObject(bucket, key, bytes) { mkdirSync(dirname(join(bucket, key)), { recursive: true }); writeFileSync(join(bucket, key), bytes); }
export const readObject = (bucket, key) => readFileSync(join(bucket, key));
// Every object under a folder of the bucket, name to bytes and modification time.
export function snapshot(folder) {
  return Object.fromEntries(readdirSync(folder).sort().map((name) => [name, { bytes: readFileSync(join(folder, name)).toString("hex"), mtime: statSync(join(folder, name)).mtimeMs }]));
}
// A store file with the schema's tables, a build run and the given payload rows:
// [{sha256, bytes, body} | {sha256, bytes, r2_key}].
export function storeFile(path, payloads) {
  const db = new DatabaseSync(path);
  try {
    db.exec(readFileSync(schema, "utf8"));
    db.prepare("INSERT INTO run (id, writer, commit_sha, registered_at) VALUES (?, 'migration', 'test', '2026-11-17T00:00:00Z')").run("build-0123456789abcdef-test");
    const insert = db.prepare("INSERT INTO payload (sha256, bytes, body, r2_key, added_run) VALUES (?, ?, ?, ?, 'build-0123456789abcdef-test')");
    for (const row of payloads) insert.run(row.sha256, row.bytes, row.body ?? null, row.r2_key ?? null);
  } finally { db.close(); }
  return path;
}
// A payload large enough to be an R2 object, its row, and its bytes.
export function external(seed) {
  const bytes = Buffer.from(`${seed}:`.repeat(40_000));
  const sum = sha(bytes);
  return { bytes, row: { sha256: sum, bytes: bytes.length, r2_key: `payload/${sum}` } };
}
