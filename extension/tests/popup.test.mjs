// Exercise the real popup entry point, controller, page composer and short-link
// reader together. Only the browser, network and final DOM renderer are stand-ins.
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const postA = "https://x.com/research/status/123456789";
const postB = "https://x.com/research/status/987654321";
const shortLink = "https://t.co/AbCdEf";
const article = "https://news.example.org/tooth-regrowth";

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

async function runPopup(navigate, words = "EX-1 is being studied as a treatment for missing teeth.") {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "thenwhat-popup-"));
  const globals = ["browser", "document", "window", "fetch", "__popupTestCapture"];
  const saved = new Map(globals.map((name) => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  const shortStarted = deferred();
  const shortResponse = deferred();
  const complete = deferred();
  const posts = [];
  const states = [];
  const events = {};
  let current = { id: 7, url: postA };
  let confirmedTab = null;
  let reads = 0;
  try {
    const files = {
      "popup.js": "extension/src/popup.js",
      "controller.js": "extension/src/controller.js",
      "lookup.js": "extension/src/lookup.js",
      "open-page.js": "extension/src/open-page.js",
      "short-links.js": "extension/src/short-links.js",
      "article-key.js": "site/src/lib/article-key.mjs",
      "lookup-match.js": "site/src/lib/lookup-match.mjs",
      "page.js": "site/worker/page.mjs",
      "live-lookup.js": "site/src/lib/live-lookup.mjs",
      "notices.ts": "site/src/lib/notices.ts",
    };
    for (const [name, source] of Object.entries(files)) {
      const content = (await fs.readFile(path.join(root, source), "utf8")).replaceAll("./article-key.mjs", "./article-key.js");
      await fs.writeFile(path.join(directory, name), content);
    }
    await fs.writeFile(path.join(directory, "package.json"), '{"type":"module"}');
    await fs.writeFile(path.join(directory, "config.js"), 'export const SITE = {name:"Test",url:"https://whatcameofit.example"};');
    await fs.writeFile(path.join(directory, "view.js"), 'export function render(root,state){globalThis.__popupTestCapture(state);}');

    globalThis.document = { querySelector: () => ({ textContent: "" }) };
    globalThis.window = { addEventListener: (name, callback) => { events[name] = callback; }, close() {} };
    globalThis.browser = {
      storage: { local: { get: async () => ({}), set: async () => {} } },
      tabs: {
        query: async () => [current],
        get: async (id) => { confirmedTab = id; return current; },
      },
      scripting: {
        executeScript: async ({ target }) => {
          assert.equal(target.tabId, 7);
          reads += 1;
          return [{ result: {
            address: postA, title: "Research post", selection: "", head: "", focusHtml: "",
            focusText: words,
            links: [{ href: shortLink, text: "Read the article" }],
          } }];
        },
      },
    };
    globalThis.fetch = async (url, options) => {
      if (url.endsWith("/lookup.json")) return Response.json({ articles: {}, claims: {}, live: "/api/lookup" });
      if (url === shortLink) {
        shortStarted.resolve();
        return shortResponse.promise;
      }
      assert.equal(url, "https://whatcameofit.example/api/lookup");
      posts.push(JSON.parse(options.body));
      return Response.json({ about_a_treatment: false, candidates: [] });
    };
    globalThis.__popupTestCapture = (state) => {
      states.push(state);
      if (state.kind === "answer" || state.kind === "refused") complete.resolve();
    };

    await import(pathToFileURL(path.join(directory, "popup.js")));
    await shortStarted.promise;
    if (navigate) current = { ...current, url: postB };
    shortResponse.resolve(new Response(`<title>${article}</title>`));
    await complete.promise;
    return { posts, states, reads, confirmedTab };
  } finally {
    events.pagehide?.();
    for (const [name, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor);
      else delete globalThis[name];
    }
    await fs.rm(directory, { recursive: true, force: true });
  }
}

test("actual popup glue automatically reads once, resolves the link and sends one request", { timeout: 5000 }, async () => {
  const result = await runPopup(false);
  assert.equal(result.reads, 1);
  assert.equal(result.confirmedTab, 7);
  assert.equal(result.posts.length, 1);
  assert.deepEqual(result.posts[0].links, [article]);
  assert.equal(result.posts[0].platform, "X");
  assert.doesNotMatch(JSON.stringify(result.posts[0]), /x\.com|status\/123456789/);
  assert.deepEqual(result.states.map((state) => state.kind), ["checking", "searching", "answer"]);
});

test("actual popup glue refuses navigation during a paused short-link resolution", { timeout: 5000 }, async () => {
  const result = await runPopup(true);
  assert.equal(result.reads, 1);
  assert.deepEqual(result.posts, []);
  assert.deepEqual(result.states.at(-1), { kind: "refused", code: "page_changed" });
  assert.equal(result.confirmedTab, 7);
});

test("actual popup glue follows an article from a short post", { timeout: 5000 }, async () => {
  const result = await runPopup(false, "Read this");
  assert.equal(result.posts.length, 1);
  assert.equal(result.posts[0].text, "Read this");
  assert.deepEqual(result.posts[0].links, [article]);
});
