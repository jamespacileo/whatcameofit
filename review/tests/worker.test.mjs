// The review Worker as Cloudflare runs it (Miniflare), in front of a local D1 holding migration
// 0011 and the site's test bundle, loaded by the store's own loader. Access's key set is served
// to the Worker from a key made for this run, so the tokens below are signed exactly as Access
// signs them (RS256, `kid`, issuer = team domain, audience = the application's AUD tag) and no
// request leaves the machine.
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import { build } from "esbuild";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";
import { SignJWT, exportJWK, generateKeyPair } from "jose";
import { statements } from "../../store/ingest/scripts/load-pairs.mjs";
import { migrate } from "./store.mjs";

const TEAM = "https://review-test.cloudflareaccess.com";
const AUD = "a".repeat(64);
const OPERATOR = "operator@example.org";
const BUNDLE = "../site/tests/bundle";
const STAGING = "https://staging.review-test";
// What staging's two deploy files answer in these tests: the site's last deploy, recorded.
let servedBundle = null;
const REVISION = "0123456789abcdef0123456789abcdef01234567";

let key;
let jwks;
let script;
const running = [];

async function sign({ email = OPERATOR, audience = AUD, issuer = TEAM, expires = "5m", signer = key.privateKey, kid = "k1" } = {}) {
  const token = new SignJWT({ email, type: "app" })
    .setProtectedHeader({ alg: "RS256", kid })
    .setIssuer(issuer)
    .setAudience(audience)
    .setSubject("operator")
    .setIssuedAt();
  if (expires !== null) token.setExpirationTime(expires);
  return token.sign(signer);
}

async function worker({ bindings = { STAGING_URL: STAGING, ACCESS_ISSUER: TEAM, ACCESS_AUD: AUD, OPERATOR_EMAILS: `Someone@example.org, ${OPERATOR}` }, store = "bundle" } = {}) {
  const mf = new Miniflare(convertV4MiniflareOptions({
    modules: true,
    script,
    compatibilityDate: "2026-10-01",
    bindings,
    d1Databases: store ? ["STAGING_PAIRS"] : [],
    serviceBindings: {
      ASSETS: () => new Response("<!doctype html><title>Content review</title>", { headers: { "Content-Type": "text/html", "Cache-Control": "public, max-age=3600" } }),
    },
    outboundService: (request) => {
      const url = new URL(request.url);
      if (url.origin === TEAM && url.pathname === "/cdn-cgi/access/certs") return Response.json(jwks);
      if (url.origin === STAGING && url.pathname === "/build-revision.txt") return new Response(`${REVISION}\n`);
      if (url.origin === STAGING && url.pathname === "/bundle-version.txt") return servedBundle ? new Response(`${servedBundle}\n`) : new Response("", { status: 404 });
      return new Response("no network in tests", { status: 599 });
    },
  }));
  running.push(mf);
  // "bundle": the pair tables alone, as staging's store began; "full": every migration, as a
  // store that has held claims too. Both hold the tests' bundle.
  if (store === "bundle" || store === "full") {
    const db = await mf.getD1Database("STAGING_PAIRS");
    await migrate(db, store === "bundle" ? { only: ["0011"] } : {});
    for (const sql of statements(BUNDLE).sql) await db.prepare(sql).run();
  }
  return mf;
}

const get = async (mf, pathname, { token, method = "GET" } = {}) =>
  mf.dispatchFetch(`https://review.test${pathname}`, { method, headers: token ? { "Cf-Access-Jwt-Assertion": token } : {} });

let site;

before(async () => {
  key = await generateKeyPair("RS256", { extractable: true });
  jwks = { keys: [{ ...(await exportJWK(key.publicKey)), kid: "k1", alg: "RS256", use: "sig" }] };
  const out = await build({ entryPoints: ["worker/index.mjs"], bundle: true, format: "esm", platform: "browser", conditions: ["workerd", "worker", "browser"], target: "es2022", write: false });
  script = out.outputFiles[0].text;
  site = await worker();
});

after(async () => { for (const mf of running) await mf.dispose(); });

test("a request without an Access token is refused, pages and API alike", async () => {
  for (const pathname of ["/", "/assets/index.js", "/api/me", "/api/staging/overview"]) {
    const response = await get(site, pathname);
    assert.equal(response.status, 403, pathname);
    assert.equal(response.headers.get("Cache-Control"), "private, no-store");
    await response.text();
  }
});

test("a token Access did not sign for this application is refused", async () => {
  const stranger = await generateKeyPair("RS256");
  const cases = {
    "another application": await sign({ audience: "b".repeat(64) }),
    "another team": await sign({ issuer: "https://other.cloudflareaccess.com" }),
    "expired": await sign({ expires: Math.floor(Date.now() / 1000) - 60 }),
    "without an expiry": await sign({ expires: null }),
    "another key": await sign({ signer: stranger.privateKey }),
    "not on the operator list": await sign({ email: "reader@example.org" }),
    "garbled": "not.a.token",
  };
  for (const [why, token] of Object.entries(cases)) {
    const response = await get(site, "/api/me", { token });
    assert.equal(response.status, 403, why);
    await response.text();
  }
});

