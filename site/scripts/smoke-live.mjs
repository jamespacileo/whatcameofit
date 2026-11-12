import assert from "node:assert/strict";
import fs from "node:fs";
const origin = process.env.SITE_URL || "https://whatcameofit.com";
const expected = JSON.parse(fs.readFileSync(new URL("../data/published-export.json", import.meta.url)));
for (const pathname of ["/", "/how-it-works", "/privacy", "/sitemap.xml", ...expected.claims.slice(0, 5).map(c => `/${c.slug}`)]) {
  const response = await fetch(`${origin}${pathname}`, { signal: AbortSignal.timeout(30_000) });
  assert.equal(response.status, 200, `${pathname} returned ${response.status}`);
  console.log(`OK ${pathname}`);
}
const lookup = await fetch(`${origin}/lookup.json`, { signal: AbortSignal.timeout(30_000) });
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
