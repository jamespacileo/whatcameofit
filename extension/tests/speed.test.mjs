// Faster popup lookups that stay correct: a staged answer shown as soon as its clinical
// part is complete, completed answers reused for unchanged content, an ordinary article
// read from its words without an automatic screenshot, and an early shared-result probe
// that respects selection, private windows and navigation. All pages are made up.
import assert from "node:assert/strict";
import { test } from "node:test";

import { readAddress } from "../../site/src/lib/lookup-match.mjs";
import { pageAsText, readPage } from "../../site/worker/page.mjs";
import { createPopupController, lookupEvents } from "../src/controller.js";
import { composeRequest, fingerprintInput, readableArticle } from "../src/open-page.js";
import { RESULT_TTL, completed, remember, reusable } from "../src/results.js";
import { SCIENCE, PARAGRAPHS, STRUCTURED, sciencePage, heroPhoto } from "./science-page.mjs";

const shared = { readAddress, readPage, pageAsText };
const never = () => new Promise(() => {});
const pause = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}
async function until(check, ms = 500) {
  const started = Date.now();
  while (!check()) {
    if (Date.now() - started > ms) throw new Error("still waiting");
    await pause(2);
  }
}

// --- the page: an ordinary article or a media post ---------------------------------------

const REDDIT = "https://www.reddit.com/r/science/comments/abc123/dental_revolution/";
const redditPost = {
  address: REDDIT, title: "Dental revolution : r/science", selection: "",
  head: '<head><meta property="og:type" content="article"><script type="application/ld+json">{"@type":"DiscussionForumPosting","headline":"Dental revolution"}</script></head>',
  focusHtml: '<shreddit-post post-title="Dental revolution"><a href="https://preview.redd.it/teeth.png">image</a></shreddit-post>',
  focusText: "r/science\nu/poster\nDental revolution",
  links: [{ href: "https://www.reddit.com/r/science/", text: "r/science" }, { href: "https://www.reddit.com/user/poster/", text: "u/poster" }, { href: "https://preview.redd.it/teeth.png", text: "image" }],
  postTitle: "Dental revolution", contentHref: null,
  structured: ['{"@type":"DiscussionForumPosting","headline":"Dental revolution"}'],
};
const judge = (collected, address, media = heroPhoto) => readableArticle(collected, composeRequest(collected, address, shared), address, { readAddress, media });

test("the ScienceAlert tinnitus report qualifies as an ordinary readable article despite its photo", () => {
  const request = composeRequest(sciencePage(), SCIENCE, shared);
  assert.ok(request.text.length >= 1000, "its words are read");
  assert.deepEqual(request.links, ["https://doi.org/10.1000/example.tinnitus"]);
  assert.equal(judge(sciencePage(), SCIENCE), true);
});

test("the Reddit Dental revolution post does not qualify, even if it calls itself an article", () => {
  // Too little text of its own: the popup sends its title with the image, as a Reddit post.
  assert.equal(composeRequest(redditPost, REDDIT, shared), null);
  const request = { text: redditPost.postTitle, links: [], platform: "Reddit" };
  assert.equal(readableArticle(redditPost, request, REDDIT, { readAddress, media: heroPhoto }), false);
  assert.equal(readableArticle(redditPost, { ...request, platform: undefined }, REDDIT, { readAddress, media: heroPhoto }), false);
  // Its words and type aside, a post is never treated as an ordinary article.
  const long = { ...redditPost, focusText: `r/science\n${PARAGRAPHS.replace(/<\/?p>/g, "")}` };
  assert.equal(judge(long, REDDIT), false);
});

