// Reading a social media post by its address and following the article it links to.
// Every post, article and platform answer here is made up; nothing is fetched.
// Scenario names are from openspec live-lookup.
import assert from "node:assert/strict";
import { test } from "node:test";

import { describeAnswer, refusalMessage, textWouldHelp } from "../src/lib/live-lookup.mjs";
import { readAddress } from "../src/lib/lookup-match.mjs";
import { handle } from "../worker/index.mjs";
import { readPost } from "../worker/post.mjs";

const CONTACT = "ops@example.org";
const ARTICLE = "https://news.example.org/health/ex1-regrows-teeth";
const ARTICLE_PAGE = `<html><head><meta property="og:title" content="Antibody regrows teeth"></head>
<body><p>${"EX-1 regrew teeth in people born without them. ".repeat(15)}</p></body></html>`;
const BLUESKY_POST = "https://bsky.app/profile/someone.example/post/3kabc123xyz";
const BLUESKY_API = "https://public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri=at%3A%2F%2Fsomeone.example%2Fapp.bsky.feed.post%2F3kabc123xyz&depth=0&parentHeight=0";
const BLUESKY_ANSWER = {
  thread: {
    post: {
      author: { handle: "someone.example", displayName: "Someone Real" },
      record: {
        text: "Huge if true: a drug that regrows teeth news.example.org/health/ex1…",
        facets: [{ features: [{ $type: "app.bsky.richtext.facet#link", uri: ARTICLE }] }],
      },
      embed: { external: { uri: ARTICLE, title: "Antibody regrows teeth", description: "A drug called EX-1 restored missing teeth." } },
    },
  },
};

/** A stand-in for the network: answers by address, remembers what was asked and how. */
function web(pages) {
  const asked = [];
  const fetch = async (address, options = {}) => {
    asked.push({ address, agent: options.headers?.["User-Agent"] });
    const page = pages[address];
    if (page === undefined) return new Response("", { status: 404 });
    if (typeof page === "number") return new Response("", { status: page });
    return typeof page === "string" ? new Response(page) : Response.json(page);
  };
  return { fetch, asked, addresses: () => asked.map((one) => one.address) };
}

const post = (address) => readAddress(address).post;

// --- which addresses are posts the service can read -----------------------------------

test("a post on a platform that offers posts to software is readable by its address", () => {
  const readable = [
    [BLUESKY_POST, "Bluesky", "bluesky"],
    ["https://news.ycombinator.com/item?id=50028027", "Hacker News", "hackernews"],
    ["https://mastodon.social/@someone/117593221666993044", "Mastodon", "mastodon"],
    ["https://scicomm.example/@lab/117593221666993044", "Mastodon", "mastodon"],
    ["https://scicomm.example/users/lab/statuses/117593221666993044", "Mastodon", "mastodon"],
  ];
  for (const [address, platform, how] of readable) {
    const read = readAddress(address);
    assert.deepEqual([read.kind, read.platform, read.readable, read.post.how], ["post", platform, true, how], address);
  }
});

test("a post on any other platform, and a platform's page that is not one post, is named and not readable", () => {
  const named = [
    ["https://x.com/someone/status/1234567890", "X"],
    ["https://www.reddit.com/r/science/comments/abc123/a_title/", "Reddit"],
    ["https://www.facebook.com/someone/posts/123456", "Facebook"],
    ["https://www.threads.net/@someone/post/abc", "Threads"],
    ["https://www.linkedin.com/posts/someone_activity-123", "LinkedIn"],
    ["https://bsky.app/profile/someone.example", "Bluesky"],
    ["https://news.ycombinator.com/newest", "Hacker News"],
  ];
  for (const [address, platform] of named) {
    const read = readAddress(address);
    assert.deepEqual([read.kind, read.platform, read.readable], ["post", platform, false], address);
  }
  // An article whose address merely starts with an @ name is still an article.
  assert.equal(readAddress("https://medium.com/@someone/a-story-123abc").kind, "article");
});

// --- reading one post ------------------------------------------------------------------

test("Scenario: Post on Bluesky", async () => {
  const { fetch, asked } = web({ [BLUESKY_API]: BLUESKY_ANSWER });

  const read = await readPost(post(BLUESKY_POST), { fetch, contact: CONTACT });

  assert.equal(
    read.text,
    "Huge if true: a drug that regrows teeth news.example.org/health/ex1…\nThe page it links to: Antibody regrows teeth. A drug called EX-1 restored missing teeth.",
  );
  assert.deepEqual(read.links, [ARTICLE]);
  // Who wrote the post is not read out.
  assert.doesNotMatch(JSON.stringify(read), /Someone Real|someone\.example/);
  assert.match(asked[0].agent, /^thenwhat\/\S+ \(mailto:ops@example\.org\)$/);
});

