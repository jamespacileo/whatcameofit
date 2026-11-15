// Real reports whose paper the lookup must find, replayed with no network. Each case in
// fixtures/research/cases holds what the model read from the article (never its text) and
// what OpenAlex and ROR answered, as recorded by `scripts/smoke-research.mjs --record`.
// A request the recording does not hold fails the case: record it again.
import assert from "node:assert/strict";
import { readdirSync, readFileSync } from "node:fs";
import { test } from "node:test";

import { makeResearch } from "../worker/research.mjs";

const fixtures = new URL("./fixtures/research/", import.meta.url);
const read = (name) => JSON.parse(readFileSync(new URL(name, fixtures), "utf8"));
const allowance = read("openalex-allowance.json").body;
const rankOf = (papers, doi) => papers.findIndex((paper) => paper.url.toLowerCase() === `https://doi.org/${doi}`.toLowerCase());

for (const name of readdirSync(new URL("cases/", fixtures)).filter((file) => file.endsWith(".json")).sort()) {
  const one = read(`cases/${name}`);
  test(`${name}: the report's paper is found`, async (t) => {
    assert(one.recorded, "not recorded yet: run scripts/smoke-research.mjs --record");
    const { reading, linked, responses } = one.recorded;
    const unrecorded = [];
    const replay = async (url) => {
      const at = new URL(url);
      if (at.pathname === "/rate-limit") return Response.json(allowance);
      if (at.href in responses) return Response.json(responses[at.href]);
      unrecorded.push(at.href);
      return new Response("", { status: 500 });
    };
    const research = () => makeResearch({ fetch: replay, apiKey: "fixture-only", contact: "operator@example.org" });

    await t.test("without the page's link to it, among the first results the site shows", async () => {
      const found = await research().search(reading);
      assert.deepEqual(unrecorded, []);
      assert.equal(found.availability.openalex, "ok");
      const rank = rankOf(found.papers, one.expected_doi);
      assert(rank >= 0 && rank < (one.within ?? 5), `result ${rank + 1}`);
      assert(found.papers[rank].institutions?.length, "found under an organisation the report names");
      assert(!found.papers[rank].linked);
    });

    await t.test("first when the page links to it", { skip: !linked.length }, async () => {
      const found = await research().search({ ...reading, linked });
      assert.deepEqual(unrecorded, []);
      assert.equal(rankOf(found.papers, one.expected_doi), 0);
      assert.equal(found.papers[0].linked, true);
    });
  });
}
