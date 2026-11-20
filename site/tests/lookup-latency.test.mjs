// Lookups that cannot be held up: by linked papers or stated records once the model has
// read the text as no treatment, by a publisher that stalls, or by a slow paper or registry.
import assert from "node:assert/strict";
import { test } from "node:test";
import { handle } from "../worker/index.mjs";
import { lookUp } from "../worker/lookup.mjs";
import { readArticle } from "../worker/article.mjs";
import { makePapers } from "../worker/papers.mjs";
import { makeRegistry } from "../worker/registry.mjs";
import { withDeadline } from "../worker/deadline.mjs";

const never = () => new Promise(() => {});
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}
async function within(promise, ms = 500) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("still waiting")), ms); })]);
  } finally { clearTimeout(timer); }
}
const study = (id, title, intervention = "EX-1") => ({
  protocolSection: {
    identificationModule: { nctId: id, briefTitle: title },
    conditionsModule: { conditions: ["tinnitus"] },
    armsInterventionsModule: { interventions: [{ name: intervention }] },
    statusModule: { overallStatus: "COMPLETED" },
  },
});
const treatment = { about_a_treatment: true, intervention: "EX-1", indication: "tinnitus", gist: "EX-1 for tinnitus" };
const scoreAll = async (_intro, records) => records.map(() => ({ answer: "yes", probabilities: { match: 0.9 } }));

// --- lookUp ---------------------------------------------------------------------------

test("a non-treatment answer is given at once and later background failures stay handled", async () => {
  const unhandled = [];
  const watch = (reason) => unhandled.push(reason);
  process.on("unhandledRejection", watch);
  try {
    const paper = deferred();
    const record = deferred();
    const result = await within(lookUp({
      text: "A tinnitus biomarker study. NCT00000001",
      model: { read: async () => ({ about_a_treatment: false, gist: "not a treatment" }) },
      index: { pairs: {} },
      registry: { fetch: () => record.promise },
      page: { dois: ["10.1002/example"] },
      papers: { trialNumbers: () => paper.promise },
    }), 100);
    assert.equal(result.about_a_treatment, false);
    assert.deepEqual(result.registry_numbers, ["NCT00000001"]);
    assert.deepEqual(result.candidates, []);
    // What was still pending ends afterwards, one way or the other.
    record.reject(new Error("registry 500"));
    paper.resolve(["NCT00000002"]);
    await pause(10);
    assert.deepEqual(unhandled, []);
  } finally {
    process.off("unhandledRejection", watch);
  }
});

test("a treatment lookup still overlaps the model's reading with stated records and papers", async () => {
  const reading = deferred();
  const asked = [];
  const records = { NCT00000001: study("NCT00000001", "EX-1 stated"), NCT00000002: study("NCT00000002", "EX-1 from paper") };
  const running = lookUp({
    text: "EX-1 for tinnitus. NCT00000001",
    model: { read: () => reading.promise, score: scoreAll },
    index: { pairs: {} },
    registry: {
      fetch: async (number) => { asked.push(number); return records[number] ?? null; },
      named: async () => [],
      search: async () => [],
    },
    page: { dois: ["10.1002/example"] },
    papers: { trialNumbers: async () => { asked.push("paper"); return ["NCT00000002"]; } },
  });
  await pause(5);
  assert.ok(asked.includes("NCT00000001") && asked.includes("paper"), "asked before the model answered");
  reading.resolve(treatment);
  const result = await within(running);
  assert.equal(result.about_a_treatment, true);
  assert.deepEqual(result.candidates.map((one) => one.id), ["NCT00000001", "NCT00000002"]);
  assert.deepEqual(result.candidates[0].agrees, ["stated"]);
  assert.deepEqual(result.candidates[1].agrees, ["paper"]);
});

test("a treatment lookup still fails when a stated record cannot be fetched", async () => {
  await assert.rejects(lookUp({
    text: "EX-1 for tinnitus. NCT00000001",
    model: { read: async () => treatment, score: scoreAll },
    index: { pairs: {} },
    registry: { fetch: async () => { throw new Error("registry 500"); }, named: async () => [], search: async () => [] },
  }), /registry 500/);
});