test("an operator Access signed in reads pages and the API, and nothing is cached publicly", async () => {
  const token = await sign({ email: "Operator@Example.org" });
  const me = await get(site, "/api/me", { token });
  assert.equal(me.status, 200);
  assert.deepEqual(await me.json(), { email: OPERATOR });
  const page = await get(site, "/", { token });
  assert.equal(page.status, 200);
  assert.match(await page.text(), /Content review/);
  assert.equal(page.headers.get("Cache-Control"), "private, no-store");
  assert.equal(page.headers.get("X-Robots-Tag"), "noindex, nofollow");
  assert.equal(page.headers.get("X-Frame-Options"), "DENY");
});

test("the API only reads", async () => {
  const token = await sign();
  for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
    const response = await get(site, "/api/staging/overview", { token, method });
    assert.equal(response.status, 405, method);
    await response.text();
  }
});

test("the staging overview names the current bundle and counts what it holds", async () => {
  const manifest = JSON.parse(fs.readFileSync(`${BUNDLE}/manifest.json`, "utf8"));
  const response = await get(site, "/api/staging/overview", { token: await sign() });
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.environment, "staging");
  assert.equal(body.versions.length, 1);
  assert.equal(body.versions[0].current, true);
  assert.equal(body.current.version, body.versions[0].version);
  // With one version loaded, the rows the loader counted for it are every row of each table.
  const rows = Object.fromEntries(body.tables.map((t) => [t.name, t.rows]));
  for (const [table, count] of Object.entries(body.current.counts)) assert.equal(rows[table], count, table);
  assert.equal(rows.pair_bundle, 1);
  assert.equal(rows.pair, manifest.counts.PairPage);
  assert.ok(rows.pair_page > 0);
});

test("a store without the pair tables is shown as holding none, not as an error", async () => {
  const empty = await worker({ store: "empty" });
  const response = await get(empty, "/api/staging/overview", { token: await sign() });
  assert.equal(response.status, 200);
  const body = await response.json();
  assert.equal(body.current, null);
  assert.ok(body.tables.every((t) => t.rows === null));
});

test("a Worker missing the issuer, the audience or the allowlist answers no one and reads no store", async () => {
  const settings = { ACCESS_ISSUER: TEAM, ACCESS_AUD: AUD, OPERATOR_EMAILS: OPERATOR };
  for (const missing of Object.keys(settings)) {
    const bindings = { ...settings, [missing]: "" };
    const unset = await worker({ bindings });
    for (const pathname of ["/", "/api/me", "/api/staging/overview"]) {
      const response = await get(unset, pathname, { token: await sign() });
      assert.equal(response.status, 503, `${missing} ${pathname}`);
      assert.doesNotMatch(await response.text(), /pair_bundle|version/, missing);
    }
  }
});

test("the overview tells the bundle staging serves apart from the one its store marks current", async () => {
  const token = await sign();
  servedBundle = null;
  let body = await (await get(site, "/api/staging/overview", { token })).json();
  assert.deepEqual(body.published, { host: "staging.review-test", revision: REVISION, bundle: null });
  servedBundle = "f".repeat(16);
  body = await (await get(site, "/api/staging/overview", { token })).json();
  assert.equal(body.published.bundle, servedBundle);
  assert.notEqual(body.published.bundle, body.current.version);
  servedBundle = body.current.version;
  body = await (await get(site, "/api/staging/overview", { token })).json();
  assert.equal(body.published.bundle, body.current.version);
});

// The model inventory (phase 2).

const modelsOf = async (mf) => (await get(mf, "/api/models", { token: await sign() })).json();

test("every model is listed for every environment, with production shown as not readable yet", async () => {
  const body = await modelsOf(site);
  assert.deepEqual(body.environments.map((e) => [e.name, e.readable]), [["staging", true], ["production", false]]);
  assert.match(body.environments[1].reason, /phase 4/);
  for (const model of body.models) {
    assert.ok(model.name, model.id);
    assert.equal(model.environments.production.status, "unavailable", model.id);
    assert.ok(["present", "absent"].includes(model.environments.staging.status), model.id);
  }
  const byId = Object.fromEntries(body.models.map((m) => [m.id, m]));
  // A store of the pair tables alone: the legacy and operational tables are absent, each with
  // the migration that would make it.
  assert.equal(byId.trial_paper.environments.staging.status, "absent");
  assert.match(byId.trial_paper.environments.staging.reason, /0006_trial_papers_and_slices\.sql/);
  assert.equal(byId.trial_slice.migration, "0006_trial_papers_and_slices.sql");
  assert.equal(byId.pair.environments.staging.status, "present");
});

