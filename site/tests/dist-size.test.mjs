// The build check on file sizes: openspec open-data, "No built file near the host's limit".
// Files are made sparse, so a 21 MiB file costs no disk.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { FILE_LIMIT, SEARCH_GZIP_LIMIT, countFiles, oversizedFiles } from "../scripts/dist-size.mjs";
import { randomBytes } from "node:crypto";
import { NOTICES } from "../src/lib/notices.ts";

const CHECK = path.resolve(import.meta.dirname, "../scripts/check-dist.mjs");

function built(sizes) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-dist-size-"));
  const dist = path.join(root, "dist");
  fs.mkdirSync(path.join(dist, "data/claims"), { recursive: true });
  fs.writeFileSync(
    path.join(dist, "index.html"),
    `<footer>${[...NOTICES, "Data sources:", "Registries"].join(" ")}</footer>`,
  );
  for (const [file, bytes] of Object.entries(sizes)) {
    fs.writeFileSync(path.join(dist, file), "");
    fs.truncateSync(path.join(dist, file), bytes);
  }
  return root;
}

test("oversizedFiles names each file over the limit, largest first", () => {
  const root = built({ "data/claims.json": 1000, "data/claims/a.json": 3000, "data/claims/b.json": 5000 });
  assert.deepEqual(oversizedFiles(path.join(root, "dist"), 2000), [
    { file: "data/claims/b.json", bytes: 5000 },
    { file: "data/claims/a.json", bytes: 3000 },
  ]);
});

test("Scenario: A built file over 20 MiB", () => {
  const root = built({ "data/claims.json": FILE_LIMIT + 2 ** 20 });
  const result = spawnSync(process.execPath, [CHECK], { cwd: root, encoding: "utf8" });
  assert.notEqual(result.status, 0);
  assert.match(result.stderr, /data\/claims\.json is 21\.0 MiB, over the 20 MiB/);
});

test("a build with every file under 20 MiB passes", () => {
  const root = built({ "data/claims.json": FILE_LIMIT });
  const result = spawnSync(process.execPath, [CHECK], { cwd: root, encoding: "utf8" });
  assert.equal(result.status, 0, result.stderr);
  assert.match(result.stdout, /no file over 20 MiB/);
});

test("Scenario: Too many built files", () => {
  const root = built({});
  for (let index = 0; index < 30; index += 1) {
    fs.writeFileSync(path.join(root, "dist/data/claims", `claim-${index}.json`), "{}");
  }
  assert.equal(countFiles(path.join(root, "dist")), 31);
  const run = (limit) =>
    spawnSync(process.execPath, [CHECK], {
      cwd: root,
      encoding: "utf8",
      env: { ...process.env, DIST_FILE_LIMIT: String(limit) },
    });
  const over = run(20);
  assert.notEqual(over.status, 0);
  assert.match(over.stderr, /the build holds 31 files, over the 20 a build may hold/);
  const under = run(40);
  assert.equal(under.status, 0, under.stderr);
  assert.match(under.stdout, /31 files of the 40 a build may hold/);
});

test("a search file over 2 MiB with gzip stops the build, and a lighter one passes", () => {
  const root = built({});
  fs.mkdirSync(path.join(root, "dist/lookup"));
  // Random bytes do not compress, so the gzip size is about the file's own.
  fs.writeFileSync(path.join(root, "dist/lookup/2.json"), randomBytes(SEARCH_GZIP_LIMIT + 2 ** 17));
  const over = spawnSync(process.execPath, [CHECK], { cwd: root, encoding: "utf8" });
  assert.notEqual(over.status, 0);
  assert.match(over.stderr, /lookup\/2\.json is 2\.1 MiB with gzip, over the 2 MiB the search may download/);
  // A file far larger than the limit that compresses well is no problem.
  fs.writeFileSync(path.join(root, "dist/lookup/2.json"), "{}".padEnd(SEARCH_GZIP_LIMIT * 3, " "));
  fs.writeFileSync(path.join(root, "dist/search-detail.json"), "{}");
  const under = spawnSync(process.execPath, [CHECK], { cwd: root, encoding: "utf8" });
  assert.equal(under.status, 0, under.stderr);
});