test("media, cues, posts, short or unlabelled pages and selections keep the screenshot fallback", () => {
  const cases = {
    "a visible video": [sciencePage(), heroPhoto.concat({ ...heroPhoto[0], kind: "video" })],
    "a visible canvas": [sciencePage(), [{ ...heroPhoto[0], kind: "canvas" }]],
    "a claim said to be in a picture": [sciencePage({ focusHtml: sciencePage().focusHtml.replace("</article>", "<p>The results are shown in the infographic below.</p></article>") }), heroPhoto],
    "a pointer to a video": [sciencePage({ focusHtml: sciencePage().focusHtml.replace("</article>", "<p>Watch the video above for the full claim.</p></article>") }), heroPhoto],
    "a social posting": [sciencePage({ head: "<head></head>", structured: ['{"@type":"SocialMediaPosting"}'] }), heroPhoto],
    "a live blog": [sciencePage({ structured: [STRUCTURED, '{"@type":"LiveBlogPosting"}'] }), heroPhoto],
    "a video page": [sciencePage({ head: '<head><meta property="og:type" content="video.other"></head>', structured: [STRUCTURED] }), heroPhoto],
    "no structured data": [sciencePage({ head: "<head><title>x</title></head>", structured: [] }), heroPhoto],
    "malformed structured data": [sciencePage({ head: "<head></head>", structured: ["{not json"] }), heroPhoto],
    "a short report": [sciencePage({ focusHtml: "<article><h1>Ear study</h1><p>A short note about a blood marker for ringing ears.</p></article>" }), heroPhoto],
    "a selection": [sciencePage({ selection: "the reader chose these words themselves" }), heroPhoto],
  };
  for (const [name, [collected, media]] of Object.entries(cases)) {
    assert.equal(judge(collected, SCIENCE, media), false, name);
  }
  assert.equal(readableArticle(sciencePage(), null, SCIENCE, { readAddress }), false);
});

test("an ordinary article's fingerprint ignores where its photo sits; other pages' do not", () => {
  const request = { text: "words", links: ["https://doi.org/10.1/x"], readableArticle: true };
  const scrolled = [{ ...heroPhoto[0], top: -200 }];
  assert.deepEqual(fingerprintInput(request, heroPhoto), fingerprintInput(request, scrolled));
  assert.equal(JSON.stringify(fingerprintInput(request, heroPhoto)).includes("ear.jpg"), false);
  const media = { ...request, readableArticle: false };
  assert.notDeepEqual(fingerprintInput(media, heroPhoto), fingerprintInput(media, scrolled));
  assert.equal(fingerprintInput(media, heroPhoto, { videoOnly: true }).media, null);
});

// --- saved results --------------------------------------------------------------------------

const negative = { about_a_treatment: false, treatment: null, condition: null, candidates: [], papers_unchecked: 0, gist: "A biomarker report." };
const positive = { about_a_treatment: true, treatment: "EX-1", condition: "tinnitus", candidates: [], papers_unchecked: 0 };

test("only whole answers are kept: no errors, misses, partial streams or answers missing a paper", () => {
  const now = Date.now();
  for (const unfinished of [{ error: "failed" }, { cacheMiss: true }, { ...positive, incomplete: true }, { ...positive, papers_unchecked: 1 },
    { about_a_treatment: false }, { ...negative, papers_unchecked: undefined }, null]) {
    assert.equal(completed(unfinished), false, JSON.stringify(unfinished));
    assert.deepEqual(remember([], "page", "print", unfinished, now), []);
  }
  const kept = remember([], "page", "print", negative, now);
  assert.equal(kept[0].found.gist, undefined, "the model's summary is not kept");
  assert.equal(reusable(kept, "page", "print", now + 1).found.about_a_treatment, false);
  assert.equal(reusable(kept, "page", "print", now + RESULT_TTL), null);
  for (const version of [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]) {
    assert.equal(reusable([{ ...kept[0], version }], "page", "print", now + 1), null, "entries kept before the corpus corrections are not reused");
  }
});

test("a shared answer kept with its earlier date does not push out newer saved answers; ten at most", () => {
  const now = Date.now();
  let entries = [];
  for (let one = 0; one < 12; one += 1) entries = remember(entries, `page-${one}`, "print", positive, now - one);
  assert.equal(entries.length, 10);
  entries = remember(entries, "shared-page", "print", positive, now - 3_600_000);
  assert.equal(entries.length, 10);
  assert.equal(entries[0].at, now - 3_600_000);
  assert.deepEqual(entries.slice(1).map((entry) => entry.key), ["page-11", "page-10", "page-9", "page-8", "page-7", "page-6", "page-5", "page-4", "page-3"]);
});

// --- reading a staged answer -----------------------------------------------------------------

const encoder = new TextEncoder();
function staged() {
  let sink;
  const state = { cancelled: false };
  const body = new ReadableStream({ start(controller) { sink = controller; }, cancel() { state.cancelled = true; } });
  return {
    state,
    response: new Response(body, { headers: { "Content-Type": "application/x-ndjson; charset=utf-8" } }),
    // A reader that has gone cancels the body: what the service sends after that is dropped.
    send: (event) => { try { sink.enqueue(encoder.encode(`${JSON.stringify(event)}\n`)); } catch { /* cancelled */ } },
    bytes: (bytes) => { try { sink.enqueue(bytes); } catch { /* cancelled */ } },
    close: () => { try { sink.close(); } catch { /* cancelled */ } },
  };
}
async function collect(response, signal, options) {
  const events = [];
  for await (const event of lookupEvents(response, signal, options)) events.push(event);
  return events;
}