test("page models count the current bundle's files, as its manifest does", async () => {
  const manifest = JSON.parse(fs.readFileSync(`${BUNDLE}/manifest.json`, "utf8"));
  const body = await modelsOf(site);
  for (const model of body.models.filter((m) => m.kind === "page-model")) {
    const state = model.environments.staging;
    assert.equal(state.status, "present", model.model);
    assert.equal(state.rows, manifest.counts[model.model], model.model);
    assert.equal(state.schema, true, model.model);
  }
});

test("a store with every migration holds every table, and an unlisted table is shown", async () => {
  const full = await worker({ store: "full" });
  const db = await full.getD1Database("STAGING_PAIRS");
  await db.prepare("CREATE TABLE something_new (id INTEGER PRIMARY KEY)").run();
  const body = await modelsOf(full);
  for (const model of body.models) assert.equal(model.environments.staging.status, "present", model.id);
  assert.deepEqual(body.environments[0].unlisted, ["something_new"]);
});

test("a table's rows come a page at a time, without the columns that are never shown", async () => {
  const full = await worker({ store: "full" });
  const db = await full.getD1Database("STAGING_PAIRS");
  await db.prepare("INSERT INTO inbox (run_id, kind, key, body) VALUES ('r1', 'claim', 'k1', 'raw words')").run();
  const token = await sign();
  const inbox = await (await get(full, "/api/models/inbox/rows", { token })).json();
  assert.equal(inbox.total, 1);
  assert.deepEqual(inbox.hiddenColumns, ["body"]);
  assert.ok(!inbox.columns.some((c) => c.name === "body"));
  assert.equal(inbox.rows[0].body, undefined);
  assert.equal(inbox.rows[0].key, "k1");
  assert.ok(inbox.columns.find((c) => c.name === "seq").key);

  const pages = await (await get(full, "/api/models/pair_page/rows", { token })).json();
  assert.ok(pages.rows.length > 0 && pages.rows.length <= 50);
  assert.ok(pages.rows.every((row) => row.body === undefined && row.body_chars > 0));
  assert.ok(pages.rows.every((row) => row.version === pages.version));

  const manifest = JSON.parse(fs.readFileSync(`${BUNDLE}/manifest.json`, "utf8"));
  const pairs = await (await get(full, "/api/models/pair/rows", { token })).json();
  assert.equal(pairs.total, manifest.counts.PairPage);
  const second = await (await get(full, "/api/models/pair/rows?offset=10", { token })).json();
  assert.equal(second.offset, 10);
  assert.equal(second.rows.length, manifest.counts.PairPage - 10);

  for (const bad of ["/api/models/pair/rows?offset=-1", "/api/models/pair/rows?offset=1.5", "/api/models/pair/record"]) {
    const response = await get(full, bad, { token });
    assert.equal(response.status, 400, bad);
    await response.text();
  }
  const missing = await get(full, "/api/models/no_such_table/rows", { token });
  assert.equal(missing.status, 404);
  await missing.text();
  const production = await get(full, "/api/models/pair/rows?env=production", { token });
  assert.equal(production.status, 409);
  await production.text();
});

test("a page record shows its file, its schema and the bundle's provenance", async () => {
  const token = await sign();
  const keys = await (await get(site, `/api/models/${encodeURIComponent("page:PairPage")}/rows`, { token })).json();
  const key = keys.rows[0].key;
  const record = await (await get(site, `/api/models/${encodeURIComponent("page:PairPage")}/record?key=${encodeURIComponent(key)}`, { token })).json();
  const file = fs.readdirSync(BUNDLE).find((name) => name.endsWith("_pair_page"));
  assert.deepEqual(record.body, JSON.parse(fs.readFileSync(`${BUNDLE}/${file}/${key}.json`, "utf8")));
  assert.deepEqual(record.schema, JSON.parse(fs.readFileSync(`${BUNDLE}/schemas/PairPage.json`, "utf8")));
  const manifest = JSON.parse(fs.readFileSync(`${BUNDLE}/manifest.json`, "utf8"));
  assert.equal(record.manifest.checksum, manifest.checksum);
  assert.equal(record.manifest.made_at, manifest.made_at);
  assert.equal(record.version, keys.version);
  const none = await get(site, `/api/models/${encodeURIComponent("page:PairPage")}/record?key=nope`, { token });
  assert.equal(none.status, 404);
  await none.text();
});

