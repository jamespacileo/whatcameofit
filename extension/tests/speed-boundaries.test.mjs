import assert from "node:assert/strict";
import { test } from "node:test";
import { createPopupController } from "../src/controller.js";

const positive = { about_a_treatment: true, treatment: "EX-1", candidates: [], papers_unchecked: 0 };
const negative = { about_a_treatment: false, candidates: [], papers_unchecked: 0 };
const encoder = new TextEncoder();
const event = (type, result) => encoder.encode(JSON.stringify({ type, result }) + "\n");
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

function setup(overrides = {}) {
  const states = [];
  const writes = [];
  const values = { lookup: { version: 2, savedAt: Date.now(), index: { articles: {}, claims: {}, live: "/api/lookup" } } };
  const controller = createPopupController({
    lookupTimeoutMs: 60,
    site: { url: "https://service.example" },
    storage: { get: async () => values, set: async next => { writes.push(next); Object.assign(values, next); } },
    readTab: async () => ({ id: 1, key: "news.example/report", url: "https://news.example/report" }),
    isCurrentPage: async () => true,
    readPage: async () => ({ text: "A report about EX-1.", links: [], contentFingerprint: "text-print" }),
    describeAnswer: found => found,
    present: state => states.push(state),
    ...overrides,
    fetch: (url, options) => options.method === "POST"
      ? overrides.fetch(url, options) : Promise.resolve(Response.json(values.lookup.index)),
  });
  return { controller, states, values, writes };
}

test("a shared negative caption cannot suppress an image-only claim", async () => {
  let captured = 0;
  const { controller, states, values } = setup({
    lookupTimeoutMs: 1000,
    readPage: async () => ({ text: "Dental revolution", links: [], pageUrl: "https://news.example/report", contentFingerprint: "caption", visualCandidate: true, readableArticle: false }),
    capturePage: async () => { captured++; return { image: { dataUrl: "data:image/jpeg;base64,AA==", width: 1, height: 1 } }; },
    fetch: async (_url, options) => {
      const body = JSON.parse(options.body);
      return Response.json(body.cacheOnly ? { ...negative, cache: { shared: true, checkedAt: Date.now() } } : body.image ? positive : negative);
    },
  });
  try {
    await controller.open();
    assert.equal(captured, 1);
    assert.equal(states.at(-1).shown?.treatment, "EX-1");
    assert.ok(!(values.results ?? []).some(row => row.fingerprint === "caption" && row.found.about_a_treatment === false));
  } finally { controller.close(); }
});

for (const tail of ["eof", "error", "malformed", "deadline"]) {
  test(`navigation after core prevents stale restoration on ${tail}`, async () => {
    let stream;
    let current = true;
    let seenCore;
    const coreVisible = new Promise(resolve => { seenCore = resolve; });
    const states = [];
    const { controller, writes } = setup({
      lookupTimeoutMs: 100,
      isCurrentPage: async () => current,
      fetch: async () => new Response(new ReadableStream({ start(value) { stream = value; stream.enqueue(event("core", positive)); } }), { headers: { "Content-Type": "application/x-ndjson" } }),
      present: state => { states.push(state); if (state.kind === "answer") seenCore(); },
    });
    const opening = controller.open();
    try {
      await coreVisible;
      await pause(0);
      current = false;
      const stateCount = states.length;
      const writeCount = writes.length;
      if (tail === "error") stream.enqueue(encoder.encode('{"type":"error","error":"failed"}\n'));
      if (tail === "malformed") stream.enqueue(encoder.encode('invalid JSON\n'));
      if (tail !== "deadline") stream.close();
      await opening;
      assert.equal(states.length, stateCount, "no late rendering after navigation");
      assert.equal(writes.length, writeCount, "no late recent/result write after navigation");
    } finally { controller.close(); await opening; }
  });
}

test("a truncated stream retains the completed core but never caches it", async () => {
  const { controller, states, values } = setup({
    fetch: async () => new Response(new ReadableStream({ start(stream) { stream.enqueue(event("core", positive)); stream.close(); } }), { headers: { "Content-Type": "application/x-ndjson" } }),
  });
  try {
    await controller.open();
    assert.equal(states.at(-1).kind, "answer");
    assert.equal(states.at(-1).shown?.treatment, "EX-1");
    assert.equal(values.results?.length ?? 0, 0);
  } finally { controller.close(); }
});

test("the overall deadline keeps a completed core when only the stream tail stalls", async () => {
  const { controller, states, values } = setup({
    fetch: async () => new Response(new ReadableStream({ start(stream) { stream.enqueue(event("core", positive)); } }), { headers: { "Content-Type": "application/x-ndjson" } }),
  });
  try {
    await controller.open();
    assert.equal(states.at(-1).kind, "answer");
    assert.equal(states.at(-1).shown?.treatment, "EX-1");
    assert.equal(values.results?.length ?? 0, 0);
  } finally { controller.close(); }
});

test("closing after a core result prevents a late complete event from rendering or saving", async () => {
  let stream;
  let seenCore;
  const coreVisible = new Promise(resolve => { seenCore = resolve; });
  const states = [];
  const { controller, values } = setup({
    lookupTimeoutMs: 500,
    fetch: async () => new Response(new ReadableStream({ start(value) { stream = value; stream.enqueue(event("core", positive)); } }), { headers: { "Content-Type": "application/x-ndjson" } }),
    present: state => { states.push(state); if (state.kind === "answer" && state.shown?.treatment === "EX-1") seenCore(); },
  });
  const opening = controller.open();
  try {
    await Promise.race([coreVisible, pause(300).then(() => { throw new Error("core not displayed"); })]);
    controller.close();
    const count = states.length;
    try { stream.enqueue(event("complete", { ...positive, research: { papers: [], organisations: [] } })); stream.close(); } catch { /* Cancellation may already have closed the reader. */ }
    await opening;
    await pause(10);
    assert.equal(states.length, count);
    assert.equal(values.results?.length ?? 0, 0);
  } finally { controller.close(); await opening; }
});
