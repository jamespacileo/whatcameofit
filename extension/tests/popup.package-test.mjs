import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { test } from "node:test";
import { setTimeout as delay } from "node:timers/promises";

import { dist, installGlobals, launchEntry, manifest, SITE } from "./package-support.mjs";
import { heroPhoto, sciencePage } from "./science-page.mjs";

const { parseHTML } = createRequire(new URL("../../site/package.json", import.meta.url))("linkedom");
const popupUrl = new URL(manifest.action.default_popup, dist);
const popupHtml = await readFile(popupUrl, "utf8");
const postUrl = "https://x.com/research/status/123456789";
const shortLink = "https://t.co/AbCdEf";
const article = "https://news.example.org/tooth-regrowth";
const shortPost = { address: postUrl, focusText: "Read this", links: [{ href: shortLink, text: "Read the article" }] };
const treatment = { about_a_treatment: true, treatment: "EX-1", condition: "missing teeth", candidates: [] };
const noTreatment = { about_a_treatment: false, candidates: [], papers_unchecked: 0, gist: "A biomarker report." };

async function until(check, description) {
  const deadline = Date.now() + 2000;
  while (!check()) {
    assert.ok(Date.now() < deadline, description);
    await delay(5);
  }
}

function popup(t, collected, { media = [], answer = treatment } = {}) {
  const tab = { id: 7, windowId: 1, url: collected.address };
  const stored = { sharing: { version: 1, enabled: true } };
  const lookups = [], reads = [], inspected = [];
  const shortResponse = Promise.withResolvers();
  let resolvingLink = false;
  let captures = 0;
  let window;

  function close() {
    if (window) window.dispatchEvent(new window.Event("pagehide"));
  }
  function resolveLink() {
    shortResponse.resolve(`<title>${article}</title>`);
  }
  t.after(() => { close(); resolveLink(); });
  installGlobals(t, {
    window: undefined,
    document: undefined,
    browser: {
      storage: { local: { get: async () => structuredClone(stored), set: async (values) => Object.assign(stored, structuredClone(values)) } },
      tabs: {
        query: async () => [{ ...tab }],
        captureVisibleTab: async () => { captures += 1; throw new Error("Unexpected screenshot"); },
      },
      scripting: {
        async executeScript({ target, func, args }) {
          if (func.name === "inspectVisible") {
            inspected.push(args);
            return [{ result: { address: tab.url, media, sensitive: false, selectionOnly: collected.selection?.length >= 20 } }];
          }
          reads.push(target.tabId);
          return [{ result: { title: "Research report", selection: "", head: "", focusHtml: "", ...collected, address: tab.url } }];
        },
      },
    },
    async fetch(url, options) {
      if (url === `${SITE.url}/lookup/2.json`) return Response.json({ articles: {}, claims: {}, live: "/api/lookup" });
      if (url === shortLink) {
        resolvingLink = true;
        return new Response(await shortResponse.promise);
      }
      assert.equal(url, `${SITE.url}/api/lookup`);
      assert.equal(options.method, "POST");
      const body = JSON.parse(options.body);
      lookups.push(body);
      return Response.json(body.cacheOnly ? { cacheMiss: true } : answer);
    },
  });

  return {
    tab, stored, lookups, reads, inspected, resolveLink,
    get posts() { return lookups.filter(body => !body.cacheOnly); },
    get captures() { return captures; },
    async open() {
      close();
      window = parseHTML(popupHtml);
      const { document } = window;
      Object.assign(globalThis, { window, document });
      const script = document.querySelector('script[type="module"][src]');
      assert.ok(script, "the packaged popup loads a module");
      await launchEntry(new URL(script.getAttribute("src"), popupUrl));
    },
    waitForShortLink: () => until(() => resolvingLink, "the popup did not request the short link"),
    async result() {
      const view = window.document.querySelector("main");
      await until(() => view.getAttribute("aria-busy") === "false", "the popup did not finish the lookup");
      return view.textContent;
    },
  };
}

