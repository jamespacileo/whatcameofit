// The lookup file as the extension asks for and reads it: version 2 first, version 1 where
// a site has not built version 2, and a copy saved before either is read the same way.
import assert from "node:assert/strict";
import { test } from "node:test";
import { INDEX_PATHS, fetchIndex, readIndex } from "../src/index-file.js";

const site = "https://whatcameofit.example";
const v2 = {
  format: "lookup", format_version: 2, articles: { "news.example.org/story": ["ex1--tinnitus"] },
  meanings: { "Phase 1 trial": "A first trial in people." }, unchecked_note: "Not yet checked by a person.",
  pairs: { "ex1--tinnitus": { title: "EX-1 for tinnitus", status: "Phase 1 trial", unchecked: true, names: ["EX-1"], condition: "Tinnitus" } },
};
const v1 = {
  schema_version: 1, articles: { "news.example.org/story": ["ex1--tinnitus"] },
  claims: { "ex1--tinnitus": { headline: "EX-1 for tinnitus", page: "/ex1--tinnitus", status: "Phase 1 trial", meaning: "A first trial in people.", unchecked: "Not yet checked by a person.", names: ["EX-1"], indication: "Tinnitus" } },
};

test("both versions read as the same pair, with the popup's own words", () => {
  const two = readIndex(v2).pairs["ex1--tinnitus"];
  const one = readIndex(v1).pairs["ex1--tinnitus"];
  for (const key of ["headline", "page", "status", "meaning", "unchecked", "names", "indication"]) assert.deepEqual(two[key], one[key], key);
  assert.deepEqual(readIndex(v2).articles, v1.articles);
  assert.equal(readIndex(null), null);
});

test("version 2 is asked for first, and version 1 only when the site has no version 2", async () => {
  const asked = [];
  const only = (answers) => async (url) => { asked.push(url); return answers[new URL(url).pathname]; };
  const found = await fetchIndex(only({ "/lookup/2.json": Response.json(v2, { headers: { ETag: '"two"' } }) }), site);
  assert.deepEqual([found.path, found.etag, found.file], ["/lookup/2.json", '"two"', v2]);
  assert.deepEqual(asked, [`${site}/lookup/2.json`]);
  asked.length = 0;
  const older = await fetchIndex(only({ "/lookup/2.json": new Response(null, { status: 404 }), "/lookup.json": Response.json(v1) }), site);
  assert.deepEqual([older.path, older.file], ["/lookup.json", v1]);
  assert.deepEqual(asked, INDEX_PATHS.map((path) => `${site}${path}`));
  // Any other failure is not a reason to read version 1.
  await assert.rejects(fetchIndex(only({ "/lookup/2.json": new Response(null, { status: 503 }) }), site), /status 503/);
});

test("a saved ETag is sent only to the address it came from, and a 304 keeps the saved file", async () => {
  const sent = [];
  const fetch = async (url, options) => { sent.push([new URL(url).pathname, options.headers?.["If-None-Match"] ?? null]); return new Response(null, { status: 304 }); };
  const found = await fetchIndex(fetch, site, { saved: { file: v2, path: "/lookup/2.json", etag: '"two"' } });
  assert.equal(found.file, v2);
  assert.deepEqual(sent, [["/lookup/2.json", '"two"']]);
  // An ETag saved for version 1 is not sent for version 2.
  sent.length = 0;
  await assert.rejects(fetchIndex(fetch, site, { saved: { file: v1, path: "/lookup.json", etag: '"one"' } }));
  assert.deepEqual(sent[0], ["/lookup/2.json", null]);
});
