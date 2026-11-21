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

const TEAM = "https://review-test.cloudflareaccess.com";
const AUD = "a".repeat(64);
const OPERATOR = "operator@example.org";
const BUNDLE = "../site/tests/bundle";

let key;
let jwks;
let script;
const running = [];

async function sign({ email = OPERATOR, audience = AUD, issuer = TEAM, expires = "5m", signer = key.privateKey, kid = "k1" } = {}) {
  return new SignJWT({ email, type: "app" })
    .setProtectedHeader({ alg: "RS256", kid })
    .setIssuer(issuer)
    .setAudience(audience)
    .setSubject("operator")
    .setIssuedAt()
    .setExpirationTime(expires)
    .sign(signer);
}

/** Migration 0011, one statement at a time, as D1 applies it. */
function migration() {
  return fs.readFileSync("../store/ingest/migrations/0011_pairs.sql", "utf8")
    .split("\n")
    .filter((line) => !line.trim().startsWith("--"))
    .join("\n")
    .split(/;\s*\n/)
    .map((one) => one.trim())
    .filter(Boolean);
}

async function worker({ bindings = { ACCESS_ISSUER: TEAM, ACCESS_AUD: AUD, OPERATOR_EMAILS: `Someone@example.org, ${OPERATOR}` }, store = "bundle" } = {}) {
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
      return new Response("no network in tests", { status: 599 });
    },
  }));
  running.push(mf);
  if (store === "bundle") {
    const db = await mf.getD1Database("STAGING_PAIRS");
    for (const sql of migration()) await db.prepare(sql).run();
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