test("events split anywhere, a character across chunks included, are read whole", async () => {
  const text = `${JSON.stringify({ type: "core", result: { treatment: "Prüfmittel – EX‑1 ✓" } })}\n\n${JSON.stringify({ type: "complete", result: { treatment: "Prüfmittel – EX‑1 ✓", research: {} } })}\n`;
  const bytes = encoder.encode(text);
  for (const size of [1, 2, 3, 7, 64]) {
    const stream = staged();
    const reading = collect(stream.response);
    for (let at = 0; at < bytes.length; at += size) stream.bytes(bytes.slice(at, at + size));
    stream.close();
    const events = await reading;
    assert.deepEqual(events.map((event) => event.type), ["core", "complete"], `chunks of ${size}`);
    assert.equal(events[1].result.treatment, "Prüfmittel – EX‑1 ✓");
  }
});

test("malformed, cut-off, invalid or oversized input is refused", async () => {
  const inputs = {
    "not JSON": "{oops}\n",
    "an unknown event": '{"type":"surprise","result":{}}\n',
    "a result that is not an object": '{"type":"core","result":[1]}\n',
    "a cut-off line": '{"type":"complete","result":{"treat',
    "bad UTF-8": new Uint8Array([0x7b, 0xff, 0xfe, 0x7d, 0x0a]),
  };
  for (const [name, input] of Object.entries(inputs)) {
    const stream = staged();
    const reading = collect(stream.response);
    stream.bytes(typeof input === "string" ? encoder.encode(input) : input);
    stream.close();
    await assert.rejects(reading, { message: "malformed" }, name);
  }
  const big = staged();
  const reading = collect(big.response, null, { maxBytes: 100 });
  big.bytes(new Uint8Array(101).fill(0x20));
  await assert.rejects(reading, { message: "malformed" });
  assert.equal(big.state.cancelled, true, "an oversized body is cancelled");
  // A last line without its newline still counts when it is whole.
  const whole = staged();
  const ending = collect(whole.response);
  whole.bytes(encoder.encode('{"type":"complete","result":{"treatment":"EX-1"}}'));
  whole.close();
  assert.equal((await ending)[0].type, "complete");
});

test("aborting stops reading and cancels the body", async () => {
  const stream = staged();
  const stop = new AbortController();
  const reading = collect(stream.response, stop.signal);
  stream.send({ type: "core", result: positive });
  await pause(5);
  stop.abort();
  await assert.rejects(reading, { name: "AbortError" });
  assert.equal(stream.state.cancelled, true);
});

// --- the popup with a staged answer ----------------------------------------------------------

const tab = { id: 7, windowId: 1, key: "sciencealert.com/report", url: "https://www.sciencealert.com/report" };
const index = { articles: {}, claims: {}, live: "/api/lookup" };
const articleRequest = { text: "A complete ordinary article. ".repeat(60), links: [], pageUrl: tab.url, contentFingerprint: "article-print", readableArticle: true, visualCandidate: true };
function popup(overrides = {}) {
  const stored = { lookup: { version: 2, index, savedAt: Date.now() } };
  const calls = { states: [], posts: [], probes: [], captures: 0, writes: [] };
  // One staged body per paid request, the first ready before it is asked for.
  const streams = [staged()];
  let current = true;
  const send = async (_url, options) => {
    const body = JSON.parse(options.body);
    if (body.cacheOnly) { calls.probes.push(body); return Response.json({ cacheMiss: true }); }
    calls.posts.push({ body, signal: options.signal });
    if (calls.posts.length > streams.length) streams.push(staged());
    return streams[calls.posts.length - 1].response;
  };
  const controller = createPopupController({
    site: { url: "https://service.example.org" },
    storage: { get: async () => stored, set: async (values) => { calls.writes.push(values); Object.assign(stored, values); } },
    readTab: async () => tab,
    isCurrentPage: async () => current,
    readPage: async () => articleRequest,
    capturePage: async () => { calls.captures += 1; return { image: { dataUrl: "data:image/jpeg;base64,AAAA", width: 1, height: 1 }, pageUrl: tab.url }; },
    describeAnswer: (found) => ({ ...found }),
    present: (state) => calls.states.push(state),
    ...overrides,
    fetch: (url, options) => options.method === "POST"
      ? (overrides.fetch ?? send)(url, options) : Promise.resolve(Response.json(stored.lookup.index)),
  });
  return { controller, calls, stored, stream: streams[0], streams, navigate: () => { current = false; } };
}
const answers = (calls) => calls.states.filter((state) => state.kind === "answer");

