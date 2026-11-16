// The popup's lookups end: one deadline over each attempt, a bounded lookup file and a
// bounded shared-result probe. A timeout is never shown as no results.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createPopupController } from "../src/controller.js";

const never = () => new Promise(() => {});
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
async function within(promise, ms = 300) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(new Error("still waiting")), ms); })]);
  } finally { clearTimeout(timer); }
}

const tab = { id: 1, key: "news.example.org/report", url: "https://news.example.org/report" };
const index = { articles: {}, claims: {}, live: "/api/lookup" };
const answer = { about_a_treatment: true, treatment: "EX-1", candidates: [] };
const fresh = { lookup: { version: 2, index, savedAt: Date.now() } };

function setup({ indexFetch = async () => Response.json(index), ...overrides } = {}) {
  const calls = { states: [], writes: [], posts: [] };
  const send = async (_url, options) => { calls.posts.push(options); return { ok: true, json: async () => answer }; };
  const controller = createPopupController({
    lookupTimeoutMs: 30,
    site: { url: "https://whatcameofit.example" },
    storage: { get: async () => fresh, set: async (value) => { calls.writes.push(value); } },
    readTab: async () => tab,
    isCurrentPage: async () => true,
    readPage: async () => ({ text: "A report of EX-1 for a condition.", links: [], contentFingerprint: "print" }),
    describeAnswer: (value) => value,
    present: (state) => calls.states.push(state),
    ...overrides,
    fetch: (url, options) => options.method === "POST" ? (overrides.fetch ?? send)(url, options) : indexFetch(url, options),
  });
  return { controller, calls };
}

test("a stalled response body times out, is aborted, and a retry gets a fresh signal", async () => {
  let first = true;
  const { controller, calls } = setup({
    fetch: async (_url, options) => {
      calls.posts.push(options);
      if (first) { first = false; return { ok: true, json: never }; }
      return { ok: true, json: async () => answer };
    },
  });
  await within(controller.open());
  assert.deepEqual(calls.states.at(-1), { kind: "refused", code: "timeout" });
  assert.equal(calls.posts[0].signal.aborted, true);
  assert.equal(calls.writes.filter(value => !value.lookup).length, 0, "a timeout is not saved as a result");
  await within(controller.search());
  assert.equal(calls.posts[1].signal.aborted, false, "the retry is not poisoned by the aborted attempt");
  assert.equal(calls.states.at(-1).kind, "answer");
  assert.equal(calls.posts.length, 2, "nothing was retried automatically");
  controller.close();
});

test("a slow shared-result probe is abandoned and the search goes on", async () => {
  const { controller, calls } = setup({
    lookupTimeoutMs: 1_000,
    cacheProbeTimeoutMs: 20,
    readPage: async () => ({ text: "A report of EX-1 for a condition.", links: [], pageUrl: tab.url }),
    fetch: async (_url, options) => {
      calls.posts.push(options);
      return JSON.parse(options.body).cacheOnly ? never() : { ok: true, json: async () => answer };
    },
  });
  await within(controller.open());
  assert.equal(calls.posts.length, 2);
  assert.equal(calls.posts[0].signal.aborted, true, "the probe is aborted");
  assert.equal(calls.posts[1].signal.aborted, false);
  assert.equal(calls.states.at(-1).kind, "answer");
  controller.close();
});

test("a stalled lookup file is bounded and aborted", async () => {
  let signal;
  const { controller, calls } = setup({
    indexTimeoutMs: 20,
    storage: { get: async () => ({}), set: async () => {} },
    indexFetch: async (_url, options) => { signal = options.signal; return { ok: true, json: never }; },
  });
  await within(controller.open());
  assert.equal(signal.aborted, true);
  assert.notEqual(calls.states.at(-1).kind, "checking");
  controller.close();
});

test("the automatic screenshot fallback is inside the same deadline", async () => {
  let captureSignal;
  const { controller, calls } = setup({
    readPage: async () => ({ text: "Look", links: [], visualCandidate: true }),
    capturePage: (_tab, signal) => { captureSignal = signal; return never(); },
  });
  await within(controller.open());
  assert.equal(calls.states.at(-1).code, "timeout");
  assert.equal(captureSignal.aborted, true);
  assert.equal(calls.posts.length, 0, "nothing was sent after the deadline");
  controller.close();
});

test("closing during a lookup cancels it with no rendering, even after the deadline", async () => {
  let started;
  const begun = new Promise((resolve) => { started = resolve; });
  const { controller, calls } = setup({
    lookupTimeoutMs: 20,
    fetch: async (_url, options) => { calls.posts.push(options); started(); return never(); },
  });
  const opening = controller.open();
  await begun;
  const count = calls.states.length;
  controller.close();
  assert.equal(calls.posts[0].signal.aborted, true);
  await within(opening);
  await pause(40);
  assert.equal(calls.states.length, count, "nothing is shown after closing");
  assert.equal(calls.states.at(-1).kind, "searching");
});

test("only one lookup is in flight at a time", async () => {
  const { controller, calls } = setup({
    lookupTimeoutMs: 1_000,
    fetch: async (_url, options) => { calls.posts.push(options); await pause(10); return { ok: true, json: async () => answer }; },
  });
  await within(controller.open());
  const one = controller.search();
  const two = controller.search();
  assert.equal(one, two);
  await within(one);
  assert.equal(calls.posts.length, 2);
  controller.close();
});

test("a response from an expired attempt cannot overwrite a successful retry or its saved results", async () => {
  let finishOld;
  let first = true;
  const { controller, calls } = setup({
    fetch: async (_url, options) => {
      calls.posts.push(options);
      if (first) {
        first = false;
        return new Promise(resolve => { finishOld = resolve; });
      }
      return { ok: true, json: async () => answer };
    },
  });
  await within(controller.open());
  assert.equal(calls.states.at(-1).code, "timeout");
  await within(controller.search());
  assert.equal(calls.states.at(-1).shown.treatment, "EX-1");
  const stateCount = calls.states.length;
  const writeCount = calls.writes.length;
  finishOld({ ok: true, json: async () => ({ ...answer, treatment: "Expired answer" }) });
  await pause(10);
  assert.equal(calls.states.length, stateCount);
  assert.equal(calls.writes.length, writeCount);
  controller.close();
});

test("page reading completed after timeout cannot start a request", async () => {
  let finishRead;
  const { controller, calls } = setup({
    readPage: () => new Promise(resolve => { finishRead = resolve; }),
  });
  await within(controller.open());
  assert.equal(calls.states.at(-1).code, "timeout");
  const stateCount = calls.states.length;
  finishRead({ text: "Browser text received too late", links: [] });
  await pause(10);
  assert.equal(calls.posts.length, 0);
  assert.equal(calls.writes.filter(value => !value.lookup).length, 0);
  assert.equal(calls.states.length, stateCount);
  controller.close();
});
