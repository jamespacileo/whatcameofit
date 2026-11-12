import assert from "node:assert/strict";
import { test } from "node:test";
import { createPopupController } from "../src/controller.js";

const tab = { id: 7, url: "https://news.example.org/report", key: "news.example.org/report" };
const index = { articles: {}, claims: {}, live: "/api/lookup" };
const request = { text: "EX-1 is being studied for a specific medical condition.", links: [] };
const answer = { treatment: "EX-1", candidates: [] };

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

function setup(overrides = {}) {
  const calls = { fetch: [], read: [], states: [] };
  const controller = createPopupController({
    storage: { get: async () => ({}), set: async () => {} },
    site: { url: "https://whatcameofit.example" },
    readTab: async () => tab,
    readPage: async (current) => { calls.read.push(current); return request; },
    fetch: async (url, options) => {
      calls.fetch.push({ url, options });
      return { ok: true, json: async () => options.method === "POST" ? answer : index };
    },
    describeAnswer: (found) => found,
    present: (state) => calls.states.push(state),
    ...overrides,
  });
  return { controller, calls };
}

test("opening an untracked page automatically performs one search without a second action", async () => {
  const { controller, calls } = setup();
  await controller.open();

  assert.deepEqual(calls.states.map((state) => state.kind), ["checking", "searching", "answer"]);
  assert.deepEqual(calls.read, [tab]);
  assert.equal(calls.fetch.length, 2);
  assert.equal(calls.fetch[1].url, "https://whatcameofit.example/api/lookup");
  assert.deepEqual(JSON.parse(calls.fetch[1].options.body), request);
  assert.equal(calls.states.at(-1).shown, answer);
});

test("tracked, non-web and disabled-service pages never read the page or start a model request", async () => {
  const claim = { headline: "Reviewed claim", page: "/reviewed", status: "Phase 1 trial" };
  const cases = [
    { current: tab, lookup: { ...index, articles: { [tab.key]: ["reviewed"] }, claims: { reviewed: claim } }, kind: "tracked" },
    { current: { id: 8, key: null, url: "chrome://extensions" }, lookup: index, kind: "no-page" },
    { current: tab, lookup: { ...index, live: null }, kind: "untracked" },
  ];
  for (const one of cases) {
    const { controller, calls } = setup({
      readTab: async () => one.current,
      storage: { get: async () => ({ lookup: { version: 2, index: one.lookup, savedAt: Date.now() } }) },
    });
    await controller.open();
    assert.equal(calls.states.at(-1).kind, one.kind);
    assert.equal(calls.read.length, 0);
    assert.equal(calls.fetch.length, 0);
  }
});

test("a fresh cached index still starts the page search", async () => {
  const { controller, calls } = setup({
    storage: { get: async () => ({ lookup: { version: 2, index, savedAt: Date.now() } }) },
  });
  await controller.open();
  assert.equal(calls.fetch.length, 1);
  assert.equal(calls.fetch[0].options.method, "POST");
});

test("concurrent opening calls and search actions share the running request", async () => {
  const reading = deferred();
  const started = deferred();
  let reads = 0;
  const { controller, calls } = setup({
    readPage: async () => { reads += 1; started.resolve(); return reading.promise; },
  });
  const first = controller.open();
  const second = controller.open();
  assert.equal(first, second);
  await started.promise;
  const retry = controller.search();
  reading.resolve(request);
  await Promise.all([first, second, retry]);
  assert.equal(reads, 1);
  assert.equal(calls.fetch.filter((call) => call.options.method === "POST").length, 1);
});

test("an upgrade refreshes an older cached service configuration", async () => {
  const { controller, calls } = setup({
    storage: {
      get: async () => ({ lookup: { index: { ...index, live: null }, savedAt: Date.now() } }),
      set: async () => {},
    },
  });
  await controller.open();
  assert.equal(calls.fetch.length, 2);
  assert.equal(calls.states.at(-1).kind, "answer");
});

test("a delayed index does not switch the lookup to a newly active tab", async () => {
  const indexResponse = deferred();
  const indexStarted = deferred();
  let active = tab;
  let tabReads = 0;
  const read = [];
  const { controller } = setup({
    readTab: async () => { tabReads += 1; return active; },
    readPage: async (current) => { read.push(current); return request; },
    fetch: async (_url, options) => {
      if (options.method === "POST") return { ok: true, json: async () => answer };
      indexStarted.resolve();
      return indexResponse.promise;
    },
  });
  const opening = controller.open();
  await indexStarted.promise;
  active = { id: 99, key: "other.example/", url: "https://other.example/" };
  indexResponse.resolve({ ok: true, json: async () => index });
  await opening;
  assert.equal(tabReads, 1);
  assert.deepEqual(read, [tab]);
});

test("a failed search offers recovery and an explicit retry can succeed", async () => {
  let attempts = 0;
  const { controller, calls } = setup({
    fetch: async (_url, options) => {
      if (options.method !== "POST") return { ok: true, json: async () => index };
      attempts += 1;
      return attempts === 1
        ? { ok: false, json: async () => ({ error: "budget_exhausted" }) }
        : { ok: true, json: async () => answer };
    },
  });
  await controller.open();
  assert.deepEqual(calls.states.at(-1), { kind: "refused", code: "budget_exhausted" });
  await controller.search();
  assert.equal(attempts, 2);
  assert.equal(calls.states.at(-1).kind, "answer");
});

test("too little text and navigation races make no search request", async () => {
  for (const readPage of [
    async () => null,
    async () => { const error = new Error("Page changed"); error.code = "page_changed"; throw error; },
  ]) {
    const { controller, calls } = setup({ readPage });
    await controller.open();
    assert.equal(calls.fetch.filter((call) => call.options.method === "POST").length, 0);
    assert.ok(["too-little", "refused"].includes(calls.states.at(-1).kind));
  }
});

test("closing while the browser reads prevents sending and late rendering", async () => {
  const reading = deferred();
  const started = deferred();
  const { controller, calls } = setup({
    readPage: async () => { started.resolve(); return reading.promise; },
  });
  const opening = controller.open();
  await started.promise;
  controller.close();
  reading.resolve(request);
  await opening;
  assert.equal(calls.fetch.filter((call) => call.options.method === "POST").length, 0);
  assert.equal(calls.states.at(-1).kind, "searching");
});

test("closing aborts a pending request and ignores its eventual response", async () => {
  const response = deferred();
  const started = deferred();
  let signal;
  const { controller, calls } = setup({
    fetch: async (_url, options) => {
      if (options.method !== "POST") return { ok: true, json: async () => index };
      signal = options.signal;
      started.resolve();
      return response.promise;
    },
  });
  const opening = controller.open();
  await started.promise;
  controller.close();
  assert.equal(signal.aborted, true);
  response.resolve({ ok: true, json: async () => answer });
  await opening;
  assert.equal(calls.states.at(-1).kind, "searching");
});

test("cache failures do not discard a working network lookup", async () => {
  const { controller, calls } = setup({
    storage: {
      get: async () => { throw new Error("Cache unavailable"); },
      set: async () => { throw new Error("Cache unavailable"); },
    },
  });
  await controller.open();
  assert.equal(calls.states.at(-1).kind, "answer");
});