function endStream(stream, ending) {
  if (ending === "deadline") return;
  if (ending === "error") stream.send({ type: "error", error: "failed" });
  if (ending === "malformed") stream.bytes(encoder.encode("{broken\n"));
  stream.close();
}

test("a slow enrichment shows the completed core with research loading, then the full answer, from one request", async () => {
  const { controller, calls, stored, stream } = popup();
  const opening = controller.open();
  await until(() => calls.posts.length === 1);
  assert.equal(calls.posts[0].body.stream, true);
  assert.equal(calls.posts[0].body.readableArticle, undefined, "internal reading hints are not sent");
  stream.send({ type: "core", result: { ...positive, candidates: [{ id: "NCT00000001" }] }, timings: { core_ms: 900, note: "text" } });
  await until(() => answers(calls).length === 1);
  const first = answers(calls)[0];
  assert.equal(first.research, "loading");
  assert.equal(first.shown.treatment, "EX-1");
  assert.equal(typeof first.timings.core_ms, "number");
  assert.equal(first.timings.service_note, undefined, "only numbers are timed");
  assert.equal(stored.results, undefined, "a core answer is not kept");
  stream.send({ type: "complete", result: { ...positive, candidates: [{ id: "NCT00000001" }], research: { papers: [], organisations: [] } } });
  stream.close();
  await opening;
  const last = calls.states.at(-1);
  assert.equal(last.kind, "answer");
  assert.equal(last.research, undefined);
  assert.deepEqual(last.shown.research, { papers: [], organisations: [] });
  assert.ok(last.timings.complete_ms >= last.timings.core_ms);
  assert.equal(stored.results.length, 1);
  assert.equal(calls.posts.length, 1, "no second paid lookup");
  assert.equal(calls.captures, 0);
  controller.close();
});

test("a stream that ends, errs or turns malformed after its core keeps the core, says research is incomplete, and keeps nothing", async () => {
  for (const ending of ["end of stream", "error", "malformed"]) {
    const { controller, calls, stored, stream } = popup();
    const opening = controller.open();
    await until(() => calls.posts.length === 1);
    stream.send({ type: "core", result: positive });
    endStream(stream, ending);
    await opening;
    const last = calls.states.at(-1);
    assert.equal(last.kind, "answer", ending);
    assert.equal(last.research, "incomplete", ending);
    assert.equal(last.shown.treatment, "EX-1", ending);
    assert.equal(stored.results, undefined, ending);
    controller.close();
  }
});

test("the deadline after a core keeps the core rather than a timeout, cancels the body and keeps nothing", async () => {
  const { controller, calls, stored, stream } = popup({ lookupTimeoutMs: 60 });
  const opening = controller.open();
  await until(() => calls.posts.length === 1);
  stream.send({ type: "core", result: positive });
  await opening;
  const last = calls.states.at(-1);
  assert.equal(last.kind, "answer");
  assert.equal(last.research, "incomplete");
  assert.equal(last.shown.treatment, "EX-1");
  assert.equal(calls.posts[0].signal.aborted, true);
  await until(() => stream.state.cancelled);
  const count = calls.states.length;
  stream.send({ type: "complete", result: positive });
  await pause(10);
  assert.equal(calls.states.length, count, "a late complete event is not shown");
  assert.equal(stored.results, undefined);
  controller.close();
});

test("closing or navigating between events stops rendering, saving and further requests", async () => {
  for (const leave of ["close", "navigate"]) {
    const { controller, calls, stored, stream, navigate } = popup();
    const opening = controller.open();
    await until(() => calls.posts.length === 1);
    stream.send({ type: "core", result: positive });
    await until(() => answers(calls).length === 1);
    if (leave === "close") controller.close(); else navigate();
    const count = calls.states.length;
    const writeCount = calls.writes.length;
    stream.send({ type: "complete", result: positive });
    stream.close();
    await opening;
    if (leave === "close") assert.equal(calls.states.length, count, "nothing renders after closing");
    else assert.deepEqual(calls.states.at(-1), { kind: "refused", code: "page_changed" });
    assert.equal(stored.results, undefined, leave);
    assert.equal(calls.writes.length, writeCount, leave);
    assert.equal(calls.posts.length, 1, leave);
    assert.equal(calls.captures, 0, leave);
    controller.close();
  }
});

