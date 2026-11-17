// The headers Cloudflare sends with the site's files (site/public/_headers). A rule in
// that file is matched by the address alone: it is sent with the "not found" page too
// when a file of that address is missing, as one is for a moment while a deploy is
// reaching every location. So no rule may tell a browser to keep an answer without
// asking again: a kept 404 for a stylesheet leaves the site unstyled for that reader.
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";

const text = fs.readFileSync(new URL("../public/_headers", import.meta.url), "utf8");

/** Each rule as its address pattern and its headers, in file order. */
function rules(source) {
  const found = [];
  for (const line of source.split("\n")) {
    if (!line.trim() || line.startsWith("#")) continue;
    if (!/^\s/.test(line)) found.push({ pattern: line.trim(), headers: [] });
    else {
      const at = line.indexOf(":");
      found.at(-1).headers.push([line.slice(0, at).trim().toLowerCase(), line.slice(at + 1).trim()]);
    }
  }
  return found;
}

const cacheRules = rules(text).flatMap(({ pattern, headers }) =>
  headers.filter(([name]) => name === "cache-control").map(([, value]) => ({ pattern, value })),
);

test("the file is read as rules", () => {
  assert.deepEqual(
    rules("# note\n/a/*\n  X-One: 1\n  Cache-Control: public, max-age=0\n\n/b\n  X-Two: a: b\n"),
    [
      { pattern: "/a/*", headers: [["x-one", "1"], ["cache-control", "public, max-age=0"]] },
      { pattern: "/b", headers: [["x-two", "a: b"]] },
    ],
  );
});

test("no rule lets a browser keep an answer without asking again", () => {
  for (const { pattern, value } of cacheRules) {
    assert.doesNotMatch(value, /\bimmutable\b/, `${pattern}: "immutable" would be sent with a 404 too`);
    const age = Number(value.match(/(?:^|[\s,])max-age=(\d+)/)?.[1]);
    assert.ok(Number.isFinite(age), `${pattern}: says how long its answer is fresh`);
    // Five minutes at most: a wrong answer kept by a browser is replaced soon.
    assert.ok(age <= 300, `${pattern}: max-age=${age} would keep a 404 that long`);
    assert.doesNotMatch(value, /\bs-maxage=(?!0\b)\d+/, `${pattern}: a shared cache would keep a 404`);
  }
});

test("built files are used at once and checked behind the page", () => {
  const built = cacheRules.filter(({ pattern }) => pattern === "/_astro/*");
  assert.equal(built.length, 1);
  assert.equal(built[0].value, "public, max-age=0, stale-while-revalidate=31536000");
});