// --- readArticle ----------------------------------------------------------------------

const ARTICLE = "https://news.example.org/report";
const PAGE = "<html><head><title>EX-1 report</title></head><body><main><p>EX-1 was studied for tinnitus.</p></main></body></html>";

test("article stalls in headers or body end in the existing refusal, even when abort is ignored", async () => {
  for (const stage of ["robots-headers", "robots-body", "article-headers", "article-body"]) {
    const signals = [];
    const started = Date.now();
    const result = await within(readArticle(ARTICLE, {
      contact: "test@example.org",
      timeoutMs: 30,
      // Ignores its signal throughout: only the deadline can end the wait.
      fetch: async (url, options) => {
        signals.push(options.signal);
        const robots = String(url).endsWith("/robots.txt");
        if (stage.startsWith(robots ? "robots" : "article")) {
          return stage.endsWith("headers") ? never() : { status: 200, text: never };
        }
        return new Response(robots ? "User-agent: *\nAllow: /" : PAGE);
      },
    }));
    assert.ok(Date.now() - started < 300, stage);
    assert.deepEqual(result, { refused: "unreadable" }, stage);
    assert.equal(signals.at(-1)?.aborted, true, `${stage}: the stalled request is aborted`);
  }
});

test("the article deadline is one total, not one per request", async () => {
  const result = await within(readArticle(ARTICLE, {
    contact: "test@example.org",
    timeoutMs: 40,
    fetch: async (url) => {
      await pause(25);
      return new Response(String(url).endsWith("/robots.txt") ? "User-agent: *\nAllow: /" : PAGE);
    },
  }));
  assert.deepEqual(result, { refused: "unreadable" });
});

test("robots rules still decide, and an article read in time is read as before", async () => {
  const site = (robots) => async (url) => new Response(String(url).endsWith("/robots.txt") ? robots : PAGE);
  assert.deepEqual(await readArticle(ARTICLE, { contact: "t@example.org", fetch: site("User-agent: *\nDisallow: /") }), { refused: "robots" });
  assert.deepEqual(await readArticle(ARTICLE, { contact: "t@example.org", fetch: async () => { throw new Error("offline"); } }), { refused: "robots" });
  const read = await readArticle(ARTICLE, { contact: "t@example.org", fetch: site("User-agent: *\nAllow: /") });
  assert.match(read.text, /EX-1 was studied for tinnitus/);
});

// --- papers and registry --------------------------------------------------------------

test("paper and registry requests reject when headers or body stall, and abort them", async () => {
  for (const kind of ["papers", "registry"]) {
    for (const stage of ["headers", "body"]) {
      let signal;
      const options = {
        contact: "test@example.org",
        timeoutMs: 20,
        fetch: async (_url, given) => { signal = given.signal; return stage === "headers" ? never() : { ok: true, status: 200, json: never }; },
      };
      const client = kind === "papers" ? makePapers(options) : makeRegistry(options);
      const asked = kind === "papers"
        ? [() => client.trialNumbers({ doi: "10.1002/example" })]
        : [() => client.fetch("NCT00000001"), () => client.named("EXAMPLE-1"), () => client.search("EX-1", "tinnitus")];
      for (const ask of asked) {
        signal = null;
        await assert.rejects(within(ask()), (error) => error.code === "timeout", `${kind} ${stage}`);
        assert.equal(signal.aborted, true, `${kind} ${stage}`);
      }
    }
  }
});

