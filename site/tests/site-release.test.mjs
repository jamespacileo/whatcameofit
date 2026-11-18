import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

import { prepareSiteRelease } from "../scripts/site-release-deploy.mjs";
import { FILE_LIMIT } from "../scripts/dist-size.mjs";
import { handle } from "../worker/index.mjs";

const origin = "https://whatcameofit.test";
const digest = (source) => createHash("sha256").update(source).digest("hex");

function release(files, { noindex = false } = {}) {
  const shards = new Map();
  const objects = new Map();
  const reads = [];
  for (const [name, body] of Object.entries(files)) {
    const value = Buffer.from(body);
    const hash = digest(value);
    const shard = digest(name).slice(0, 2);
    const manifest = shards.get(shard) ?? {};
    manifest[name] = [hash, value.length];
    shards.set(shard, manifest);
    objects.set(`site-files/v1/${hash}`, value);
  }
  const env = {
    ASSETS: {
      async fetch(request) {
        const pathname = new URL(request.url).pathname;
        const shard = /^\/_site-release\/([a-f0-9]{2})\.json$/.exec(pathname)?.[1];
        if (shards.has(shard)) return Response.json({ noindex, files: shards.get(shard) });
        if (shard) return new Response("Missing shard", { status: 404 });
        if (pathname === "/gone.json") {
          return Response.json([{ slug: "retired", to: "registry-example" }, { slug: "archived", on: "2026-11-18" }]);
        }
        if (pathname === "/topic/test" || pathname === "/lookup.json") return new Response("Shared file");
        return new Response("Site 404 page", { status: 404 });
      },
    },
    SITE_FILES: {
      async get(key) {
        reads.push(key);
        const value = objects.get(key);
        return value && { size: value.length, body: new Response(value).body };
      },
      async head(key) {
        const value = objects.get(key);
        return value && { size: value.length };
      },
    },
  };
  return { env, reads, objects };
}

test("one staged release serves stable addresses for browsable claims and their search index", async () => {
  const entries = {
    "registry-example/index.html": "<h1>Example registry claim</h1>",
    "data/claims/registry-example.json": '{"claim":"registry-example"}',
    "changes/registry-example.xml": "<feed/>",
    "embed/registry-example/index.html": "<h1>Embed</h1>",
    "oembed/registry-example.json": "{}",
    "og/registry-example.png": "image",
    "og/square/registry-example.png": "square",
    "og/tall/registry-example.png": "tall",
    "pagefind/pagefind.js": "export {};",
    "pagefind/fragment/en_8d01202.pf_fragment": "fragment",
  };
  const { env, reads } = release(entries, { noindex: true });
  for (const [name, body] of Object.entries(entries)) {
    const pathname = `/${name.replace(/\/index\.html$/, "")}`;
    const response = await handle(new Request(origin + pathname), env);
    assert.equal(response.status, 200, pathname);
    assert.equal(await response.text(), body, pathname);
    assert.equal(response.headers.get("x-robots-tag"), "noindex");
    assert.equal(response.headers.get("x-content-type-options"), "nosniff");
    assert.equal(response.headers.get("etag"), `"${digest(body)}"`);
  }
  assert.equal(reads.length, Object.keys(entries).length);
  const head = await handle(new Request(`${origin}/registry-example`, { method: "HEAD" }), env);
  assert.equal(head.status, 200);
  assert.equal(await head.text(), "");
  assert.equal(Number(head.headers.get("content-length")), entries["registry-example/index.html"].length);
  const etag = head.headers.get("etag");
  const unchanged = await handle(new Request(`${origin}/registry-example`, { headers: { "If-None-Match": `W/${etag}` } }), env);
  assert.equal(unchanged.status, 304);
  assert.equal(reads.length, Object.keys(entries).length);
  const canonical = await handle(new Request(`${origin}/registry-example/index.html?from=feed`), env);
  assert.equal(canonical.status, 308);
  assert.equal(canonical.headers.get("location"), `${origin}/registry-example?from=feed`);
  for (const pathname of ["/topic/test", "/lookup.json"]) {
    assert.equal(await (await handle(new Request(origin + pathname), env)).text(), "Shared file");
  }
  for (const internal of ["_site-release", "_site%2Drelease"]) {
    const shard = digest("registry-example/index.html").slice(0, 2);
    const hidden = await handle(new Request(`${origin}/${internal}/${shard}.json`), env);
    assert.equal(hidden.status, 404);
  }
  assert.equal((await handle(new Request(`${origin}/archived`), env)).status, 410);
  assert.equal((await handle(new Request(`${origin}/retired`), env)).headers.get("location"), `${origin}/registry-example`);
});

