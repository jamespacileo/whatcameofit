// Where the Worker runs before the files (openspec pairs-site task 4.6d), in the asset routing
// Cloudflare runs, through `wrangler dev` on the configuration a deployment with pairs is given
// (scripts/pairs-preview.mjs, pairsConfig). The site is built from the small bundle and the
// bundle loaded into D1's local engine, so a page only the Worker can make shows it was asked.
// It builds into a folder of its own, leaving site/dist as it was, and runs offline: nothing is
// sent to Cloudflare, nor asked of it or of the npm registry.
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import fs from "node:fs";
import net from "node:net";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { setTimeout as wait } from "node:timers/promises";
import { findDeployDatabase } from "../scripts/pairs-deploy.mjs";
import { WORKER_FIRST, loadPairsBundle, pairsConfig } from "../scripts/pairs-preview.mjs";
import { readBundle } from "../src/lib/bundle.ts";

const BUNDLE = path.resolve("tests/bundle");
const scratch = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-worker-first-"));
const dist = path.join(scratch, "dist");
// Wrangler and Miniflare ask the network for nothing: no metrics, no update check, no request
// metadata from workers.cloudflare.com.
const OFFLINE = { CI: "1", WRANGLER_SEND_METRICS: "false", WRANGLER_HIDE_BANNER: "true", CLOUDFLARE_CF_FETCH_ENABLED: "false" };
Object.assign(process.env, OFFLINE);
const pages = readBundle(BUNDLE).pages.PairPage;
const PAIR = "acoziborole--trypanosomiasis";
let origin;
let server;
let config;

before(async () => {
  const env = { ...process.env, PAIRS_BUNDLE: BUNDLE, ASTRO_TELEMETRY_DISABLED: "1" };
  const built = spawnSync("npx", ["astro", "build", "--outDir", dist], { encoding: "utf8", env });
  assert.equal(built.status, 0, built.stdout.slice(-3000) + built.stderr.slice(-3000));
  const redirects = spawnSync(process.execPath, ["scripts/redirects.mjs"], { encoding: "utf8", env: { ...env, DIST_DIR: dist } });
  assert.equal(redirects.status, 0, redirects.stdout + redirects.stderr);
  const database = findDeployDatabase("thenwhat-worker-first-preview", { localState: path.join(scratch, "d1") });
  config = pairsConfig({ base: "wrangler.preview.jsonc", database, scratch });
  // The assets are this test's build, not site/dist.
  const written = JSON.parse(fs.readFileSync(config, "utf8"));
  written.assets.directory = dist;
  fs.writeFileSync(config, JSON.stringify(written));
  loadPairsBundle({ config, database, bundle: BUNDLE, local: true, persistTo: database.persistTo });
  const free = net.createServer();
  await new Promise((done) => free.listen(0, "127.0.0.1", done));
  const { port } = free.address();
  await new Promise((done) => free.close(done));
  origin = `http://127.0.0.1:${port}`;
  server = spawn(process.execPath, ["node_modules/wrangler/bin/wrangler.js", "dev", "--config", config, "--local", "--persist-to", database.persistTo,
    "--ip", "127.0.0.1", "--port", String(port)], { env: { ...process.env, ...OFFLINE }, stdio: "ignore" });
  for (let attempt = 0; attempt < 120; attempt += 1) {
    if (await fetch(origin).then(() => true, () => false)) return;
    await wait(500);
  }
  throw new Error("wrangler dev did not answer");
});

after(() => {
  server?.kill();
  fs.rmSync(scratch, { recursive: true, force: true });
});

const ask = (pathname) => fetch(`${origin}${pathname}`, { redirect: "manual" });

/** Whether a path runs the Worker first, by Cloudflare's rule: `*` matches across "/", and a
 * "!" pattern wins over the others. */
const runsFirst = (pathname) => {
  const matches = (pattern) => (pattern.endsWith("*") ? pathname.startsWith(pattern.slice(0, -1)) : pathname === pattern);
  return WORKER_FIRST.some((one) => !one.startsWith("!") && matches(one)) && !WORKER_FIRST.some((one) => one.startsWith("!") && matches(one.slice(1)));
};

test("the configuration a deployment with pairs is given runs the Worker first only where a file must not answer", () => {
  const assets = JSON.parse(fs.readFileSync(config, "utf8")).assets;
  assert.deepEqual(assets.run_worker_first, WORKER_FIRST);
  // An address no file has reaches the Worker; with "404-page" the files would answer it.
  assert.equal(assets.not_found_handling, "none");
  assert.ok(WORKER_FIRST.length <= 100, "Cloudflare takes at most 100 patterns");
  // Every file of the build is served without the Worker but the frames and the reader's template.
  const files = fs.readdirSync(dist, { recursive: true }).filter((name) => fs.statSync(path.join(dist, name)).isFile());
  const first = files.map((name) => `/${name.split(path.sep).join("/").replace(/(\/?index)?\.html$/, "")}`).filter(runsFirst);
  assert.deepEqual([...new Set(first)].sort(), ["/embed-shell", "/pair-shell", "/trial-reader"]);
});

