// Staging, rehearsed on this machine (docs/deploy.md, "Staging"): the small bundle loaded into the
// preview store's name on D1's local engine, deploy.mjs --staging in dry-run mode builds from it
// and has Wrangler check a version of thenwhat-staging, then the staging smoke checks run against
// that build's Worker in workerd (Miniflare) with staging's configuration. Nothing is sent to
// Cloudflare. A host that does not resolve is reported as not answering yet, never as a pass.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { build as bundleWorker } from "esbuild";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
import { statements } from "../../store/ingest/scripts/load-pairs.mjs";
import { findDeployDatabase } from "../scripts/pairs-deploy.mjs";
import { loadPairsBundle, pairsConfig } from "../scripts/pairs-preview.mjs";
import { checkStaging, smokeAddresses } from "../scripts/staging-smoke.mjs";

const BUNDLE = path.resolve("tests/bundle");
const DATABASE = "thenwhat-store-preview";
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-staging-test-"));
const ORIGIN = "https://staging.whatcameofit.com";
let run;
let mf;

/** The built files, as the asset binding serves them: a page at its address, else the 404 page. */
function assets(request) {
  const { pathname } = new URL(request.url);
  const clean = pathname.replace(/\/$/, "") || "/";
  const candidates = clean === "/" ? ["index.html"] : [`${clean.slice(1)}/index.html`, clean.slice(1), `${clean.slice(1)}.html`];
  for (const candidate of candidates) {
    const file = path.join("dist", candidate);
    if (fs.existsSync(file) && fs.statSync(file).isFile()) {
      const type = file.endsWith(".html") ? "text/html; charset=utf-8" : file.endsWith(".json") ? "application/json" : "text/plain";
      return new Response(fs.readFileSync(file), { headers: { "Content-Type": type } });
    }
  }
  return new Response(fs.readFileSync(path.join("dist", "404.html")), { status: 404, headers: { "Content-Type": "text/html; charset=utf-8" } });
}

before(async () => {
  const database = findDeployDatabase(DATABASE, { localState: path.join(scratch, "state") });
  const config = pairsConfig({ base: "wrangler.staging.jsonc", database, scratch, worker: "thenwhat-staging" });
  loadPairsBundle({ config, database, bundle: BUNDLE, local: true, persistTo: database.persistTo });
  run = spawnSync(process.execPath, ["scripts/deploy.mjs", "--staging", "--dry-run"], {
    encoding: "utf8",
    maxBuffer: 256 * 1024 * 1024,
    env: {
      ...process.env,
      SITE_URL: ORIGIN,
      PAIRS_DATABASE: DATABASE,
      PAIRS_LOCAL_STATE: database.persistTo,
      PAIRS_BUNDLE: "",
      BUILD_REVISION: "0123456789abcdef0123456789abcdef01234567",
      ASTRO_TELEMETRY_DISABLED: "1",
      CI: "1",
      WRANGLER_SEND_METRICS: "false",
    },
  });
  assert.equal(run.status, 0, run.stdout.slice(-4000) + run.stderr.slice(-4000));

  // The Worker as Wrangler bundles it, with staging's own variables and the bundle in D1.
  const worker = await bundleWorker({
    entryPoints: ["worker/with-pairs.mjs"],
    bundle: true,
    format: "esm",
    platform: "browser",
    conditions: ["workerd", "worker", "browser"],
    target: "es2022",
    write: false,
  });
  const staging = JSON.parse(fs.readFileSync(config, "utf8"));
  mf = new Miniflare(convertV4MiniflareOptions({
    modules: true,
    script: worker.outputFiles[0].text,
    compatibilityDate: "2026-10-01",
    cf: false,
    bindings: staging.vars,
    d1Databases: ["PAIRS"],
    serviceBindings: { ASSETS: assets },
  }));
  const db = await mf.getD1Database("PAIRS");
  const migration = fs.readFileSync("../store/ingest/migrations/0011_pairs.sql", "utf8")
    .split("\n").filter((line) => !line.trim().startsWith("--")).join("\n")
    .split(/;\s*\n/).map((one) => one.trim()).filter(Boolean);
  for (const sql of migration) await db.prepare(sql).run();
  for (const sql of statements(BUNDLE).sql) await db.prepare(sql).run();
});

after(async () => {
  if (mf) await mf.dispose();
});