test("a release rollback selects the old bytes and a missing staged file fails closed", async () => {
  const path = "registry-example/index.html";
  const old = release({ [path]: "old release" });
  const next = release({ [path]: "new release" });
  const request = new Request(`${origin}/registry-example`);
  assert.equal(await (await handle(request, next.env)).text(), "new release");
  assert.equal(await (await handle(request, old.env)).text(), "old release");
  next.objects.clear();
  const failed = await handle(request, next.env);
  assert.equal(failed.status, 503);
  assert.equal(failed.headers.get("cache-control"), "no-store");
  const missing = await handle(new Request(`${origin}/unknown-claim`), next.env);
  assert.equal(missing.status, 404);
  assert.equal(await missing.text(), "Site 404 page");
});

test("staging keeps the original build and checks the exact bundle before deployment", (t) => {
  const directory = fs.mkdtempSync(path.join(os.tmpdir(), "site-release-test-"));
  t.after(() => fs.rmSync(directory, { recursive: true, force: true }));
  const files = [
    "registry-example/index.html", "embed/registry-example/index.html",
    "changes/registry-example.xml", "data/claims/registry-example.json", "oembed/registry-example.json",
    "og/registry-example.png", "og/square/registry-example.png", "og/tall/registry-example.png",
  ];
  for (const name of [...files, "pagefind/pagefind.js", "index.html", "_headers"]) {
    const target = path.join(directory, name);
    fs.mkdirSync(path.dirname(target), { recursive: true });
    fs.writeFileSync(target, name.endsWith(".png") ? "the same image bytes" : name);
  }
  const rows = "rows/claims.release-id.txt";
  fs.mkdirSync(path.join(directory, "rows"));
  fs.closeSync(fs.openSync(path.join(directory, rows), "w"));
  fs.truncateSync(path.join(directory, rows), FILE_LIMIT + 1);
  fs.writeFileSync(path.join(directory, "lookup.json"), JSON.stringify({ claims: { "registry-example": {} } }));

  const calls = [];
  const siteDir = path.resolve(import.meta.dirname, "..");
  const configPath = prepareSiteRelease({
    settings: { prefix: "PREVIEW_SITE_FILES", bucket: "test-bucket", remote: "test-remote" },
    siteDir,
    dist: directory,
    noindex: true,
    dryRun: false,
    run(command, args) {
      if (command === "rclone") {
        calls.push(args);
        return;
      }
      const result = spawnSync(command, args, { encoding: "utf8" });
      assert.equal(result.status, 0, result.stdout + result.stderr);
    },
  });
  const config = JSON.parse(fs.readFileSync(configPath, "utf8"));
  assert.deepEqual(config.r2_buckets, [{ binding: "SITE_FILES", bucket_name: "test-bucket" }]);
  assert.ok(config.main.endsWith("/worker/index.mjs"));
  assert.deepEqual(config.assets.run_worker_first, ["/*", "!/_astro/*"]);
  assert.ok(fs.existsSync(path.join(config.assets.directory, "_headers")));
  assert.ok(fs.existsSync(path.join(config.assets.directory, "lookup.json")));
  for (const name of [...files, "pagefind/pagefind.js", rows]) {
    const manifest = path.join(config.assets.directory, "_site-release", digest(name).slice(0, 2) + ".json");
    const contents = fs.readFileSync(path.join(directory, name)); // Still available for verification.
    assert.ok(!fs.existsSync(path.join(config.assets.directory, name)));
    assert.deepEqual(JSON.parse(fs.readFileSync(manifest, "utf8")).files[name], [digest(contents), contents.length]);
  }
  assert.deepEqual(calls.map((args) => args[0]), ["copy", "check"]);
  assert.ok(calls[0].includes("--immutable"));
  assert.ok(calls[1].includes("--one-way"));
  assert.equal(calls[0].at(-1), "test-remote:test-bucket/site-files/v1");
  assert.equal(calls[1].at(-1), calls[0].at(-1));
});

test("a large public row file retains its text type and noindex instruction", async () => {
  const relative = "rows/claims.release-id.txt";
  const { env } = release({ [relative]: "<tr><td>A claim</td></tr>" });
  const response = await handle(new Request(`${origin}/${relative}`), env);
  assert.equal(response.headers.get("x-robots-tag"), "noindex");
  assert.equal(response.headers.get("content-type"), "text/plain; charset=utf-8");
  assert.equal(await response.text(), "<tr><td>A claim</td></tr>");
});
