// Pair pages in a pull request's preview (openspec pairs-site, task 4.5), on this machine:
// the preview configuration with pairs, the bundle loaded into the pairs database on D1's
// local engine by the same commands a preview runs remotely, and Wrangler's own dry run of the
// copy's Worker. Nothing is sent to Cloudflare. The bundle is tests/bundle, real pair pages.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { statements } from "../../store/ingest/scripts/load-pairs.mjs";
import { writeBundleCode } from "../scripts/bundle-code.mjs";
import { PREVIEW_PAIRS_BUNDLE, PREVIEW_PAIRS_DATABASE, loadPairsBundle, pairsConfig } from "../scripts/pairs-preview.mjs";

const WRANGLER = path.resolve("node_modules/wrangler/bin/wrangler.js");
// A stand-in id: the local engine keys its file by it and asks Cloudflare nothing.
const database = { name: PREVIEW_PAIRS_DATABASE, id: "00000000-0000-4000-8000-000000000045" };
const scratch = () => fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-pairs-preview-test-"));
const wrangler = (args) =>
  spawnSync(process.execPath, [WRANGLER, ...args], { encoding: "utf8", env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" } });

test("the preview's configuration gains the Worker with pairs and the pairs database, and production's is refused", () => {
  const dir = scratch();
  const file = pairsConfig({ base: "wrangler.preview.jsonc", database, scratch: dir });
  const config = JSON.parse(fs.readFileSync(file, "utf8"));
  assert.equal(config.name, "thenwhat-pr");
  assert.equal(config.main, path.resolve("worker/with-pairs.mjs"));
  assert.equal(config.assets.directory, path.resolve("dist"));
  assert.deepEqual(config.d1_databases.map((binding) => [binding.binding, binding.database_name, binding.database_id]), [["PAIRS", database.name, database.id]]);
  assert.ok(config.ratelimits.length > 0, "the preview's own counters are kept");
  assert.equal(config.routes, undefined);
  assert.throws(() => pairsConfig({ base: "wrangler.jsonc", database, scratch: dir }), /not a pull request preview's configuration/);
});

test("the preview's configuration is found by its name from any folder, as pr-preview.mjs names it", () => {
  // `make pr-preview` runs from the repository's root and gives the name alone.
  const dir = scratch();
  const script = `const { pairsConfig } = await import(${JSON.stringify(new URL("../scripts/pairs-preview.mjs", import.meta.url).href)});
    console.log(pairsConfig({ base: "wrangler.preview.jsonc", database: ${JSON.stringify(database)}, scratch: ${JSON.stringify(dir)} }));`;
  const run = spawnSync(process.execPath, ["--input-type=module", "-e", script], { cwd: path.resolve(".."), encoding: "utf8" });
  assert.equal(run.status, 0, run.stderr);
  assert.equal(JSON.parse(fs.readFileSync(run.stdout.trim(), "utf8")).assets.directory, path.resolve("dist"));
});

test("a preview loads its bundle into the pairs database once, after the store's migrations", () => {
  const dir = scratch();
  const persistTo = path.join(dir, "state");
  const config = pairsConfig({ base: "wrangler.preview.jsonc", database, scratch: dir });
  const first = loadPairsBundle({ config, database, bundle: PREVIEW_PAIRS_BUNDLE, local: true, persistTo });
  assert.deepEqual(first, { version: statements(PREVIEW_PAIRS_BUNDLE).version, loaded: true });
  const again = loadPairsBundle({ config, database, bundle: PREVIEW_PAIRS_BUNDLE, local: true, persistTo });
  assert.deepEqual(again, { version: first.version, loaded: false });

  const read = wrangler(["d1", "execute", database.name, "--local", "--persist-to", persistTo, "--config", config, "--json",
    "--command", "SELECT b.version, b.current, (SELECT count(*) FROM pair p WHERE p.version = b.version) AS pairs FROM pair_bundle b"]);
  assert.equal(read.status, 0, read.stderr);
  const rows = JSON.parse(read.stdout.slice(read.stdout.indexOf("[")))[0].results;
  assert.deepEqual(rows, [{ version: first.version, current: 1, pairs: fs.readdirSync(path.join(PREVIEW_PAIRS_BUNDLE, "p12_pair_page")).length }]);
});

test("Wrangler accepts the copy's Worker with pairs and its binding, in a dry run", async () => {
  const dir = scratch();
  // The validators a build that reads the bundle writes, which the Worker with pairs imports.
  await writeBundleCode(PREVIEW_PAIRS_BUNDLE, ".bundle-code");
  const assets = path.join(dir, "assets");
  fs.mkdirSync(assets);
  fs.writeFileSync(path.join(assets, "index.html"), "<!doctype html><title>copy</title>");
  const base = path.join(dir, "wrangler.preview.jsonc");
  fs.writeFileSync(base, fs.readFileSync("wrangler.preview.jsonc", "utf8").replace('"directory": "./dist"', `"directory": ${JSON.stringify(assets)}`));
  const config = pairsConfig({ base, database, scratch: dir });
  const out = path.join(dir, "out");
  const run = wrangler(["deploy", "--dry-run", "--config", config, "--name", "thenwhat-pr-45", "--outdir", out]);
  assert.equal(run.status, 0, run.stdout + run.stderr);
  assert.match(run.stdout, /env\.PAIRS/);
  const bundled = fs.readdirSync(out).filter((name) => name.endsWith(".js")).map((name) => fs.readFileSync(path.join(out, name), "utf8")).join("\n");
  assert.match(bundled, /FROM pair_page WHERE version = \?1/);
  assert.match(bundled, /validatePairPage/);
});
