// Synthetic provider fixtures; never calls a live API.
import { test } from "node:test";
import assert from "node:assert/strict";
import { makeResearch } from "../worker/research.mjs";
const budget={daily_budget_usd:1,daily_remaining_usd:0.95,prepaid_balance_usd:0,prepaid_remaining_usd:0,endpoint_costs_usd:{search:0.001}};
const work={id:"https://openalex.org/W1234567890",doi:"https://doi.org/10.1234/example",title:"EX-1 for tooth agenesis",publication_year:2025,type:"article",primary_location:{source:{display_name:"Example Journal"}},abstract_inverted_index:{PRIVATE:[0]}};
const org={id:"https://ror.org/02kpeqv85",names:[{value:"Kyoto University",types:["ror_display"]}],locations:[{geonames_details:{country_name:"Japan"}}],links:[{type:"website",value:"https://www.kyoto-u.ac.jp"}]};
const input={intervention:"EX-1",indication:"tooth agenesis",searchPhrases:["tooth repair"],organisations:["Kyoto University"]};
function setup(overrides={}) {
 const calls=[], entries=new Map(); const cache={get:async k=>JSON.parse(entries.get(k)??"null"),put:async(k,v)=>{entries.set(k,v)}};
 const fetch=async(url,init={})=>{calls.push({url:String(url),init});const u=new URL(url);if(u.hostname==="api.ror.org")return Response.json({items:[{chosen:true,score:1,organization:org}]});if(u.pathname==="/rate-limit")return Response.json({rate_limit:overrides.budget??budget});return Response.json({results:[work]});};
 return {calls,entries,research:makeResearch({fetch,cache,contact:"operator@example.org",apiKey:"SENTINEL_SECRET",...overrides})};
}
test("real API shapes become minimal safe public records; caching avoids repeat charges",async()=>{
 const s=setup();const a=await s.research.search(input);
 assert.equal(a.papers.length,1);assert.equal(a.papers[0].title,work.title);assert.equal(a.organisations[0].name,"Kyoto University");assert.equal(a.organisations[0].id,org.id);
 assert.equal(a.availability.openalex,"ok");assert.equal(a.availability.ror,"ok");
 assert(!JSON.stringify(a).includes("PRIVATE"));assert(!JSON.stringify([...s.entries]).includes("SENTINEL_SECRET"));
 assert(s.calls.every(c=>!c.url.includes("SENTINEL_SECRET")));assert(s.calls.filter(c=>c.url.includes("api.openalex.org")).every(c=>new Headers(c.init.headers).get("Authorization")==="Bearer SENTINEL_SECRET"));
 const n=s.calls.length;await s.research.search(input);assert.equal(s.calls.length,n);
});
test("no key never calls OpenAlex while ROR still works",async()=>{const s=setup({apiKey:""});const a=await s.research.search(input);assert.equal(a.availability.openalex,"not_configured");assert.equal(a.organisations.length,1);assert(!s.calls.some(c=>c.url.includes("api.openalex.org")));});
test("exhaustion, uncertain budgets, or prepaid credit cannot become paid search",async()=>{
 for(const b of [{...budget,daily_remaining_usd:0},{...budget,prepaid_balance_usd:10},{...budget,prepaid_remaining_usd:10},{}, {...budget,daily_budget_usd:100}]) {
 const s=setup({budget:b});const a=await s.research.search(input);assert.equal(a.papers.length,0);assert(!s.calls.some(c=>new URL(c.url).pathname==="/works"));assert.equal(a.organisations.length,1);
 }
});
test("429 stops further searches and partial failure preserves ROR",async()=>{
 let works=0;const s=setup({fetch:async(url)=>{const u=new URL(url);if(u.hostname==="api.ror.org")return Response.json({items:[]});if(u.pathname==="/rate-limit")return Response.json({rate_limit:budget});works++;return new Response("",{status:429,headers:{"Retry-After":"120"}})}});
 const a=await s.research.search(input);assert.equal(works,1);assert.equal(a.availability.openalex,"limit");assert.equal(a.availability.ror,"ok");
});

test("empty responses cache, expire, and never turn ambiguous ROR items into matches", async () => {
  let time = Date.UTC(2026, 10, 13); let count = 0;
  const entries = new Map();
  const cache = { get: async k => JSON.parse(entries.get(k) ?? "null"), put: async (k,v) => entries.set(k,v) };
  const research = makeResearch({ apiKey: "key", contact: "test@example.org", cache, now: () => time,
    fetch: async url => { count++; return Response.json(String(url).includes("rate-limit") ? {rate_limit:budget} :
      String(url).includes("ror.org") ? { items: [{ chosen: false, score: 0.99, organization: org }] } : { results: [] }); } });
  const first = await research.search(input);
  assert.deepEqual(first.papers, []); assert.deepEqual(first.organisations, []);
  const after = count; await research.search(input); assert.equal(count, after);
  time += 8 * 86_400_000; await research.search(input); assert(count > after);
});

test("a provider outage cannot erase the other provider; header and body timeouts are bounded", async () => {
  for (const stalled of [() => new Promise(() => {}), () => new Response(new ReadableStream({ start() {} }))]) {
    const start = Date.now();
    const s = setup({ timeoutMs: 20, fetch: async url => String(url).includes("openalex") ? stalled() : Response.json({items:[{chosen:true,score:1,organization:org}]}) });
    const result = await s.research.search(input);
    assert.equal(result.availability.openalex, "unavailable"); assert.equal(result.organisations.length, 1);
    assert(Date.now() - start < 1000);
  }
});

test("no contact means no requests; input and result counts are bounded", async () => {
  const missing = setup({contact: ""}); await missing.research.search(input); assert.equal(missing.calls.length, 0);
  const s = setup();
  await s.research.search({...input, searchPhrases: Array(100).fill("another phrase"), organisations: Array(100).fill("Kyoto University")});
  assert.equal(s.calls.filter(c=>new URL(c.url).pathname==="/works").length, 2);
  assert.equal(s.calls.filter(c=>c.url.includes("ror.org")).length, 1);
});

test("exhausted provider pauses survive a new client via shared cache", async () => {
  const entries = new Map(); let calls = 0;
  const options = { apiKey: "key", contact: "test@example.org", cache: {
    get: async k => JSON.parse(entries.get(k) ?? "null"), put: async (k,v) => entries.set(k,v),
  }, fetch: async () => { calls++; return new Response("secret upstream error", { status: 402 }); } };
  await makeResearch(options).search({intervention:"A",indication:"B"});
  const before = calls;
  const result = await makeResearch(options).search({intervention:"C",indication:"D"});
  assert.equal(calls, before); assert.equal(result.availability.openalex, "limit");
  assert(!JSON.stringify([...entries]).includes("secret upstream error"));
});

test("malformed metadata, script links and raw abstracts never enter the answer", async () => {
  const s = setup({fetch: async url => Response.json(String(url).includes("rate-limit") ? {rate_limit:budget} : String(url).includes("ror.org") ?
    {items:[{chosen:true,score:1,organization:{...org,id:"javascript:alert(1)"}}]} :
    {results:[{...work,id:"javascript:alert(1)"},{...work,doi:"https://evil.example/redirect",title:"<script>example</script>"}]})});
  const result = await s.research.search(input);
  assert.equal(result.papers.length,1); assert.equal(result.papers[0].url,work.id);
  assert.deepEqual(result.organisations,[]); assert(!JSON.stringify(result).includes("PRIVATE"));
});
