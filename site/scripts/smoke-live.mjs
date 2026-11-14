import assert from "node:assert/strict";
import fs from "node:fs";
import { SITE } from "../site.config.mjs";

const origin = SITE.url;
const expected = JSON.parse(fs.readFileSync(new URL("../data/published-export.json", import.meta.url)));
// A page added in this deploy can answer 404 for a few seconds while the new version
// reaches every Cloudflare location, so each check is tried again before it fails.
const ATTEMPTS = 6;
const WAIT_MS = 10_000;
async function fetchSettled(pathname, ok, options = {}) {
  let response;
  for (let attempt = 1; attempt <= ATTEMPTS; attempt += 1) {
    response = await fetch(`${origin}${pathname}`, { ...options, signal: AbortSignal.timeout(30_000) });
    if (ok(response)) return response;
    if (attempt < ATTEMPTS) await new Promise((done) => setTimeout(done, WAIT_MS));
  }
  return response;
}
for (const pathname of ["/", "/how-it-works", "/privacy", "/sitemap.xml", ...expected.claims.slice(0, 5).map(c => `/${c.slug}`)]) {
  const response = await fetchSettled(pathname, (r) => r.status === 200);
  assert.equal(response.status, 200, `${pathname} returned ${response.status}`);
  console.log(`OK ${pathname}`);
}
const lookup = await fetchSettled("/lookup.json", (r) => r.status === 200);
assert.equal(lookup.status, 200);
const live = await lookup.json();
assert.equal(live.preview, false, "Live site must not be a preview");
assert.equal(live.generated_at, expected.generated_at, "Live export must match the deployed snapshot");
assert.deepEqual(Object.keys(live.claims).sort(), expected.claims.map(claim => claim.slug).sort());
for (const old of expected.retired_verticals ?? []) {
  const response = await fetch(`${origin}/topic/${old.slug}`, { redirect: "manual", signal: AbortSignal.timeout(30_000) });
  assert.equal(response.status, 301, `Retired topic ${old.slug} must redirect`);
  assert.equal(new URL(response.headers.get("location"), origin).pathname, `/topic/${old.successor}`);
}
console.log("OK reviewed snapshot and retired topic redirects");
