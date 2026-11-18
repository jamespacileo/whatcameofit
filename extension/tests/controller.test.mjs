import assert from "node:assert/strict";
import { test } from "node:test";
import { createPopupController } from "../src/controller.js";
import { remember } from "../src/results.js";

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
    site: { url: "https://whatcameofit.example", key: "whatcameofit.example" },
    readTab: async () => tab,
    readPage: async (current) => { calls.read.push(current); return request; },
    isCurrentPage: async () => true,
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

test("tracked, non-web and disabled-service pages never read the page or start a model request", async () => {
  const claim = { headline: "Reviewed claim", page: "/reviewed", status: "Phase 1 trial" };
  const cases = [
    { current: tab, lookup: { ...index, articles: { [tab.key]: ["reviewed"] }, claims: { reviewed: claim } }, kind: "tracked" },
    { current: { id: 8, key: null, url: "chrome://extensions" }, lookup: index, kind: "no-page" },
    { current: tab, lookup: { ...index, live: null }, kind: "untracked" },
    // The site's own pages: a claim's page shows the claim, any other asks for an article.
    { current: { id: 9, key: "whatcameofit.example/reviewed", url: "https://whatcameofit.example/reviewed" }, lookup: { ...index, claims: { reviewed: claim } }, kind: "tracked" },
    { current: { id: 10, key: "whatcameofit.example/privacy", url: "https://whatcameofit.example/privacy" }, lookup: index, kind: "no-page" },
  ];
  for (const one of cases) {
    const { controller, calls } = setup({
      readTab: async () => one.current,
      storage: { get: async () => ({ lookup: { version: 2, index: one.lookup, savedAt: Date.now() } }) },
      fetch: async (url, options) => { calls.fetch.push({ url, options }); return Response.json(one.lookup); },
    });
    await controller.open();
    assert.equal(calls.states.at(-1).kind, one.kind);
    assert.equal(calls.read.length, 0);
    assert.equal(calls.fetch.length, one.current.key ? 1 : 0);
  }
});

test("a newly published exact-source card supersedes the recent index and saved clinical answer", async () => {
  const claim = { headline: "EX-1 for tinnitus", page: "/ex1-tinnitus", status: "Phase 1 trial" };
  const latest = { ...index, articles: { [tab.key]: ["ex1"] }, claims: { ex1: claim } };
  const writes = [];
  const clinical = { ...answer, about_a_treatment: true, names: ["Topical EX-1"], condition: "Tinnitus in adults", tracked: [] };
  const { controller, calls } = setup({
    storage: {
      get: async () => ({ lookup: { version: 2, index, savedAt: Date.now(), etag: '"old"' },
        results: remember([], tab.key, "article-print", clinical, Date.now() - 1000) }),
      set: async values => writes.push(values),
    },
    readPage: async current => { calls.read.push(current); return { ...request, contentFingerprint: "article-print" }; },
    fetch: async (url, options) => {
      calls.fetch.push({ url, options });
      if (options.method === "POST") return Response.json(clinical);
      return Response.json(latest, { headers: { ETag: '"new"' } });
    },
  });
  await controller.open();
  assert.equal(calls.states.at(-1).kind, "tracked");
  assert.deepEqual(calls.states.at(-1).claims, [claim]);
  assert.equal(calls.read.length, 0);
  assert.equal(calls.fetch.length, 1);
  assert.equal(calls.fetch[0].options.headers["If-None-Match"], '"old"');
  assert.equal(writes.find(value => value.lookup)?.lookup.etag, '"new"');
});

test("an unchanged index uses no response body and reuses the completed clinical answer", async () => {
  const checkedAt = Date.now() - 1000;
  const clinical = { ...answer, about_a_treatment: true, names: ["EX-1"], condition: "Tinnitus", tracked: [] };
  const stored = { lookup: { version: 2, index, savedAt: checkedAt, etag: '"same"' },
    results: remember([], tab.key, "article-print", clinical, checkedAt) };
  const { controller, calls } = setup({
    storage: { get: async () => stored, set: async values => Object.assign(stored, values) },
    readPage: async () => ({ ...request, contentFingerprint: "article-print" }),
    fetch: async (url, options) => {
      calls.fetch.push({ url, options });
      assert.equal(options.headers["If-None-Match"], '"same"');
      assert.equal(options.body, undefined, "no page context is sent with the index request");
      return { status: 304, ok: false, json: () => assert.fail("304 has no body") };
    },
  });
  await controller.open();
  assert.equal(calls.fetch.length, 1);
  assert.equal(calls.states.at(-1).kind, "answer");
  assert.equal(calls.states.at(-1).cachedAt, checkedAt);
  assert.deepEqual(stored.lookup.index, index);
  assert.ok(stored.lookup.savedAt >= checkedAt);
});