test("a staging dry run checks a version of thenwhat-staging with the preview store, and names no domain", () => {
  const { version } = statements(BUNDLE);
  assert.match(run.stdout, new RegExp(`Bundle ${version}, \\d+ pairs, from ${DATABASE} \\(local engine\\)`));
  assert.match(run.stdout, /env\.PAIRS \(thenwhat-store-preview\)/);
  assert.match(run.stdout, /ROBOTS_NOINDEX/);
  assert.match(run.stdout, /Dry run finished\. Nothing was published\..*thenwhat-staging \(staging\.whatcameofit\.com once its domain is attached\)/);
  assert.doesNotMatch(run.stdout + run.stderr, /--domain|Custom domains|workers\.dev/);
  // Every file is marked noindex, and the build says which bundle it was made from.
  assert.match(fs.readFileSync("dist/_headers", "utf8"), /\/\*\n {2}X-Robots-Tag: noindex/);
  assert.equal(fs.readFileSync("dist/bundle-version.txt", "utf8").trim(), version);
});

test("the staging smoke checks pass against the build's Worker, every answer marked noindex", async () => {
  const lines = await checkStaging({
    origin: ORIGIN,
    dist: "dist",
    request: (url) => mf.dispatchFetch(url, { redirect: "manual" }),
    attempts: 1,
  });
  assert.match(lines.at(-1), /Staging passed all 7 checks at https:\/\/staging\.whatcameofit\.com\./);
  for (const status of ["200", "301", "410", "404"]) assert.ok(lines.some((line) => line.includes(` ${status}, noindex`)), status);
});

/** One address of every kind of answer the Worker gives, from the build: a built page passed
 * through from the assets, a page, a listing and a data file made on request, a 301, a 410, a
 * 404, and the error page of a file that fails its check (one is broken in D1 below). A 304
 * joins them once pages carry ETags (openspec pairs-site 4.6, item 5). */
async function everyKind() {
  const { checks } = smokeAddresses("dist");
  const db = await mf.getD1Database("PAIRS");
  const { version } = statements(BUNDLE);
  const pages = JSON.parse(fs.readFileSync("dist/data/pairs.json", "utf8")).entries.filter((entry) => !fs.existsSync(path.join("dist", entry.address, "index.html")));
  const broken = pages.at(-1).address;
  await db.prepare("DELETE FROM pair_page WHERE version = ?1 AND model = 'PairPage' AND key = ?2 AND part > 0").bind(version, broken).run();
  await db.prepare("UPDATE pair_page SET body = '{}' WHERE version = ?1 AND model = 'PairPage' AND key = ?2").bind(version, broken).run();
  // A listing, made on request from the lab's file (worker/listings.mjs).
  const listing = `/intervention/${fs.readdirSync(path.join(BUNDLE, "p12_pair_intervention_page")).sort()[0].slice(0, -5)}`;
  return [...checks, { pathname: listing, status: 200 }, { pathname: `/${broken}`, status: 500 }, { pathname: "/pair-shell", status: 404 }];
}

test("the Worker marks every kind of answer noindex in staging's configuration, and adds none in production's", async () => {
  const kinds = await everyKind();
  assert.deepEqual([...new Set(kinds.map((kind) => kind.status))].sort(), [200, 301, 404, 410, 500]);
  for (const { pathname, status } of kinds) {
    const answer = await mf.dispatchFetch(`${ORIGIN}${pathname}`, { redirect: "manual" });
    assert.equal(answer.status, status, pathname);
    // The asset binding here sets no header of its own: the mark is the Worker's doing.
    assert.equal(answer.headers.get("X-Robots-Tag"), "noindex", `${pathname} (${status})`);
    await answer.body?.cancel();
  }
  // The same Worker without staging's variable, as production's configuration has none.
  await mf.setOptions(convertV4MiniflareOptions({
    modules: true,
    script: (await bundleWorker({ entryPoints: ["worker/with-pairs.mjs"], bundle: true, format: "esm", platform: "browser", conditions: ["workerd", "worker", "browser"], target: "es2022", write: false })).outputFiles[0].text,
    compatibilityDate: "2026-10-01",
    cf: false,
    d1Databases: ["PAIRS"],
    serviceBindings: { ASSETS: assets },
  }));
  assert.equal(JSON.parse(fs.readFileSync("wrangler.jsonc", "utf8").replace(/^\s*\/\/.*$/gm, "")).vars?.ROBOTS_NOINDEX, undefined);
  for (const { pathname, status } of kinds.filter((kind) => kind.status !== 500)) {
    const answer = await mf.dispatchFetch(`${ORIGIN}${pathname}`, { redirect: "manual" });
    assert.equal(answer.headers.get("X-Robots-Tag"), null, `${pathname} (${status})`);
    await answer.body?.cancel();
  }
});

test("a staging address that does not resolve is reported as not answering yet, and fails", async () => {
  // .invalid never resolves (RFC 6761), as staging's own name does not before its domain is attached.
  await assert.rejects(
    checkStaging({ origin: "https://staging.invalid", dist: "dist", attempts: 1 }),
    /staging\.invalid does not answer yet .*attach the custom domain in the dashboard/,
  );
});
