import assert from "node:assert/strict";
import { test } from "node:test";
import { checkLive } from "../scripts/smoke-live.mjs";

const revision = "a".repeat(40);
const expected = { generated_at: "2026-11-17", claims: [{ slug: "one-trial" }] };
const stylesheet = "/_astro/global.abc.css";
const options = { origin: "https://example.org", revision, expected, attempts: 3, waitMs: 0 };

function answer(pathname) {
  switch (pathname) {
    case "/build-revision.txt": return new Response(revision);
    case "/": return new Response(`<link rel="stylesheet" href="${stylesheet}">`);
    case stylesheet: return new Response("body {}", { headers: { "Content-Type": "text/css" } });
    case "/api/lookup": return Response.json({ error: "method" }, { status: 405 });
    case "/lookup.json": return Response.json({
      preview: false,
      generated_at: expected.generated_at,
      claims: { "one-trial": {} },
    });
    default: return new Response("Page");
  }
}

test("production smoke retries a timeout and a stale 200 before accepting the expected release", async () => {
  let revisionRequests = 0;
  let snapshotRequests = 0;
  await checkLive({
    ...options,
    request: async ({ pathname }) => {
      if (pathname === "/build-revision.txt") {
        revisionRequests += 1;
        if (revisionRequests === 1) throw new DOMException("Timed out", "TimeoutError");
        if (revisionRequests === 2) return new Response("b".repeat(40));
      }
      if (pathname === "/lookup.json" && ++snapshotRequests === 1) {
        return Response.json({ preview: false, generated_at: "2026-11-16", claims: { "one-trial": {} } });
      }
      return answer(pathname);
    },
  });
  assert.equal(revisionRequests, 3);
  assert.equal(snapshotRequests, 2);
});

test("production smoke rejects an older release even if it serves the same snapshot", async () => {
  await assert.rejects(
    checkLive({
      ...options,
      request: async ({ pathname }) => {
        assert.equal(pathname, "/build-revision.txt");
        return new Response("b".repeat(40));
      },
    }),
    /build-revision.*failed after 3 attempts: Live build must match/,
  );
});

test("production smoke rejects an HTML fallback at the stylesheet URL", async () => {
  await assert.rejects(
    checkLive({
      ...options,
      request: async ({ pathname }) => pathname === stylesheet ? new Response("<html>Fallback</html>") : answer(pathname),
    }),
    /_astro\/global\.abc\.css failed after 3 attempts/,
  );
});