test("a page or file of the site is served as the file", async () => {
  const condition = Object.values(pages)[0].row.condition.slug;
  for (const pathname of ["/", "/about", "/topics", "/clinical", `/condition/${condition}`, "/data/pairs.json", "/lookup.json", "/sitemap.xml", "/how-it-works"]) {
    const response = await ask(pathname);
    assert.equal(response.status, 200, pathname);
    assert.equal(await response.text(), fs.readFileSync(path.join(dist, pathname === "/" ? "index.html" : fs.existsSync(path.join(dist, `${pathname.slice(1)}.html`)) ? `${pathname.slice(1)}.html` : fs.existsSync(path.join(dist, pathname.slice(1), "index.html")) ? path.join(pathname.slice(1), "index.html") : pathname.slice(1)), "utf8"), pathname);
  }
});

test("every address the Worker makes or guards reaches it, a file of that address or not", async () => {
  // Made only by the Worker, from D1: a pair's page, and the 301 of a saved alias.
  for (const [pathname, status] of [
    [`/${PAIR}`, 200],
    [`/data/pairs/${PAIR}.json`, 200],
    [`/embed/${PAIR}`, 200],
    [`/oembed/${PAIR}.json`, 200],
    [`/og/${PAIR}.png`, 200],
    ["/intervention/acoziborole", 200],
    ["/topic/infections", 200],
    [`/${PAIR}/`, 301],
    ["/no-such--pair", 404],
    ["/pair-shell", 404],
    ["/embed-shell", 404],
    ["/trial-reader", 404],
    ["/api/lookup", 405],
    ["/data/claims.json", 410],
  ]) {
    const response = await ask(pathname);
    assert.equal(response.status, status, pathname);
    await response.body?.cancel();
    await response.body?.cancel();
  }
});

test("an old claim's address still leads to its pair (301) or answers gone (410)", async () => {
  const gone = JSON.parse(fs.readFileSync(path.join(dist, "gone.json"), "utf8"));
  const moved = gone.find((entry) => entry.to);
  const removed = gone.find((entry) => entry.gone || entry.on);
  assert.ok(moved && removed, "the build has an old claim of each kind");
  const led = await ask(`/${moved.slug}`);
  assert.equal(led.status, 301);
  assert.equal(new URL(led.headers.get("Location")).pathname, `/${moved.to}`);
  assert.equal((await ask(`/${removed.slug}`)).status, 410);
  // Its old files too, which no file of the build answers any more.
  assert.equal((await ask(`/embed/${moved.slug}`)).status, 301);
  assert.equal((await ask(`/data/claims/${removed.slug}.json`)).status, 410);
});

test("an address no file or pair has gets the site's not-found page, from the Worker", async () => {
  const page = fs.readFileSync(path.join(dist, "404.html"), "utf8");
  for (const pathname of ["/no-such--pair", "/no-such-page", "/guide/no-such-entry", "/pair-shell", "/_astro/no-such-file.css"]) {
    const response = await ask(pathname);
    assert.equal(response.status, 404, pathname);
    assert.match(response.headers.get("Content-Type"), /text\/html/, pathname);
    assert.equal(await response.text(), page, pathname);
  }
  // A missing page is asked about again before it is reused, so it is never kept once it appears;
  // a confirmed miss of a pair's address is kept five minutes.
  assert.match((await ask("/no-such-page")).headers.get("Cache-Control"), /max-age=0|no-cache|must-revalidate/);
  assert.equal((await ask("/no-such--pair")).headers.get("Cache-Control"), "public, max-age=300");
});

test("an address the Worker makes answers GET and HEAD only, as a file does", async () => {
  for (const [method, pathname] of [["POST", `/${PAIR}`], ["OPTIONS", `/data/pairs/${PAIR}.json`], ["PUT", "/intervention/acoziborole"], ["DELETE", "/no-such--pair"]]) {
    const response = await fetch(`${origin}${pathname}`, { method, redirect: "manual" });
    assert.equal(response.status, 405, `${method} ${pathname}`);
    assert.equal(response.headers.get("Allow"), "GET, HEAD");
    await response.body?.cancel();
  }
  assert.equal((await fetch(`${origin}/${PAIR}`, { method: "HEAD" })).status, 200);
  // The registry search still takes its POST (here unconfigured, so it says so).
  assert.notEqual((await fetch(`${origin}/api/lookup`, { method: "POST", body: "{}" })).status, 405);
});
