// Exercise real workerd Request/fetch/KV behavior with recorded offline providers.
// Node's Fetch API accepts modes that Workers does not, so mocks alone are insufficient.
import { readFileSync } from "node:fs";
import assert from "node:assert/strict";
import { test } from "node:test";
import { Miniflare, convertV4MiniflareOptions } from "miniflare";

const recorded = name => JSON.parse(readFileSync(new URL(`./fixtures/research/${name}.json`, import.meta.url), "utf8")).body;
const source = readFileSync(new URL("../worker/research.mjs", import.meta.url), "utf8");
const script = `${source}
export default { async fetch(request, env) {
  return Response.json(await makeResearch({fetch, apiKey: "fixture-only", contact: "operator@example.org", cache: env.RESEARCH_CACHE})
    .search({intervention:"median nerve stimulation",indication:"Tourette syndrome",organisations:["Kyoto University"]}));
}};`;

test("Workers runtime retrieves both sources and reuses KV without outbound requests", async () => {
  const calls = [];
  const mf = new Miniflare(convertV4MiniflareOptions({
    modules: true, script, compatibilityDate: "2026-10-01", cf: false,
    kvNamespaces: ["RESEARCH_CACHE"],
    outboundService(request) {
      const url = new URL(request.url);
      calls.push(url.href);
      if (url.hostname === "api.openalex.org") {
        assert.equal(request.headers.get("Authorization"), "Bearer fixture-only");
        return Response.json(recorded(url.pathname === "/rate-limit" ? "openalex-allowance" : "openalex-works"));
      }
      assert.equal(url.hostname, "api.ror.org");
      assert.equal(request.headers.get("Authorization"), null);
      return Response.json(recorded("ror-affiliation"));
    },
  }));
  try {
    const response = await mf.dispatchFetch("https://worker.test/");
    assert.equal(response.status, 200);
    const result = await response.json();
    assert.deepEqual(result.availability, {openalex:"ok",ror:"ok"});
    assert.equal(result.papers.length, 10);
    assert.equal(result.organisations[0].name, "Kyoto University");
    assert.equal(calls.length, 3);
    const again = await (await mf.dispatchFetch("https://worker.test/")).json();
    assert.deepEqual(again, result);
    assert.equal(calls.length, 3);
  } finally { await mf.dispose(); }
});

test("Workers never follows provider redirects or forwards the API key to their target", async () => {
  const calls = [];
  const mf = new Miniflare(convertV4MiniflareOptions({
    modules: true, script, compatibilityDate: "2026-10-01", cf: false,
    outboundService(request) {
      calls.push(request.url);
      assert.notEqual(new URL(request.url).hostname, "redirect.example");
      return new Response(null, {status:302,headers:{Location:"https://redirect.example/"}});
    },
  }));
  try {
    const result = await (await mf.dispatchFetch("https://worker.test/")).json();
    assert.deepEqual(result.availability, {openalex:"unavailable",ror:"unavailable"});
    assert.equal(calls.length, 2);
  } finally { await mf.dispose(); }
});

test("Workers discovers the King's paper without citation identifiers and caches the scoped queries", async () => {
  const probe = JSON.parse(readFileSync(new URL("./fixtures/research/kcl-blind-discovery.json", import.meta.url), "utf8"));
  const { reading } = probe;
  const input = {intervention:reading.intervention, indication:reading.indication,
    paperQueries:reading.paper_queries, researchers:reading.researchers, publishedBefore:probe.publicationDate};
  const calls = [];
  const mf = new Miniflare(convertV4MiniflareOptions({
    modules: true, script: `${source}
      export default { async fetch(request, env) {
        return Response.json(await makeResearch({fetch, apiKey:"fixture-only", contact:"operator@example.org",cache:env.RESEARCH_CACHE})
          .search(${JSON.stringify(input)}));
      }};`, compatibilityDate:"2026-10-01", cf:false, kvNamespaces:["RESEARCH_CACHE"],
    outboundService(request) {
      const url = new URL(request.url); calls.push(url.href);
      assert.equal(url.hostname, "api.openalex.org");
      assert.equal(request.headers.get("Authorization"), "Bearer fixture-only");
      assert(!/39532305|4c00520|W4404326590|Generating.*Tooth.*Organoids/i.test(decodeURIComponent(url.href)));
      if (url.pathname === "/rate-limit") return Response.json(recorded("openalex-allowance"));
      assert.equal(url.pathname, "/works");
      if (url.searchParams.get("search") === probe.query.search && url.searchParams.get("filter")?.includes(probe.query.filter)) {
        return Response.json(probe.response.body);
      }
      return Response.json({results:[]});
    },
  }));
  try {
    const result = await (await mf.dispatchFetch("https://worker.test/")).json();
    assert.equal(result.papers[0]?.id, "https://openalex.org/W4404326590");
    assert.equal(result.availability.openalex, "ok");
    assert.equal(calls.filter(value => new URL(value).pathname === "/works").length, 4);
    const before = calls.length;
    assert.deepEqual(await (await mf.dispatchFetch("https://worker.test/")).json(), result);
    assert.equal(calls.length, before);
  } finally { await mf.dispose(); }
});