test("paper and registry answers in time are unchanged", async () => {
  const papers = makePapers({ contact: "t@example.org", fetch: async () => Response.json({ resultList: { result: [{ abstractText: "Registered as NCT00000001." }] } }) });
  assert.deepEqual(await papers.trialNumbers({ doi: "10.1/x" }), ["NCT00000001"]);
  const registry = makeRegistry({ contact: "t@example.org", fetch: async (url) =>
    String(url).includes("/studies/") ? new Response("", { status: 404 }) : Response.json({ studies: [study("NCT00000001", "EX-1")], totalCount: 1 }) });
  assert.equal(await registry.fetch("NCT00000001"), null);
  assert.deepEqual((await registry.search("EX-1", "tinnitus")).map((one) => one.protocolSection.identificationModule.nctId), ["NCT00000001"]);
  const failing = makeRegistry({ contact: "t@example.org", fetch: async () => new Response("", { status: 500 }) });
  await assert.rejects(failing.search("EX-1", "tinnitus"), /registry 500/);
});

test("a deadline clears its timer and follows an aborted parent", async () => {
  assert.equal(await withDeadline(10_000, async () => "quick"), "quick");
  const parent = new AbortController();
  let inner;
  const running = withDeadline(10_000, (signal) => { inner = signal; return never(); }, { parent: parent.signal });
  await pause(1);
  parent.abort();
  await assert.rejects(within(running));
  assert.equal(inner.aborted, true);
});

// --- the public proof in the handler ----------------------------------------------------

const env = (store) => ({
  OPENAI_API_KEY: "test", LLM_MODEL: "configured", CONTACT_EMAIL: "test@example.org",
  LOOKUP_PER_READER: { limit: async () => ({ success: true }) },
  LOOKUP_IN_ALL: { limit: async () => ({ success: true }) },
  ASSETS: { fetch: async () => Response.json({ format: "lookup", format_version: 2, pairs: {}, articles: {} }) },
  LOOKUP_RESULTS: store,
});
const lookupRequest = (body) => new Request("https://whatcameofit.example/api/lookup", { method: "POST", body: JSON.stringify(body) });
const memory = () => {
  const values = new Map();
  return { values, get: async (key) => (values.has(key) ? JSON.parse(values.get(key)) : null), put: async (key, value) => { values.set(key, value); } };
};
const registry = { fetch: async () => null, named: async () => [], search: async () => [] };

test("a stalled public proof falls back to the browser's text and shares nothing", async () => {
  for (const stall of ["robots", "headers", "body"]) {
    const store = memory();
    const read = [];
    const tools = {
      registry,
      proofTimeoutMs: 30,
      model: { read: async (text) => { read.push(text); return treatment; }, score: async () => [] },
      fetch: async (url) => {
        const robots = String(url).endsWith("/robots.txt");
        if (stall === "robots" && robots) return never();
        if (robots) return new Response("User-agent: *\nAllow: /");
        return stall === "headers" ? never() : { status: 200, text: never };
      },
    };
    const response = await within(handle(lookupRequest({ pageUrl: ARTICLE, text: "Browser text of EX-1 for tinnitus." }), env(store), tools));
    assert.equal(response.status, 200, stall);
    assert.equal((await response.json()).treatment, "EX-1", stall);
    assert.deepEqual(read, ["Browser text of EX-1 for tinnitus."], stall);
    assert.equal(store.values.size, 0, `${stall}: browser content is not shared`);
  }
});

test("a fast public proof still replaces the browser's text before the result is shared", async () => {
  const store = memory();
  const read = [];
  const tools = {
    registry,
    proofTimeoutMs: 1_000,
    model: { read: async (text) => { read.push(text); return treatment; }, score: async () => [] },
    fetch: async (url) => new Response(String(url).endsWith("/robots.txt") ? "User-agent: *\nAllow: /" : PAGE),
  };
  const response = await handle(lookupRequest({ pageUrl: ARTICLE, text: "PRIVATE ADDITION" }), env(store), tools);
  assert.equal(response.status, 200);
  assert.equal(read.length, 1);
  assert.doesNotMatch(read[0], /PRIVATE ADDITION/);
  assert.match(read[0], /EX-1 was studied for tinnitus/);
  assert.equal(store.values.size, 1, "an independently public result is shared");
  assert.doesNotMatch([...store.values.values()][0], /PRIVATE ADDITION/);
});
