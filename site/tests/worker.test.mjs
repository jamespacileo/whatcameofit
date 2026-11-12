// The public lookup service, tested through its five modules with fakes for the model,
// the registry, the network and Cloudflare's bindings. No network and no account.
// Scenario names are from openspec live-lookup. All text is synthetic.
import assert from "node:assert/strict";
import { test } from "node:test";

import { readArticle } from "../worker/article.mjs";
import worker, { handle } from "../worker/index.mjs";
import { lookUp } from "../worker/lookup.mjs";
import { makeModel } from "../worker/model.mjs";
import { makeRegistry } from "../worker/registry.mjs";

const TEXT = "Scientists say EX-1, also called Toothgrow, regrew teeth in people born without them.";
const READING = {
  about_a_treatment: true,
  gist: "An antibody was reported to regrow missing teeth.",
  intervention: "EX-1",
  other_names: ["Toothgrow", "the drug"],
  known_names: [],
  search_phrases: [],
  indication: "tooth agenesis",
};

function study(id, title, condition = "Tooth Agenesis") {
  return {
    protocolSection: {
      identificationModule: { nctId: id, briefTitle: title },
      conditionsModule: { conditions: [condition] },
      armsInterventionsModule: { interventions: [{ name: "EX-1" }] },
      designModule: { phases: ["PHASE2"] },
      statusModule: { overallStatus: "RECRUITING" },
    },
  };
}

function fakeRegistry(byName, byId = {}) {
  const searched = [];
  return {
    searched,
    search: async (name, condition) => (searched.push([name, condition]), byName[name] ?? []),
    fetch: async (id) => byId[id] ?? null,
  };
}

// Scores by reading the record: a match only when it names tooth agenesis.
function fakeModel(reading = READING) {
  const shown = [];
  return {
    shown,
    read: async (text) => (shown.push(text), reading),
    score: async (_intro, items) =>
      items.map((item) => {
        const match = item.includes("Tooth Agenesis");
        const answer = match ? "match" : "other_indication";
        return { answer, probabilities: { match: match ? 0.96 : 0.02 } };
      }),
  };
}

const INDEX = {
  claims: {
    "tooth-regrowth-ex1": { headline: "Antibody regrows teeth", page: "/tooth-regrowth-ex1", names: ["Anti-USAG-1 antibody", "toothgrow"] },
  },
};

// --- lookup -------------------------------------------------------------------------

test("Scenario: Article about a treatment with registered trials", async () => {
  const registry = fakeRegistry({
    "EX-1": [study("NCT00000002", "EX-1 in lung cancer", "Lung Cancer"), study("NCT00000001", "EX-1 in tooth agenesis")],
  });

  const found = await lookUp({ text: TEXT, model: fakeModel(), registry, index: INDEX });

  assert.deepEqual([found.treatment, found.condition], ["EX-1", "tooth agenesis"]);
  assert.deepEqual(found.candidates.map((c) => [c.id, c.answer]), [
    ["NCT00000001", "match"],
    ["NCT00000002", "other_indication"],
  ]);
  const [first] = found.candidates;
  assert.equal(first.url, "https://clinicaltrials.gov/study/NCT00000001");
  assert.deepEqual(
    [first.title, first.conditions, first.phases, first.state],
    ["EX-1 in tooth agenesis", ["Tooth Agenesis"], ["PHASE2"], "RECRUITING"],
  );
  assert.ok(first.score > 0.9 && found.candidates[1].score < 0.5);
});

test("every name, part, known name and phrase is searched within the condition", async () => {
  const reading = {
    ...READING,
    intervention: "EX-1 and EX-2",
    other_names: ["Toothgrow", "the drug", "NCT01234567"],
    known_names: ["TRG-035"],
    search_phrases: ["USAG-1 antibody"],
  };
  const registry = fakeRegistry({});

  const found = await lookUp({ text: TEXT, model: fakeModel(reading), registry, index: INDEX });

  assert.deepEqual(registry.searched.map(([name]) => name), ["EX-1 and EX-2", "Toothgrow", "EX-1", "EX-2", "TRG-035", "USAG-1 antibody"]);
  assert.ok(registry.searched.every(([, condition]) => condition === "tooth agenesis"));
  assert.deepEqual([found.names, found.known_names], [["EX-1 and EX-2", "Toothgrow"], ["TRG-035"]]);
});