test("a list and the records opened from it stay on their bundle when another becomes current", async () => {
  const store = await worker({ store: "bundle" });
  const db = await store.getD1Database("STAGING_PAIRS");
  const token = await sign();
  const pages = encodeURIComponent("page:PairPage");
  const list = await (await get(store, `/api/models/${pages}/rows`, { token })).json();
  const old = list.version;
  const key = list.rows[0].key;
  // A second bundle, made current: the same files under another version, one of them changed.
  const next = "f".repeat(16);
  await db.prepare("UPDATE pair_bundle SET current = 0").run();
  await db.prepare("INSERT INTO pair_bundle (version, loaded_at, counts, current) VALUES (?, '2026-11-21T13:00:00Z', '{}', 1)").bind(next).run();
  await db.prepare("INSERT INTO pair_page SELECT ?, model, key, part, body FROM pair_page WHERE version = ?").bind(next, old).run();
  await db.prepare("INSERT INTO pair SELECT ?, key, address, intervention_id, condition_id, status_code, status_as_of, vertical, checked_by_person, trials, claim_slug FROM pair WHERE version = ?").bind(next, old).run();
  await db.prepare("UPDATE pair_page SET body = '{\"changed\":true}' WHERE version = ? AND model = 'PairPage' AND key = ? AND part = 0").bind(next, key).run();
  await db.prepare("DELETE FROM pair_page WHERE version = ? AND model = 'PairPage' AND key = ? AND part > 0").bind(next, key).run();

  const record = await (await get(store, `/api/models/${pages}/record?version=${old}&key=${encodeURIComponent(key)}`, { token })).json();
  assert.equal(record.version, old);
  assert.equal(record.current, false);
  assert.notDeepEqual(record.body, { changed: true });
  const again = await (await get(store, `/api/models/${pages}/rows?version=${old}`, { token })).json();
  assert.equal(again.version, old);
  const pairs = await (await get(store, `/api/models/pair/rows?version=${old}`, { token })).json();
  assert.ok(pairs.rows.every((row) => row.version === old));
  const fresh = await (await get(store, `/api/models/${pages}/record?key=${encodeURIComponent(key)}`, { token })).json();
  assert.equal(fresh.version, next);
  assert.deepEqual(fresh.body, { changed: true });

  // The old bundle dropped: what was bound to it says so, and never answers from the new one.
  for (const table of ["pair_page", "pair", "pair_intervention", "pair_intervention_name", "pair_condition", "pair_trial", "pair_trial_facts", "pair_status_change", "pair_bundle"]) await db.prepare(`DELETE FROM ${table} WHERE version = ?`).bind(old).run();
  for (const pathname of [
    `/api/models/${pages}/record?version=${old}&key=${encodeURIComponent(key)}`,
    `/api/models/${pages}/rows?version=${old}`,
    `/api/models/pair/rows?version=${old}`,
    `/api/models/pair/record?key=${encodeURIComponent(JSON.stringify([old, pairs.rows[0].key]))}`,
  ]) {
    const response = await get(store, pathname, { token });
    assert.equal(response.status, 410, pathname);
    assert.deepEqual(await response.json(), { error: "version gone", version: old });
  }
  const bad = await get(store, `/api/models/${pages}/rows?version=nope`, { token });
  assert.equal(bad.status, 400);
  await bad.text();
});

test("records are paged in primary-key order and one is addressed by its key", async () => {
  const full = await worker({ store: "full" });
  const db = await full.getD1Database("STAGING_PAIRS");
  // Inserted out of key order.
  for (const step of ["zeta", "alpha", "mid"]) await db.prepare("INSERT INTO store_step (step, version) VALUES (?, 1)").bind(step).run();
  const token = await sign();
  const steps = await (await get(full, "/api/models/store_step/rows", { token })).json();
  assert.deepEqual(steps.rows.map((row) => row.step), ["alpha", "mid", "zeta"]);
  assert.deepEqual(steps.key, ["step"]);
  const pairs = await (await get(full, "/api/models/pair/rows", { token })).json();
  const keys = pairs.rows.map((row) => row.key);
  assert.deepEqual(keys, [...keys].sort());
  const one = await (await get(full, `/api/models/pair/record?key=${encodeURIComponent(JSON.stringify([pairs.version, keys[3]]))}`, { token })).json();
  assert.equal(one.row.key, keys[3]);
  assert.equal(one.version, pairs.version);
  assert.deepEqual(one.key, ["version", "key"]);
  for (const key of ["[1]", "not json", JSON.stringify([pairs.version, { a: 1 }])]) {
    const response = await get(full, `/api/models/pair/record?key=${encodeURIComponent(key)}`, { token });
    assert.equal(response.status, 400, key);
    await response.text();
  }
  await db.prepare("INSERT INTO inbox (run_id, kind, key, body) VALUES ('r1', 'claim', 'k1', 'raw words')").run();
  const inbox = await (await get(full, `/api/models/inbox/record?key=${encodeURIComponent("[1]")}`, { token })).json();
  assert.equal(inbox.row.body, undefined);
  assert.equal(inbox.row.key, "k1");
});
