// Staging, rehearsed on this machine (docs/deploy.md, "Staging"): the small bundle loaded into the
// preview store's name on D1's local engine, deploy.mjs --staging in dry-run mode builds from it
// and has Wrangler check a version of thenwhat-staging, then the staging smoke checks run against
// that build's Worker in workerd (Miniflare) with staging's configuration. Nothing is sent to
// Cloudflare. A host that does not resolve is reported as not answering yet, never as a pass.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { build as bundleWorker } from "esbuild";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
import { statements } from "../../store/ingest/scripts/load-pairs.mjs";
import { findDeployDatabase } from "../scripts/pairs-deploy.mjs";
import { WORKER_FIRST, limitProblems, loadPairsBundle, pairsConfig } from "../scripts/pairs-preview.mjs";
import { checkStaging, smokeAddresses } from "../scripts/staging-smoke.mjs";

const BUNDLE = path.resolve("tests/bundle");
const DATABASE = "thenwhat-store-preview";
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-staging-test-"));
const ORIGIN = "https://staging.whatcameofit.com";
const REVISION = "0123456789abcdef0123456789abcdef01234567";
let run;
let mf;
// The Worker's options in staging's configuration, its rate limit among them.
let stagingOptions;
// The configuration pairsConfig gives staging, as deploy.mjs --staging is given it.
let stagingConfig;

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
  stagingConfig = config;
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
      BUILD_REVISION: REVISION,
      // Set as an operator's shell might have them: staging still offers no search, and the
      // trial reader is given its contact address.
      CONTACT_EMAIL: "registry-contact@example.org",
      LLM_MODEL: "a-model",
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
  stagingOptions = {
    modules: true,
    script: worker.outputFiles[0].text,
    compatibilityDate: "2026-10-01",
    cf: false,
    bindings: staging.vars,
    d1Databases: ["PAIRS"],
    ratelimits: Object.fromEntries(staging.ratelimits.map(({ name, namespace_id, simple }) => [name, { namespace_id, simple }])),
    serviceBindings: { ASSETS: assets },
  };
  mf = new Miniflare(convertV4MiniflareOptions(stagingOptions));
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

test("staging's configuration runs the Worker first only where pairsConfig says, with the rate limit in staging's namespace", () => {
  const staging = JSON.parse(fs.readFileSync(stagingConfig, "utf8"));
  assert.equal(staging.name, "thenwhat-staging");
  assert.deepEqual(staging.assets.run_worker_first, WORKER_FIRST);
  assert.equal(staging.assets.not_found_handling, "none");
  assert.deepEqual(limitProblems(stagingConfig), []);
});

test("a staging dry run checks a version of thenwhat-staging with the preview store, and names no domain", () => {
  const { version } = statements(BUNDLE);
  assert.match(run.stdout, new RegExp(`Bundle ${version}, \\d+ pairs, from ${DATABASE} \\(local engine\\)`));
  assert.match(run.stdout, /env\.PAIRS \(thenwhat-store-preview\)/);
  assert.match(run.stdout, /ROBOTS_NOINDEX/);
  assert.match(run.stdout, /Dry run finished\. Nothing was published\..*thenwhat-staging \(staging\.whatcameofit\.com once its domain is attached\)/);
  assert.doesNotMatch(run.stdout + run.stderr, /--domain|Custom domains|workers\.dev/);
  // Every file is marked noindex inside the one rule for "/*", which keeps its security headers:
  // a second "/*" rule would replace the first.
  const headers = fs.readFileSync("dist/_headers", "utf8").split("\n");
  assert.equal(headers.filter((line) => line.trim() === "/*").length, 1);
  const rule = headers.slice(headers.indexOf("/*") + 1, headers.findIndex((line, at) => at > headers.indexOf("/*") && !/^\s+\S/.test(line)));
  for (const name of ["X-Content-Type-Options", "Referrer-Policy", "Strict-Transport-Security", "X-Robots-Tag"]) {
    assert.ok(rule.some((line) => line.trim().startsWith(`${name}:`)), name);
  }
  assert.match(run.stdout, /CONTACT_EMAIL/);
  assert.match(run.stdout, /Without the registry search: staging has no saved-results namespace and no model key\./);
  assert.ok(!JSON.parse(fs.readFileSync("dist/lookup.json", "utf8")).live, "the build offers no search");
  // The build says which bundle and which commit it was made from.
  assert.equal(fs.readFileSync("dist/build-revision.txt", "utf8").trim(), REVISION);
  assert.equal(fs.readFileSync("dist/bundle-version.txt", "utf8").trim(), version);
});