test("Scenario: Text that states a registry number", async () => {
  const registry = fakeRegistry({}, { NCT01234567: study("NCT01234567", "EX-1 first study in people") });

  const found = await lookUp({ text: `${TEXT} Registered as nct01234567.`, model: fakeModel(), registry, index: INDEX });

  assert.deepEqual(found.candidates.map((c) => c.id), ["NCT01234567"]);
});

test("Scenario: Text that is not about a treatment", async () => {
  const registry = fakeRegistry({});
  const model = fakeModel({ about_a_treatment: false, gist: "A report on waiting times." });

  const found = await lookUp({ text: "Waiting lists grew again.", model, registry, index: INDEX });

  assert.deepEqual([found.about_a_treatment, found.candidates, registry.searched], [false, [], []]);
});

test("Scenario: Treatment already tracked", async () => {
  const found = await lookUp({ text: TEXT, model: fakeModel(), registry: fakeRegistry({}), index: INDEX });

  assert.deepEqual(found.tracked, [{ slug: "tooth-regrowth-ex1", headline: "Antibody regrows teeth", page: "/tooth-regrowth-ex1" }]);
});

test("no more than sixty records are scored", async () => {
  const many = Array.from({ length: 75 }, (_, n) => study(`NCT${String(n).padStart(8, "0")}`, "EX-1 study"));

  const found = await lookUp({ text: TEXT, model: fakeModel(), registry: fakeRegistry({ "EX-1": many }), index: INDEX });

  assert.equal(found.candidates.length, 60);
});

// --- registry -----------------------------------------------------------------------

function registryOver(pages) {
  const asked = [];
  const fetch = async (address, options) => {
    const url = new URL(address);
    asked.push({ url, agent: options.headers["User-Agent"] });
    const key = `${url.searchParams.get("query.intr") ?? url.pathname.split("/").pop()}|${url.searchParams.get("query.cond") ?? ""}|${url.searchParams.get("pageToken") ?? ""}`;
    const body = pages[key];
    return body ? Response.json(body) : new Response("", { status: 404 });
  };
  return { registry: makeRegistry({ fetch, contact: "ops@example.org" }), asked };
}

test("a specific name returns every page of its trials and names the client", async () => {
  const { registry, asked } = registryOver({
    "EX-1||": { studies: [study("NCT00000001", "one")], totalCount: 2, nextPageToken: "p2" },
    "EX-1||p2": { studies: [study("NCT00000002", "two")], totalCount: 2 },
  });

  const found = await registry.search("EX-1", "tooth agenesis");

  assert.deepEqual(found.map((s) => s.protocolSection.identificationModule.nctId), ["NCT00000001", "NCT00000002"]);
  assert.match(asked[0].agent, /^thenwhat-lookup\/\S+ \(mailto:ops@example\.org\)$/);
});

test("a broad name is searched within the condition, then by its telling words", async () => {
  const { registry } = registryOver({
    "vitamin C||": { studies: [], totalCount: 900 },
    "vitamin C|chronic tooth agenesis|": { studies: [], totalCount: 0 },
    "vitamin C|tooth OR agenesis|": { studies: [study("NCT00000003", "three")], totalCount: 1 },
  });

  const found = await registry.search("vitamin C", "chronic tooth agenesis");

  assert.deepEqual(found.map((s) => s.protocolSection.identificationModule.nctId), ["NCT00000003"]);
});

test("Scenario: Name that identifies nothing", async () => {
  const { registry } = registryOver({
    "therapy||": { studies: [], totalCount: 90000 },
    "therapy|tooth agenesis|": { studies: [], totalCount: 400 },
  });

  assert.deepEqual(await registry.search("therapy", "tooth agenesis"), []);
});

test("a trial is fetched by its number, and an unknown number is none", async () => {
  const { registry } = registryOver({ "NCT00000001||": study("NCT00000001", "one") });

  assert.equal((await registry.fetch("NCT00000001")).protocolSection.identificationModule.briefTitle, "one");
  assert.equal(await registry.fetch("NCT99999999"), null);
});