test("packaged popup automatically searches a short post using its resolved article link", async (t) => {
  const session = popup(t, shortPost, { media: heroPhoto });
  session.resolveLink();
  await session.open();
  assert.match(await session.result(), /EX-1.*missing teeth/);
  assert.deepEqual(session.reads, [7]);
  assert.equal(session.posts.length, 1);
  const [request] = session.posts;
  assert.equal(request.text, "Read this");
  assert.deepEqual(request.links, [article]);
  assert.equal(request.platform, "X");
  assert.equal(request.pageUrl, postUrl);
  assert.equal(request.claimResults, true);
  assert.ok(request.timeBudgetMs > 0 && request.timeBudgetMs <= 44_000);
  assert.equal(request.image, undefined);
  assert.equal(session.captures, 0);
});

test("packaged popup sends no page content after the same tab navigates during link resolution", async (t) => {
  const session = popup(t, shortPost);
  await session.open();
  await session.waitForShortLink();
  await until(() => session.lookups.length > 0, "the address-only probe did not start before navigation");
  const beforeNavigation = session.lookups.length;
  session.tab.url = "https://x.com/research/status/987654321";
  session.resolveLink();
  const result = await session.result();
  assert.equal(session.lookups.length, beforeNavigation, "no lookup request may start after navigation");
  assert.deepEqual(session.posts, []);
  assert.match(result, /The page changed/);
});

test("packaged popup keeps a YouTube text answer when only playback advances", async (t) => {
  const address = "https://www.youtube.com/watch?v=EX_test0001&t=30";
  const scope = { address, selector: 'ytd-watch-flexy[video-id="EX_test0001"]', videoOnly: true };
  const media = [{ kind: "video", identity: "blob:temporary-30", time: 30 }];
  const session = popup(t, {
    address, mediaScope: scope, focusText: "A synthetic video report describes EX-1 for missing teeth. ".repeat(8), links: [],
  }, { media });
  await session.open();
  assert.match(await session.result(), /EX-1.*missing teeth/);
  media[0] = { kind: "video", identity: "blob:temporary-60", time: 60 };
  await session.open();
  assert.match(await session.result(), /Previous result/);
  assert.deepEqual(session.inspected, [[scope], [scope]]);
  assert.equal(session.posts.length, 1);
  assert.equal(session.posts[0].platform, "YouTube");
  assert.equal(session.posts[0].pageUrl, "https://www.youtube.com/watch?v=EX_test0001");
});

test("packaged popup probes while links resolve and saves an article's text answer without a screenshot", async (t) => {
  const page = sciencePage();
  page.links.push({ href: shortLink, text: "more" });
  const session = popup(t, page, { media: heroPhoto, answer: noTreatment });
  await session.open();
  await session.waitForShortLink();
  await until(() => session.lookups.length > 0, "the address-only probe did not start while the link was pending");
  assert.deepEqual(session.lookups, [{ cacheOnly: true, pageUrl: page.address, claimResults: true }]);
  session.resolveLink();
  assert.match(await session.result(), /A specific treatment and condition could not be identified/);
  assert.equal(session.posts.length, 1);
  const [request] = session.posts;
  for (const internal of ["readableArticle", "visualCandidate", "contentFingerprint", "selectionOnly", "image"]) {
    assert.equal(request[internal], undefined, internal);
  }
  assert.equal(request.stream, true);
  assert.equal(session.captures, 0);
  assert.equal(session.stored.results.length, 1);
  assert.equal(session.stored.results[0].found.about_a_treatment, false);
  assert.ok(session.stored.results[0].at > 0);
  assert.doesNotMatch(JSON.stringify(session.stored), /biological signature|ringing in the ears|data:image/);
});

test("packaged popup sends only the selected words and keeps no reusable result", async (t) => {
  const selection = "These selected words describe a blood marker for ringing ears.";
  const session = popup(t, sciencePage({ selection }), { media: heroPhoto, answer: noTreatment });
  await session.open();
  assert.match(await session.result(), /A specific treatment and condition could not be identified/);
  assert.equal(session.lookups.length, 1);
  assert.equal(session.posts.length, 1);
  const [request] = session.posts;
  assert.equal(request.text, selection);
  assert.equal(request.pageUrl, undefined, "a selected-text lookup omits the page address");
  assert.equal(request.selectionOnly, undefined);
  assert.deepEqual(request.links, []);
  assert.equal(request.image, undefined);
  assert.equal(session.captures, 0);
  assert.equal(session.stored.results, undefined);
});