test("Scenario: Story on Hacker News", async () => {
  const { fetch } = web({
    "https://hacker-news.firebaseio.com/v0/item/50028027.json": { id: 50028027, type: "story", by: "someone", title: "Antibody regrows teeth in first human trial", url: ARTICLE },
    "https://hacker-news.firebaseio.com/v0/item/50028028.json": {
      id: 50028028,
      type: "comment",
      text: 'The paper is <a href="https://doi.org/10.1234/example.2026.0042" rel="nofollow">here</a>.<p>Registered as NCT01234567 &amp; ongoing.',
    },
    "https://hacker-news.firebaseio.com/v0/item/50028029.json": { id: 50028029, deleted: true },
  });

  const story = await readPost(post("https://news.ycombinator.com/item?id=50028027"), { fetch, contact: CONTACT });
  assert.deepEqual(story, { text: "Antibody regrows teeth in first human trial", links: [ARTICLE] });

  const comment = await readPost(post("https://news.ycombinator.com/item?id=50028028"), { fetch, contact: CONTACT });
  assert.equal(comment.text, "The paper is here.\nRegistered as NCT01234567 & ongoing.");
  assert.deepEqual(comment.links, ["https://doi.org/10.1234/example.2026.0042"]);

  for (const gone of ["50028029", "50028030"]) {
    assert.deepEqual(await readPost(post(`https://news.ycombinator.com/item?id=${gone}`), { fetch, contact: CONTACT }), { refused: "post_unreadable" });
  }
});

test("Scenario: Post on a Mastodon server", async () => {
  const status = {
    visibility: "public",
    account: { acct: "lab", display_name: "A Lab" },
    content: `<p>New trial of EX-1 <a href="https://scicomm.example/tags/teeth" class="mention hashtag" rel="tag">#teeth</a> <a href="${ARTICLE}"><span>news.example.org/health</span></a></p>`,
    card: { url: ARTICLE, title: "Antibody regrows teeth", description: "" },
  };
  const address = "https://scicomm.example/@lab/117593221666993044";
  const api = "https://scicomm.example/api/v1/statuses/117593221666993044";
  const { fetch, addresses } = web({ "https://scicomm.example/robots.txt": "User-agent: *\nDisallow: /media_proxy/", [api]: status });

  const read = await readPost(post(address), { fetch, contact: CONTACT });

  assert.equal(read.text, "New trial of EX-1 #teeth news.example.org/health\nThe page it links to: Antibody regrows teeth");
  // The link to a tag is not a link out; the card and the link in the text are one address.
  assert.deepEqual(read.links, [ARTICLE]);
  assert.deepEqual(addresses(), ["https://scicomm.example/robots.txt", api]);
  assert.doesNotMatch(JSON.stringify(read), /A Lab/);
});

test("a Mastodon server that refuses software, a private post, and a local address are not read", async () => {
  const api = "https://scicomm.example/api/v1/statuses/117593221666993044";
  const address = "https://scicomm.example/@lab/117593221666993044";
  const refusing = web({ "https://scicomm.example/robots.txt": "User-agent: *\nDisallow: /", [api]: { visibility: "public", content: "<p>x</p>" } });
  assert.deepEqual(await readPost(post(address), { fetch: refusing.fetch, contact: CONTACT }), { refused: "post_unreadable" });
  assert.ok(!refusing.addresses().includes(api), "the post was asked for");

  const followersOnly = web({ "https://scicomm.example/robots.txt": 404, [api]: { visibility: "private", content: "<p>For followers</p>" } });
  assert.deepEqual(await readPost(post(address), { fetch: followersOnly.fetch, contact: CONTACT }), { refused: "post_unreadable" });

  const local = web({});
  assert.deepEqual(await readPost(post("http://192.168.1.10/@admin/117593221666993044"), { fetch: local.fetch, contact: CONTACT }), { refused: "post_unreadable" });
  assert.deepEqual(local.asked, []);
});

// --- the service: a post and the article it links to ------------------------------------

const READING = { about_a_treatment: true, gist: "An antibody was reported to regrow missing teeth.", intervention: "EX-1", other_names: [], known_names: [], search_phrases: [], indication: "tooth agenesis" };
const STUDY = {
  protocolSection: {
    identificationModule: { nctId: "NCT00000001", briefTitle: "EX-1 in tooth agenesis" },
    conditionsModule: { conditions: ["Tooth Agenesis"] },
    designModule: { phases: ["PHASE2"] },
    statusModule: { overallStatus: "RECRUITING" },
  },
};
const INDEX = { articles: { "news.example.org/tracked-story": ["tooth-regrowth-ex1"] }, claims: { "tooth-regrowth-ex1": { headline: "Antibody regrows teeth", page: "/tooth-regrowth-ex1", names: [] } } };