test("the staging smoke checks pass against the build's Worker, every answer marked noindex", async () => {
  const lines = await checkStaging({
    origin: ORIGIN,
    dist: "dist",
    revision: REVISION,
    request: (url) => mf.dispatchFetch(url, { redirect: "manual" }),
    attempts: 1,
  });
  assert.match(lines[0], new RegExp(`OK /build-revision.txt names commit ${REVISION}`));
  assert.match(lines.at(-1), /Staging passed all 8 checks at https:\/\/staging\.whatcameofit\.com\./);
  for (const status of ["200", "301", "410", "404"]) assert.ok(lines.some((line) => line.includes(` ${status}, noindex`)), status);
});

test("staging answering for another commit fails the smoke checks, after its attempts", async () => {
  // As the version before would answer while a deployment of new code with the same bundle spreads.
  const other = "f".repeat(40);
  await assert.rejects(
    checkStaging({ origin: ORIGIN, dist: "dist", revision: other, request: (url) => mf.dispatchFetch(url, { redirect: "manual" }), attempts: 2, waitMs: 10 }),
    /Staging failed 1 of 8 checks/,
  );
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
  // A saved alias of a pair's address leads to it (301).
  const alias = `/${pages[0].address}/`;
  return [...checks, { pathname: listing, status: 200 }, { pathname: alias, status: 301 }, { pathname: `/${broken}`, status: 500 }, { pathname: "/pair-shell", status: 404 }];
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
  // A not-found answer kept for a missing pair, asked for again, and a 304 to an asker who holds
  // a page: both the Worker's, both marked.
  const missing = "/no-such--pair";
  for (let at = 0; at < 2; at += 1) {
    const answer = await mf.dispatchFetch(`${ORIGIN}${missing}`, { redirect: "manual" });
    assert.equal(answer.status, 404);
    assert.equal(answer.headers.get("X-Robots-Tag"), "noindex", `${missing}, asked ${at + 1}`);
    await answer.body?.cancel();
  }
  const page = kinds.find((kind) => kind.status === 200 && /^\/[a-z0-9-]+--[a-z0-9-]+$/.test(kind.pathname)).pathname;
  const full = await mf.dispatchFetch(`${ORIGIN}${page}`);
  const tag = full.headers.get("ETag");
  await full.body?.cancel();
  const held = await mf.dispatchFetch(`${ORIGIN}${page}`, { headers: { "If-None-Match": tag } });
  assert.equal(held.status, 304);
  assert.equal(held.headers.get("X-Robots-Tag"), "noindex", `${page} (304)`);
  // A method other than GET or HEAD at an address no file has: the Worker's 405, marked too.
  const posted = await mf.dispatchFetch(`${ORIGIN}${missing}`, { method: "POST", redirect: "manual" });
  assert.equal(posted.status, 405);
  assert.equal(posted.headers.get("X-Robots-Tag"), "noindex", `${missing} (405)`);
  await posted.body?.cancel();
  // Past the rate limit, 429: staging's binding at a limit of one, so the second request is over.
  assert.equal(stagingOptions.ratelimits.ON_REQUEST_LIMIT?.namespace_id, "4132");
  await mf.setOptions(convertV4MiniflareOptions({ ...stagingOptions, ratelimits: { ON_REQUEST_LIMIT: { namespace_id: "4132", simple: { limit: 1, period: 60 } } } }));
  // Miniflare counts in fixed minutes of the clock: two requests that cross one are asked again.
  let refused;
  for (let attempt = 1; ; attempt += 1) {
    const window = Math.floor(Date.now() / 60_000);
    const asker = { headers: { "CF-Connecting-IP": `192.0.2.${attempt}` }, redirect: "manual" };
    await (await mf.dispatchFetch(`${ORIGIN}${page}`, asker)).body?.cancel();
    refused = await mf.dispatchFetch(`${ORIGIN}${page}`, asker);
    if (Math.floor(Date.now() / 60_000) === window) break;
    await refused.body?.cancel();
    assert.ok(attempt < 3, "the limiter's window kept changing");
  }
  assert.equal(refused.status, 429);
  assert.equal(refused.headers.get("Retry-After"), "60");
  assert.equal(refused.headers.get("X-Robots-Tag"), "noindex", `${page} (429)`);
  await refused.body?.cancel();
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

test("a staging address that does not answer is reported as not answering yet, and fails", async () => {
  // A port of this machine that was just let go: the connection is refused here, with no
  // network, as staging's own name answers nothing before its domain is attached.
  const server = net.createServer();
  await new Promise((done) => server.listen(0, "127.0.0.1", done));
  const { port } = server.address();
  await new Promise((done) => server.close(done));
  await assert.rejects(
    checkStaging({ origin: `http://127.0.0.1:${port}`, dist: "dist", revision: REVISION, attempts: 1 }),
    /127\.0\.0\.1 does not answer yet \(ECONNREFUSED\): attach the custom domain in the dashboard/,
  );
});