test("a stream that ends after navigation does not restore or save the old answer", async () => {
  for (const ending of ["end of stream", "error", "malformed", "deadline"]) {
    const { controller, calls, stream, navigate } = popup({ lookupTimeoutMs: 150 });
    const opening = controller.open();
    try {
      await until(() => calls.posts.length === 1);
      stream.send({ type: "core", result: positive });
      await until(() => answers(calls).length === 1);
      navigate();
      const stateCount = calls.states.length;
      const writeCount = calls.writes.length;
      endStream(stream, ending);
      await opening;
      assert.equal(calls.states.length, stateCount, `no late rendering on ${ending}`);
      assert.equal(calls.writes.length, writeCount, `no late write on ${ending}`);
    } finally {
      controller.close();
      await opening;
    }
  }
});

test("a failure before the core is a refusal with its code, never an empty answer", async () => {
  for (const [event, code] of [[{ type: "error", status: 503, error: "budget_exhausted" }, "budget_exhausted"], [null, "failed"]]) {
    const { controller, calls, stored, stream } = popup();
    const opening = controller.open();
    await until(() => calls.posts.length === 1);
    if (event) stream.send(event); else stream.bytes(encoder.encode("not json\n"));
    stream.close();
    await opening;
    assert.equal(calls.states.at(-1).kind, "refused");
    assert.equal(calls.states.at(-1).code, code);
    assert.equal(answers(calls).length, 0);
    assert.equal(stored.results, undefined);
    controller.close();
  }
});

test("a media page's text-only non-treatment reading is neither shown nor kept; its screenshot follows", async () => {
  const media = { ...articleRequest, readableArticle: false };
  const { controller, calls, stored, stream, streams } = popup({ readPage: async () => media });
  const opening = controller.open();
  await until(() => calls.posts.length === 1);
  stream.send({ type: "core", result: negative });
  stream.send({ type: "complete", result: negative });
  stream.close();
  await until(() => calls.posts.length === 2);
  assert.equal(calls.captures, 1);
  assert.equal(answers(calls).length, 0, "the provisional reading is not shown as an answer");
  assert.equal(stored.results, undefined, "nor kept");
  assert.ok(calls.posts[1].body.image, "the screenshot is read next");
  const seen = { ...positive, source: { kind: "screenshot" } };
  streams[1].send({ type: "core", result: seen });
  streams[1].send({ type: "complete", result: seen });
  streams[1].close();
  await opening;
  assert.equal(calls.states.at(-1).shown.source.kind, "screenshot");
  assert.equal(stored.results.length, 1);
  assert.notEqual(stored.results[0].fingerprint, "article-print", "a visual answer is keyed by its pixels");
  controller.close();
});

// --- the early shared-result probe -------------------------------------------------------------

test("an early shared cache hit supplies a dated answer without sending page content", async () => {
  const collecting = deferred();
  const checkedAt = Date.now() - 1000;
  const { controller, calls } = popup({
    readPage: async (_tab, _signal, { onContext } = {}) => { onContext({ pageUrl: tab.url }); await collecting.promise; return articleRequest; },
    fetch: async (_url, options) => {
      const body = JSON.parse(options.body);
      if (body.cacheOnly) { calls.probes.push(body); return Response.json({ ...positive, cache: { shared: true, checkedAt } }); }
      calls.posts.push({ body });
      return Response.json(positive);
    },
  });
  const opening = controller.open();
  await until(() => calls.probes.length === 1);
  collecting.resolve();
  await opening;
  assert.equal(calls.posts.length, 0);
  assert.equal(calls.states.at(-1).cachedAt, checkedAt);
  controller.close();
});

test("no probe is sent for a page that is no longer current, and its result is not used", async () => {
  let current = true;
  const { controller, calls } = popup({
    isCurrentPage: async () => current,
    readPage: async (_tab, _signal, { onContext } = {}) => { current = false; onContext({ pageUrl: tab.url }); return articleRequest; },
  });
  await controller.open();
  assert.equal(calls.probes.length, 0);
  assert.equal(calls.posts.length, 0);
  assert.deepEqual(calls.states.at(-1), { kind: "refused", code: "page_changed" });
  controller.close();
});

