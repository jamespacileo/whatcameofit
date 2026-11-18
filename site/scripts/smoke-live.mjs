import assert from "node:assert/strict";
import fs from "node:fs";
import { setTimeout as wait } from "node:timers/promises";
import { SITE } from "../site.config.mjs";

export async function checkLive({ origin, expected, revision, request = fetch, attempts = 6, waitMs = 10_000 }) {
  async function check(pathname, status, verify = () => {}) {
    let failure;
    for (let attempt = 1; attempt <= attempts; attempt += 1) {
      let response;
      try {
        response = await request(new URL(pathname, origin), {
          cache: "no-store",
          redirect: "manual",
          signal: AbortSignal.timeout(10_000),
        });
        assert.equal(response.status, status);
        const result = await verify(response);
        console.log(`OK ${pathname}`);
        return result;
      } catch (error) {
        failure = error;
      } finally {
        if (response?.body && !response.bodyUsed) await response.body.cancel().catch(() => {});
      }
      if (attempt < attempts) await wait(waitMs);
    }
    throw new Error(`${pathname} failed after ${attempts} attempts: ${failure.message}`, { cause: failure });
  }

  // At the start of propagation, a previous version can still return HTTP 200.
  if (revision) {
    await check(`/build-revision.txt?rev=${revision}`, 200, async (response) => {
      assert.equal((await response.text()).trim(), revision, "Live build must match the deployed commit");
    });
  }

  const stylesheet = await check("/", 200, async (response) => {
    const html = await response.text();
    const link = html.match(/\bhref=["'](\/_astro\/[^"']+\.css)["']/);
    assert.ok(link, "Home page must link a built stylesheet");
    return link[1];
  });
  await check(stylesheet, 200, (response) => {
    assert.match(response.headers.get("content-type") ?? "", /^text\/css\b/);
  });
  for (const pathname of ["/how-it-works", "/privacy", "/sitemap.xml", ...expected.claims.slice(0, 5).map(c => `/${c.slug}`)]) {
    await check(pathname, 200);
  }
  await check("/api/lookup", 405, async (response) => {
    // A GET reaches the Worker and is rejected before any model or registry call.
    assert.equal((await response.json()).error, "method");
  });
  await check("/lookup.json", 200, async (response) => {
    const live = await response.json();
    assert.equal(live.preview, false, "Live site must serve a public build");
    assert.equal(live.generated_at, expected.generated_at, "Live export must match the deployed snapshot");
    assert.deepEqual(Object.keys(live.claims).sort(), expected.claims.map(claim => claim.slug).sort());
  });
  for (const old of expected.retired_verticals ?? []) {
    await check(`/topic/${old.slug}`, 301, (response) => {
      const destination = new URL(response.headers.get("location"), origin);
      assert.equal(destination.href, new URL(`/topic/${old.successor}`, origin).href);
    });
  }
}

if (import.meta.main) {
  const expected = JSON.parse(fs.readFileSync(new URL("../data/published-export.json", import.meta.url)));
  await checkLive({ origin: SITE.url, expected, revision: process.env.BUILD_REVISION });
}