// --- model --------------------------------------------------------------------------

function modelOver(...replies) {
  const sent = [];
  const fetch = async (address, options) => {
    sent.push({ address, headers: options.headers, body: JSON.parse(options.body) });
    return Response.json({ choices: [{ message: { content: JSON.stringify(replies.shift()) } }] });
  };
  const model = makeModel({ fetch, apiKey: "test-key", model: "example-model", baseUrl: "https://llm.example.test/v1" });
  return { model, sent };
}

test("the model is shown the text and asked for a strict shape, with the configured model", async () => {
  const { model, sent } = modelOver(READING);

  const reading = await model.read(TEXT);

  assert.equal(reading.intervention, "EX-1");
  const [{ address, headers, body }] = sent;
  assert.equal(address, "https://llm.example.test/v1/chat/completions");
  assert.equal(headers.Authorization, "Bearer test-key");
  assert.equal(body.model, "example-model");
  assert.equal(body.messages.at(-1).content, TEXT);
  assert.deepEqual([body.response_format.type, body.response_format.json_schema.strict], ["json_schema", true]);
});

test("a model named with its provider, as the pipeline's settings name it, is asked for by its own name", async () => {
  const sent = [];
  const fetch = async (_address, options) => {
    sent.push(JSON.parse(options.body));
    return Response.json({ choices: [{ message: { content: JSON.stringify(READING) } }] });
  };

  await makeModel({ fetch, apiKey: "test-key", model: "openai:example-model" }).read(TEXT);

  assert.equal(sent[0].model, "example-model");
});

test("records are scored twenty to a call and probabilities that nearly sum to one are rescaled", async () => {
  const answer = (item) => ({ item, choice: "match", probabilities: { match: 0.9, other_indication: 0.06, not_a_match: 0.02 } });
  const first = { answers: Array.from({ length: 20 }, (_, n) => answer(n + 1)) };
  const second = { answers: [answer(1)] };
  const { model, sent } = modelOver(first, second);

  const scored = await model.score("Claim: …", Array.from({ length: 21 }, (_, n) => `record ${n}`));

  assert.equal(sent.length, 2);
  assert.equal(scored.length, 21);
  assert.equal(scored[0].answer, "match");
  assert.ok(Math.abs(scored[0].probabilities.match - 0.9 / 0.98) < 1e-9);
});

test("a record the model leaves out, or answers unusably, has no score", async () => {
  const { model } = modelOver({ answers: [{ item: 2, choice: "match", probabilities: { match: 3, other_indication: 0, not_a_match: 0 } }] });

  assert.deepEqual(await model.score("Claim: …", ["one", "two"]), [null, null]);
});

// --- article ------------------------------------------------------------------------

function web(pages) {
  const asked = [];
  const fetch = async (address) => {
    asked.push(address);
    const page = pages[address];
    if (page === undefined) return new Response("", { status: 404 });
    return typeof page === "number" ? new Response("", { status: page }) : new Response(page, { status: 200 });
  };
  return { fetch, asked };
}
const ARTICLE = "https://news.example.org/health/ex1";
const PAGE = `<html><head><title>EX-1 regrows teeth</title><style>p{}</style><script>track()</script></head><body><h1>EX-1 regrows teeth</h1><p>Scientists say&nbsp;EX-1 worked.</p></body></html>`;

test("an article that robots.txt allows is returned as plain text", async () => {
  const { fetch } = web({ "https://news.example.org/robots.txt": "User-agent: *\nDisallow: /private/", [ARTICLE]: PAGE });

  const read = await readArticle(ARTICLE, { fetch, contact: "ops@example.org" });

  assert.equal(read.text, "EX-1 regrows teeth EX-1 regrows teeth Scientists say EX-1 worked.");
});