function service(pages) {
  const net = web(pages);
  const shown = [];
  const tools = {
    fetch: net.fetch,
    model: { read: async (text) => (shown.push(text), READING), score: async (_intro, items) => items.map(() => ({ answer: "match", probabilities: { match: 0.95 } })) },
    registry: { search: async () => [STUDY], fetch: async () => null, named: async () => [] },
    papers: { trialNumbers: async () => [] },
  };
  const limiter = { limit: async () => ({ success: true }) };
  const env = {
    ASSETS: { fetch: async () => Response.json(INDEX) },
    LOOKUP_PER_READER: limiter,
    LOOKUP_IN_ALL: limiter,
    OPENAI_API_KEY: "test-credential",
    LLM_MODEL: "example-model",
    CONTACT_EMAIL: CONTACT,
  };
  const ask = (url) => handle(new Request("https://tracker.example.org/api/lookup", { method: "POST", body: JSON.stringify({ url }) }), env, tools);
  return { ask, shown, net };
}

test("Scenario: Post that links to an article", async () => {
  const { ask, shown, net } = service({ [BLUESKY_API]: BLUESKY_ANSWER, "https://news.example.org/robots.txt": 404, [ARTICLE]: ARTICLE_PAGE });

  const response = await ask(BLUESKY_POST);
  const found = await response.json();

  assert.equal(response.status, 200);
  assert.deepEqual(found.post, { platform: "Bluesky", article: ARTICLE, article_host: "news.example.org", article_read: true });
  assert.deepEqual(found.candidates.map((c) => c.id), ["NCT00000001"]);
  // The model is shown the post first, then the article.
  assert.match(shown[0], /^A post on Bluesky says:\nHuge if true[\s\S]*\n\nThe article it links to:\nHeadline: Antibody regrows teeth\n\nEX-1 regrew teeth/);
  assert.deepEqual(net.addresses(), [BLUESKY_API, "https://news.example.org/robots.txt", ARTICLE]);
  assert.equal(describeAnswer(found).source, "Read from a post on Bluesky and the article it links to at news.example.org.");
});

test("Scenario: Post whose article cannot be read", async () => {
  const { ask, shown } = service({ [BLUESKY_API]: BLUESKY_ANSWER, "https://news.example.org/robots.txt": "User-agent: *\nDisallow: /" });

  const found = await (await ask(BLUESKY_POST)).json();

  assert.deepEqual([found.post.article, found.post.article_read], [ARTICLE, false]);
  assert.match(shown[0], /^A post on Bluesky says:/);
  assert.doesNotMatch(shown[0], /The article it links to:/);
  assert.equal(
    describeAnswer(found).source,
    "Read from a post on Bluesky. The article it links to at news.example.org could not be read, so only the post was used.",
  );
});

test("a post that links to no article is looked up from its own text", async () => {
  const lone = { thread: { post: { record: { text: "EX-1 regrew my teeth, apparently. See https://bsky.app/profile/other.example/post/3kzzz", facets: [{ features: [{ uri: "https://bsky.app/profile/other.example/post/3kzzz" }] }] } } } };
  const { ask } = service({ [BLUESKY_API]: lone });

  const found = await (await ask(BLUESKY_POST)).json();

  // A link to another post is not followed.
  assert.deepEqual(found.post, { platform: "Bluesky", article: null, article_host: null, article_read: false });
  assert.equal(describeAnswer(found).source, "Read from a post on Bluesky. No article was found among its links, so only the post was used.");
});

test("Scenario: Post that links to a tracked article", async () => {
  const tracked = structuredClone(BLUESKY_ANSWER);
  tracked.thread.post.embed.external.uri = "https://www.news.example.org/tracked-story?utm_source=bsky";
  tracked.thread.post.record.facets = [];
  const { ask, shown, net } = service({ [BLUESKY_API]: tracked });

  const found = await (await ask(BLUESKY_POST)).json();

  assert.equal(found.article_tracked, true);
  assert.deepEqual(found.tracked, [{ slug: "tooth-regrowth-ex1", headline: "Antibody regrows teeth", page: "/tooth-regrowth-ex1" }]);
  // No model was asked and the article was not fetched: the reviewed page is the answer.
  assert.deepEqual([shown, net.addresses()], [[], [BLUESKY_API]]);
  const said = describeAnswer(found);
  assert.deepEqual([said.marked, said.likely, said.none], [null, [], null]);
  assert.match(said.lead, /links to an article we track/);
});

test("Scenario: Post on a platform that cannot be read", async () => {
  const { ask, net } = service({});

  const refused = await ask("https://x.com/someone/status/1234567890");
  assert.deepEqual([refused.status, await refused.json()], [422, { error: "post", platform: "X" }]);
  const gone = await ask(BLUESKY_POST);
  assert.deepEqual([gone.status, await gone.json()], [422, { error: "post_unreadable", platform: "Bluesky" }]);
  // Nothing was asked of X.
  assert.deepEqual(net.addresses(), [BLUESKY_API]);

  assert.equal(refusalMessage("post", { platform: "X" }), "This site cannot read posts on X. Paste its text below, or put the address of the article it links to in the box above.");
  assert.match(refusalMessage("post_unreadable", { platform: "Bluesky" }), /^That post on Bluesky could not be read\. It may be private or deleted\./);
  assert.ok(textWouldHelp("post") && textWouldHelp("post_unreadable"));
});