test("an updated index removes an old exact-source association", async () => {
  const old = { ...index, articles: { [tab.key]: ["old"] }, claims: { old: { page: "/old", headline: "Old card" } } };
  const { controller, calls } = setup({
    storage: { get: async () => ({ lookup: { version: 2, index: old, savedAt: Date.now() } }), set: async () => {} },
  });
  await controller.open();
  assert.equal(calls.states.at(-1).kind, "answer");
  assert.equal(calls.states.some(state => state.kind === "tracked"), false);
});

test("closing while the saved index loads starts no late revalidation", async () => {
  const saved = deferred();
  const begun = deferred();
  const writes = [];
  const { controller, calls } = setup({
    storage: { get: async key => { if (key !== "lookup") return {}; begun.resolve(); return saved.promise; }, set: async value => writes.push(value) },
  });
  const opening = controller.open();
  await begun.promise;
  controller.close();
  saved.resolve({ lookup: { version: 2, index, etag: '"old"', savedAt: Date.now() } });
  await opening;
  assert.equal(calls.fetch.length, 0);
  assert.equal(writes.length, 0);
  assert.deepEqual(calls.states.map(state => state.kind), ["checking"]);
});

test("failed or stalled revalidation uses the dated saved index and never writes a late response", async () => {
  const savedAt = Date.now() - 1000;
  const saved = { ...index, articles: { [tab.key]: ["old"] }, claims: { old: { page: "/old", headline: "Saved card" } } };
  for (const failure of ["offline", "stalled"]) {
    const response = deferred();
    const writes = [];
    let signal;
    const { controller, calls } = setup({
      indexTimeoutMs: 20,
      storage: { get: async () => ({ lookup: { version: 2, index: saved, savedAt } }), set: async value => writes.push(value) },
      fetch: async (_url, options) => {
        signal = options.signal;
        if (failure === "offline") throw new Error("offline");
        return response.promise;
      },
    });
    await controller.open();
    assert.equal(calls.states.at(-1).kind, "tracked");
    assert.equal(calls.states.at(-1).savedAt, savedAt);
    assert.equal(calls.read.length, 0);
    if (failure === "stalled") assert.equal(signal.aborted, true);
    response.resolve(Response.json(index));
    await new Promise(resolve => setImmediate(resolve));
    assert.equal(writes.some(value => value.lookup), false);
    controller.close();
  }
});

test("changing automatic search settings preserves own-site pages without reading or saving them", async () => {
  const claim = { headline: "Reviewed claim", page: "/reviewed", status: "Phase 1 trial" };
  const lookup = { ...index, claims: { reviewed: claim } };
  for (const path of ["", "/privacy", "/reviewed"]) {
    for (const enabled of [false, true]) {
      const writes = [];
      const { controller, calls } = setup({
        requiresSharingConsent: true,
        readTab: async () => ({ id: 9, key: `whatcameofit.example${path}`, url: `https://whatcameofit.example${path}` }),
        storage: {
          get: async () => ({ lookup: { version: 2, index: lookup, savedAt: Date.now() }, sharing: { version: 1, enabled } }),
          set: async (values) => { writes.push(values); },
        },
        fetch: async (url, options) => { calls.fetch.push({ url, options }); return Response.json(lookup); },
      });
      await controller.open();
      const original = calls.states.at(-1);
      for (const setting of [!enabled, enabled]) {
        controller.sharingView();
        await (setting ? controller.enableSharing() : controller.disableSharing());
        assert.deepEqual(calls.states.at(-1), original, `${path || "home"}: setting ${setting}`);
      }
      assert.equal(calls.read.length, 0);
      assert.equal(calls.fetch.filter(call => call.options.method === "POST").length, 0);
      assert.ok(writes.every((values) => !Object.hasOwn(values, "recent")));
      controller.close();
    }
  }
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
  await started.promise;
  const retries = [controller.search(), controller.search()];
  reading.resolve(request);
  await Promise.all([first, second, ...retries]);
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

test("unreadable pages, navigation during reading and closed tabs send no search request", async () => {
  const cases = [
    ["unreadable page", { readPage: async () => null }, { kind: "too-little" }],
    ["navigation during reading", {
      readPage: async () => { throw Object.assign(new Error("Page changed"), { code: "page_changed" }); },
    }, { kind: "refused", code: "page_changed" }],
    ["closed tab", { isCurrentPage: async () => { throw new Error("Tab closed"); } }, { kind: "refused", code: "page_changed" }],
  ];
  for (const [scenario, overrides, expected] of cases) {
    const { controller, calls } = setup(overrides);
    await controller.open();
    assert.ok(calls.fetch.every(call => call.options.method !== "POST"), scenario);
    const { kind, code } = calls.states.at(-1);
    assert.equal(kind, expected.kind, scenario);
    assert.equal(code, expected.code, scenario);
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
