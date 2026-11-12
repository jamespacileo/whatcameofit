import assert from "node:assert/strict";
import fs from "node:fs";
const origin = process.env.SITE_URL || "https://whatcameofit.com";
const expected = JSON.parse(fs.readFileSync(new URL("../data/published-export.json", import.meta.url)));
for (const pathname of ["/", "/how-it-works", "/sitemap.xml", ...expected.claims.slice(0, 5).map(c => `/${c.slug}`)]) {
  const response = await fetch(`${origin}${pathname}`, { signal: AbortSignal.timeout(30_000) });
  assert.equal(response.status, 200, `${pathname} returned ${response.status}`);
  console.log(`OK ${pathname}`);
}
const lookup = await fetch(`${origin}/lookup.json`, { signal: AbortSignal.timeout(30_000) });
assert.equal(lookup.status, 200);
assert.equal((await lookup.json()).preview, false, "Live site must not be a preview");