test("Scenario: Article the site does not allow to be read", async () => {
  for (const robots of ["User-agent: *\nDisallow: /", "User-agent: thenwhat\nDisallow: /health/\n\nUser-agent: *\nAllow: /", 403]) {
    const { fetch, asked } = web({ "https://news.example.org/robots.txt": robots, [ARTICLE]: PAGE });

    assert.deepEqual(await readArticle(ARTICLE, { fetch, contact: "ops@example.org" }), { refused: "robots" });
    assert.ok(!asked.includes(ARTICLE), "the article was fetched");
  }
});

test("an article that does not load, or a local address, is not read", async () => {
  const { fetch } = web({ "https://news.example.org/robots.txt": 404, [ARTICLE]: 402 });

  assert.deepEqual(await readArticle(ARTICLE, { fetch, contact: "ops@example.org" }), { refused: "unreadable" });
  for (const local of ["http://localhost:4321/x", "http://127.0.0.1/x", "http://10.0.0.5/x", "https://192.168.1.1/x", "ftp://news.example.org/x"]) {
    assert.deepEqual(await readArticle(local, { fetch, contact: "ops@example.org" }), { refused: "address" });
  }
});

// --- handler ------------------------------------------------------------------------

function env(overrides = {}) {
  const limiter = (allowed) => ({ limit: async () => ({ success: allowed }) });
  return {
    ASSETS: { fetch: async (request) => (new URL(request.url).pathname === "/lookup.json" ? Response.json(INDEX) : new Response("a page")) },
    LOOKUP_PER_READER: limiter(true),
    LOOKUP_IN_ALL: limiter(true),
    OPENAI_API_KEY: "test-key",
    LLM_MODEL: "example-model",
    CONTACT_EMAIL: "ops@example.org",
    ...overrides,
  };
}
const post = (body) => new Request("https://tracker.example.org/api/lookup", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
const stubs = { model: fakeModel(), registry: fakeRegistry({ "EX-1": [study("NCT00000001", "EX-1 in tooth agenesis")] }) };

test("Scenario: Reader asks about pasted text", async () => {
  const response = await handle(post({ text: TEXT }), env(), stubs);

  assert.equal(response.status, 200);
  assert.equal(response.headers.get("Cache-Control"), "no-store");
  const body = await response.json();
  assert.deepEqual([body.treatment, body.candidates[0].id, body.tracked[0].slug], ["EX-1", "NCT00000001", "tooth-regrowth-ex1"]);
});

test("anything but the lookup address is served as a page of the site", async () => {
  const response = await worker.fetch(new Request("https://tracker.example.org/how-it-works"), env());

  assert.equal(await response.text(), "a page");
});

test("requests the service will not answer say why with a code", async () => {
  const cases = [
    [new Request("https://tracker.example.org/api/lookup"), env(), 405, "method"],
    [post({}), env(), 400, "nothing_given"],
    [post({ text: "x".repeat(20001) }), env(), 413, "too_long"],
    [post({ url: "https://x.com/someone/status/1" }), env(), 422, "post"],
    [post({ url: "https://bit.ly/abc" }), env(), 422, "short"],
    [post({ text: TEXT }), env({ LOOKUP_PER_READER: { limit: async () => ({ success: false }) } }), 429, "busy"],
    [post({ text: TEXT }), env({ LOOKUP_IN_ALL: { limit: async () => ({ success: false }) } }), 429, "busy"],
    [post({ text: TEXT }), env({ OPENAI_API_KEY: undefined }), 503, "not_set_up"],
  ];
  for (const [request, bindings, status, code] of cases) {
    const response = await worker.fetch(request, bindings);
    assert.deepEqual([response.status, (await response.json()).error], [status, code], code);
  }
});

test("Scenario: Nothing a reader sends is written down", async () => {
  const written = [];
  const original = { log: console.log, error: console.error, warn: console.warn };
  console.log = console.error = console.warn = (...parts) => written.push(parts.join(" "));
  try {
    await handle(post({ text: TEXT }), env(), stubs);
    const broken = { ...stubs, model: { read: async () => { throw new Error("model down: Toothgrow"); } } };
    assert.equal((await handle(post({ text: TEXT }), env(), broken)).status, 502);
  } finally {
    Object.assign(console, original);
  }
  assert.ok(!written.join("\n").includes("Toothgrow"), "the text was logged");
});
