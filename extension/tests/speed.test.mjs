// Faster popup lookups that stay correct: a staged answer shown as soon as its clinical
// part is complete, completed answers reused for unchanged content, an ordinary article
// read from its words without an automatic screenshot, and an early shared-result probe
// that respects selection, private windows and navigation. All pages are made up.
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

import { readAddress } from "../../site/src/lib/lookup-match.mjs";
import { pageAsText, readPage } from "../../site/worker/page.mjs";
import { createPopupController, lookupEvents } from "../src/controller.js";
import { composeRequest, fingerprintInput, readableArticle } from "../src/open-page.js";
import { RESULT_TTL, completed, remember, reusable } from "../src/results.js";

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

const SCIENCE = "https://www.sciencealert.com/scientists-identified-a-biological-signature-of-tinnitus-and-its-in-your-blood";
const PARAGRAPHS = [
  "Researchers examining blood samples from people with persistent ringing in the ears report a set of molecular markers that appear far more often in those with the condition than in people without it.",
  "The team compared hundreds of volunteers, some with chronic tinnitus and some without, and measured a panel of proteins and small molecules associated with inflammation and nerve signalling.",
  "Several of these markers differed consistently between the groups, and the differences were larger in volunteers who described their symptoms as more severe or longer lasting.",
  "The authors caution that the work identifies a possible biological signature rather than a cause, and that a blood test for clinical use would need validation in larger and more varied groups.",
  "They also note that hearing loss, stress and sleep problems often accompany the condition and may influence the same markers, which makes untangling cause and effect difficult.",
  "Independent researchers not involved in the study said the findings were interesting because the condition currently has no objective measure, and diagnosis relies on what patients report.",
  "The study was published in a peer-reviewed journal, and the researchers say their next step is to follow volunteers over time to see whether the markers change as symptoms change.",
].map((words) => `<p>${words}</p>`).join("\n");
const STRUCTURED = JSON.stringify({ "@context": "https://schema.org", "@graph": [
  { "@type": "WebPage", "@id": `${SCIENCE}#webpage` },
  { "@type": "ImageObject", "@id": `${SCIENCE}#primaryimage`, url: "https://www.sciencealert.com/images/ear.jpg" },
  { "@type": "NewsArticle", headline: "Scientists identified a biological signature of tinnitus, and it's in your blood", datePublished: "2026-11-10" },
] });
const sciencePage = (more = {}) => ({
  address: SCIENCE,
  title: "Scientists identified a biological signature of tinnitus, and it's in your blood : ScienceAlert",
  selection: "",
  head: `<head><title>Tinnitus signature</title><meta property="og:type" content="article"><meta property="og:title" content="Scientists identified a biological signature of tinnitus"><script type="application/ld+json">${STRUCTURED}</script></head>`,
  focusHtml: `<article><h1>Scientists identified a biological signature of tinnitus, and it's in your blood</h1><figure><img src="https://www.sciencealert.com/images/ear.jpg" alt="An ear"><figcaption>(Example Photo Agency)</figcaption></figure>${PARAGRAPHS}<p>Read the paper: <a href="https://doi.org/10.1000/example.tinnitus">the study</a>.</p></article>`,
  focusText: "",
  links: [{ href: "https://doi.org/10.1000/example.tinnitus", text: "the study" }],
  postTitle: null,
  contentHref: null,
  structured: [STRUCTURED],
  ...more,
});
const heroPhoto = [{ left: 0, top: 120, width: 800, height: 450, kind: "img", identity: "https://www.sciencealert.com/images/ear.jpg", time: null }];
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
  for (const version of [1, 2, 3, 4, 5, 6, 7, 8, 9]) {
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
  const controller = createPopupController({
    site: { url: "https://service.example.org" },
    storage: { get: async () => stored, set: async (values) => { calls.writes.push(values); Object.assign(stored, values); } },
    readTab: async () => tab,
    isCurrentPage: async () => current,
    readPage: async () => articleRequest,
    capturePage: async () => { calls.captures += 1; return { image: { dataUrl: "data:image/jpeg;base64,AAAA", width: 1, height: 1 }, pageUrl: tab.url }; },
    fetch: async (_url, options) => {
      const body = JSON.parse(options.body);
      if (body.cacheOnly) { calls.probes.push(body); return Response.json({ cacheMiss: true }); }
      calls.posts.push({ body, signal: options.signal });
      if (calls.posts.length > streams.length) streams.push(staged());
      return streams[calls.posts.length - 1].response;
    },
    describeAnswer: (found) => ({ ...found }),
    present: (state) => calls.states.push(state),
    ...overrides,
  });
  return { controller, calls, stored, stream: streams[0], streams, navigate: () => { current = false; } };
}
const answers = (calls) => calls.states.filter((state) => state.kind === "answer");

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
  for (const ending of ["close", "error", "malformed"]) {
    const { controller, calls, stored, stream } = popup();
    const opening = controller.open();
    await until(() => calls.posts.length === 1);
    stream.send({ type: "core", result: positive });
    if (ending === "error") stream.send({ type: "error", error: "failed" });
    if (ending === "malformed") stream.bytes(encoder.encode("{broken\n"));
    stream.close();
    await opening;
    const last = calls.states.at(-1);
    assert.equal(last.kind, "answer", ending);
    assert.equal(last.research, "incomplete", ending);
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
    stream.send({ type: "complete", result: positive });
    stream.close();
    await opening;
    if (leave === "close") assert.equal(calls.states.length, count, "nothing renders after closing");
    else assert.deepEqual(calls.states.at(-1), { kind: "refused", code: "page_changed" });
    assert.equal(stored.results, undefined, leave);
    assert.equal(calls.posts.length, 1, leave);
    assert.equal(calls.captures, 0, leave);
    controller.close();
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

test("the shared probe starts while the page is still being collected, after its context is settled", async () => {
  const collecting = deferred();
  const { controller, calls } = popup({
    readPage: async (_tab, _signal, { onContext } = {}) => { onContext({ pageUrl: tab.url }); await collecting.promise; return articleRequest; },
    fetch: async (_url, options) => {
      const body = JSON.parse(options.body);
      if (body.cacheOnly) { calls.probes.push(body); return Response.json({ ...positive, cache: { shared: true, checkedAt: Date.now() - 1000 } }); }
      calls.posts.push({ body });
      return Response.json(positive);
    },
  });
  const opening = controller.open();
  await until(() => calls.probes.length === 1);
  assert.deepEqual(calls.probes[0], { cacheOnly: true, pageUrl: tab.url });
  collecting.resolve();
  await opening;
  assert.equal(calls.posts.length, 0);
  assert.ok(calls.states.at(-1).cachedAt);
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

test("a shared non-treatment answer is final for a readable article, but a media page still gets its screenshot", async () => {
  for (const readable of [true, false]) {
    const { controller, calls, stored } = popup({
      readPage: async () => ({ ...articleRequest, readableArticle: readable }),
      fetch: async (_url, options) => {
        const body = JSON.parse(options.body);
        if (body.cacheOnly) return Response.json({ ...negative, gist: undefined, cache: { shared: true, checkedAt: Date.now() - 1000 } });
        calls.posts.push({ body });
        return Response.json(positive);
      },
    });
    await controller.open();
    if (readable) {
      assert.equal(calls.captures, 0);
      assert.equal(calls.states.at(-1).shown.about_a_treatment, false);
      assert.equal(stored.results.length, 1);
    } else {
      assert.equal(calls.captures, 1);
      assert.ok(calls.posts[0].body.image);
      assert.ok(!(stored.results ?? []).some((entry) => entry.found.about_a_treatment === false), "the shared text reading is not kept for a media page");
    }
    controller.close();
  }
});

test("selected words are never probed, never given a page address and never kept", async () => {
  const { controller, calls, stored } = popup({
    readPage: async () => ({ text: "The selected words report EX-1 for tinnitus in people.", links: [], selectionOnly: true, visualCandidate: true }),
    fetch: async (_url, options) => {
      const body = JSON.parse(options.body);
      if (body.cacheOnly) calls.probes.push(body);
      else calls.posts.push({ body });
      return Response.json(negative);
    },
  });
  await controller.open();
  assert.equal(calls.probes.length, 0);
  assert.equal(calls.posts.length, 1);
  assert.equal(calls.posts[0].body.pageUrl, undefined);
  assert.equal(calls.posts[0].body.selectionOnly, undefined);
  assert.equal(calls.captures, 0);
  assert.equal(stored.results, undefined);
  controller.close();
});

// --- the real popup glue ------------------------------------------------------------------------

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
async function runPopup({ selection = "", collected = sciencePage(), address = SCIENCE }) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "thenwhat-speed-"));
  const globals = ["browser", "document", "window", "fetch", "__speedCapture"];
  const saved = new Map(globals.map((name) => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  const shortResponse = deferred();
  const shortStarted = deferred();
  const done = deferred();
  const log = { posts: [], probes: [], shortResolvedBeforeProbe: null, captures: 0, states: [] };
  let events = {};
  try {
    const files = {
      "popup.js": "extension/src/popup.js", "controller.js": "extension/src/controller.js", "results.js": "extension/src/results.js",
      "visual.js": "extension/src/visual.js", "source-url.js": "site/src/lib/source-url.mjs", "lookup.js": "extension/src/lookup.js",
      "kept.js": "extension/src/kept.js", "watch.js": "extension/src/watch.js", "open-page.js": "extension/src/open-page.js",
      "short-links.js": "extension/src/short-links.js", "article-key.js": "site/src/lib/article-key.mjs",
      "lookup-match.js": "site/src/lib/lookup-match.mjs", "page.js": "site/worker/page.mjs",
      "live-lookup.js": "site/src/lib/live-lookup.mjs", "notices.ts": "site/src/lib/notices.ts",
    };
    for (const [name, source] of Object.entries(files)) {
      const content = (await fs.readFile(path.join(root, source), "utf8")).replaceAll("./article-key.mjs", "./article-key.js")
        .replace("../../site/src/lib/source-url.mjs", "./source-url.js");
      await fs.writeFile(path.join(directory, name), content);
    }
    await fs.writeFile(path.join(directory, "package.json"), '{"type":"module"}');
    await fs.writeFile(path.join(directory, "config.js"), 'export const SITE = {name:"Test",url:"https://whatcameofit.example"};');
    await fs.writeFile(path.join(directory, "view.js"), "export function render(root,state){globalThis.__speedCapture(state);}");
    const current = { id: 7, windowId: 1, url: address };
    const stored = { sharing: { version: 1, enabled: true } };
    let shortDone = false;
    globalThis.document = { querySelector: () => ({ textContent: "" }) };
    globalThis.window = { addEventListener: (name, callback) => { events[name] = callback; }, close() {} };
    globalThis.browser = {
      storage: { local: { get: async () => stored, set: async (values) => Object.assign(stored, values) } },
      tabs: { query: async () => [current], captureVisibleTab: async () => { log.captures += 1; throw new Error("no automatic photo"); } },
      scripting: {
        executeScript: async ({ func }) => (func.name === "inspectVisible"
          ? [{ result: { address, media: heroPhoto, sensitive: false, selectionOnly: selection.length >= 20, width: 800, height: 600, crop: heroPhoto[0] } }]
          : [{ result: { ...collected, selection, links: [...collected.links, { href: "https://t.co/AbCdEf", text: "more" }] } }]),
      },
    };
    globalThis.fetch = async (url, options = {}) => {
      if (String(url).endsWith("/lookup.json")) return Response.json(index);
      if (url === "https://t.co/AbCdEf") { shortStarted.resolve(); const response = await shortResponse.promise; shortDone = true; return response.clone(); }
      const body = JSON.parse(options.body);
      if (body.cacheOnly) { log.probes.push(body); log.shortResolvedBeforeProbe = shortDone; return Response.json({ cacheMiss: true }); }
      log.posts.push(body);
      return Response.json(negative);
    };
    globalThis.__speedCapture = (state) => { log.states.push(state); if (["answer", "refused"].includes(state.kind)) done.resolve(); };
    await import(pathToFileURL(path.join(directory, "popup.js")));
    // Selected words carry no links, so there is nothing to resolve.
    if (!selection) await shortStarted.promise;
    await pause(10);
    shortResponse.resolve(new Response("<title>https://example.org/other</title>"));
    await done.promise;
    await pause(10);
    return { ...log, stored };
  } finally {
    events.pagehide?.();
    for (const [name, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor);
      else delete globalThis[name];
    }
    await fs.rm(directory, { recursive: true, force: true });
  }
}

test("the real popup probes while links resolve, reads the article from its words, and keeps the dated answer", { timeout: 5000 }, async () => {
  const result = await runPopup({});
  assert.equal(result.probes.length, 1);
  assert.equal(result.shortResolvedBeforeProbe, false, "the probe overlapped link resolution");
  assert.equal(result.posts.length, 1);
  for (const internal of ["readableArticle", "visualCandidate", "contentFingerprint", "selectionOnly"]) assert.equal(result.posts[0][internal], undefined, internal);
  assert.equal(result.posts[0].stream, true);
  assert.equal(result.captures, 0, "no automatic photo of an ordinary article");
  assert.equal(result.states.at(-1).kind, "answer");
  assert.equal(result.states.at(-1).shown.subject, null);
  assert.equal(result.stored.results.length, 1);
  assert.equal(result.stored.results[0].found.about_a_treatment, false);
  assert.doesNotMatch(JSON.stringify(result.stored), /biological signature|ringing in the ears|data:image/);
});

test("the real popup with selected words sends no probe or page address", { timeout: 5000 }, async () => {
  const result = await runPopup({ selection: "These selected words describe a blood marker for ringing ears." });
  assert.equal(result.probes.length, 0);
  assert.equal(result.posts.length, 1);
  assert.equal(result.posts[0].pageUrl, undefined);
  assert.equal(result.stored.results, undefined);
});