test("a page with a saved answer waits for its fingerprint: a match sends nothing, a change probes then searches", async () => {
  for (const print of ["article-print", "changed-print"]) {
    const saved = remember([], tab.key, "article-print", negative, Date.now() - 1000);
    const stored = { lookup: { version: 2, index, savedAt: Date.now() }, results: saved };
    const calls = { states: [], posts: [], probes: [], order: [] };
    let read = false;
    const controller = createPopupController({
      site: { url: "https://service.example.org" },
      storage: { get: async () => stored, set: async (values) => Object.assign(stored, values) },
      readTab: async () => tab, isCurrentPage: async () => true,
      readPage: async (_tab, _signal, { onContext } = {}) => { onContext({ pageUrl: tab.url }); await pause(5); read = true; return { ...articleRequest, contentFingerprint: print }; },
      fetch: async (_url, options) => {
        if (options.method !== "POST") return Response.json(index);
        const body = JSON.parse(options.body);
        if (body.cacheOnly) { calls.probes.push(read); return Response.json({ cacheMiss: true }); }
        calls.posts.push(body);
        return Response.json(negative);
      },
      describeAnswer: (found) => ({ ...found }), present: (state) => calls.states.push(state),
    });
    await controller.open();
    if (print === "article-print") {
      assert.deepEqual([calls.probes.length, calls.posts.length], [0, 0]);
      assert.ok(calls.states.at(-1).cachedAt);
    } else {
      assert.deepEqual(calls.probes, [true], "probed once the content was known to have changed");
      assert.equal(calls.posts.length, 1);
    }
    controller.close();
  }
});

test("reused popup answers rebind cards against the loaded index without another lookup", async () => {
  for (const condition of ["tinnitus", "another condition"]) {
    const checkedAt = Date.now() - 60_000;
    const found = { ...positive, names: ["EX-1"], tracked: [{ slug: "archived", headline: "Old card", page: "/archived" }] };
    const current = { ...index, claims: { current: { names: ["EX-1"], indication: condition, headline: "New card", page: "/current" } } };
    const stored = { lookup: { version: 2, index: current, savedAt: Date.now() }, results: remember([], tab.key, "article-print", found, checkedAt) };
    const states = [];
    const controller = createPopupController({
      site: { url: "https://service.example.org" },
      storage: { get: async () => stored, set: async values => Object.assign(stored, values) },
      readTab: async () => tab, isCurrentPage: async () => true,
      readPage: async () => ({ ...articleRequest, contentFingerprint: "article-print" }),
      fetch: async (_url, options) => {
        assert.notEqual(options.method, "POST", "saved clinical work is reused");
        return Response.json(current);
      },
      describeAnswer: answer => ({ ...answer }), present: state => states.push(state),
    });
    await controller.open();
    const last = states.at(-1);
    assert.equal(last.kind, "answer");
    assert.deepEqual(last.shown.tracked, condition === "tinnitus" ? [{ slug: "current", headline: "New card", page: "/current" }] : []);
    assert.equal(last.cachedAt, checkedAt);
    controller.close();
  }
});

test("a shared non-treatment answer is final for a readable article, but a media page still gets its screenshot", async () => {
  const pages = [articleRequest, { ...articleRequest, readableArticle: false },
    { ...articleRequest, readableArticle: false, text: "Dental revolution" }];
  for (const page of pages) {
    const { controller, calls, stored } = popup({
      readPage: async () => page,
      fetch: async (_url, options) => {
        const body = JSON.parse(options.body);
        if (body.cacheOnly) return Response.json({ ...negative, gist: undefined, cache: { shared: true, checkedAt: Date.now() - 1000 } });
        calls.posts.push({ body });
        return Response.json(positive);
      },
    });
    await controller.open();
    if (page.readableArticle) {
      assert.equal(calls.captures, 0);
      assert.equal(calls.posts.length, 0);
      assert.equal(calls.states.at(-1).shown.about_a_treatment, false);
      assert.equal(stored.results.length, 1);
    } else {
      assert.equal(calls.captures, 1);
      assert.equal(calls.posts.length, 1);
      assert.ok(calls.posts[0].body.image);
      assert.equal(calls.states.at(-1).shown.treatment, "EX-1");
      assert.ok(!(stored.results ?? []).some((entry) => entry.found.about_a_treatment === false), "the shared text reading is not kept for a media page");
    }
    controller.close();
  }
});
