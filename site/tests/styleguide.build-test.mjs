// The styleguide (src/styleguide/Styleguide.astro): built only when STYLEGUIDE=1, which staging
// and pull request previews set; it draws every shared block of lib/blocks.ts with the bundle,
// is never indexed, and a production build never holds it, whatever its shell carries.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, test } from "node:test";
import * as blocks from "../src/lib/blocks.ts";
import { writeManifest } from "../../store/ingest/scripts/bundle-manifest.mjs";

const outDirs = [];
after(() => { for (const dir of outDirs) fs.rmSync(dir, { recursive: true, force: true }); });

function build(env) {
  const outDir = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-styleguide-"));
  outDirs.push(outDir);
  const run = spawnSync("npx", ["astro", "build", "--outDir", outDir], {
    env: { ...process.env, ASTRO_TELEMETRY_DISABLED: "1", PAIRS_BUNDLE: "tests/bundle", ...env },
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  assert.equal(run.status, 0, run.stdout.slice(-3000) + run.stderr.slice(-3000));
  return outDir;
}

test("with STYLEGUIDE=1 the styleguide draws every shared block, and is never indexed", () => {
  const html = fs.readFileSync(path.join(build({ STYLEGUIDE: "1" }), "styleguide", "index.html"), "utf8");
  // Every function lib/blocks.ts exports, but escape, which draws nothing.
  const drawn = Object.entries(blocks).filter(([name, value]) => typeof value === "function" && name !== "escape" && name !== "sourceNames").map(([name]) => name);
  assert.ok(drawn.length >= 10);
  for (const name of drawn) assert.ok(html.includes(`data-block="${name}"`), `${name} is not on the styleguide`);
  assert.match(html, /<meta name="robots" content="noindex, follow">/);
  // The whole pieces: a pair's page, the listings and the embed, each listing one that lists pairs.
  assert.match(html, /A pair&#39;s page: |A pair's page: /);
  assert.match(html, /An embed</);
  assert.doesNotMatch(html, /No pair is listed here yet/);
  // No two samples share an id.
  const ids = [...html.matchAll(/ id="([^"]+)"/g)].map((match) => match[1]);
  assert.deepEqual(ids.filter((id, index) => ids.indexOf(id) !== index), []);
});

test("a bundle with no pair page still builds the styleguide, saying it has none to draw with", () => {
  const empty = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-styleguide-bundle-"));
  outDirs.push(empty);
  fs.cpSync("tests/bundle", empty, { recursive: true });
  for (const folder of ["p12_pair_page", "p12_pair_data_file"]) fs.rmSync(path.join(empty, folder), { recursive: true, force: true });
  fs.mkdirSync(path.join(empty, "p12_pair_page"));
  fs.rmSync(path.join(empty, "manifest.json"));
  writeManifest(empty, { madeAt: "2026-11-20T00:00:00Z" });
  const html = fs.readFileSync(path.join(build({ STYLEGUIDE: "1", PAIRS_BUNDLE: empty }), "styleguide", "index.html"), "utf8");
  assert.match(html, /This bundle has no pair page to draw it with/);
});

test("without STYLEGUIDE there is no styleguide", () => {
  assert.ok(!fs.existsSync(path.join(build({ STYLEGUIDE: "" }), "styleguide")));
});

test("a production build has no styleguide even when its shell sets STYLEGUIDE=1", () => {
  const run = spawnSync(process.execPath, ["scripts/deploy.mjs", "--dry-run"], {
    encoding: "utf8",
    maxBuffer: 256 * 1024 * 1024,
    // The fixture alone: a database named in this shell would take precedence over the folder.
    env: { ...process.env, SITE_URL: "https://whatcameofit.com", PAIRS_BUNDLE: "tests/bundle", PAIRS_DATABASE: "", PAIRS_VERSION: "", PAIRS_LOCAL_STATE: "", STYLEGUIDE: "1", ASTRO_TELEMETRY_DISABLED: "1", CI: "1", WRANGLER_SEND_METRICS: "false" },
  });
  assert.equal(run.status, 0, run.stdout.slice(-3000) + run.stderr.slice(-3000));
  assert.ok(!fs.existsSync(path.join("dist", "styleguide")));
});
