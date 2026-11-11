// Reading an address a reader pastes: the shapes links take when they are shared.
// Pure functions, synthetic addresses. No build and no network.
import assert from "node:assert/strict";
import { test } from "node:test";
import { articleKey } from "../src/lib/article-key.mjs";
import { closestClaims, readAddress } from "../src/lib/lookup-match.mjs";

const article = (input) => {
  const read = readAddress(input);
  assert.equal(read.kind, "article", `${input} was read as ${read.kind}`);
  return read.key;
};

test("each outlet's shared forms of one article give one key", () => {
  const groups = {
    "bbc.com/news/articles/c1234abcd": [
      "https://www.bbc.com/news/articles/c1234abcd",
      "https://www.bbc.co.uk/news/articles/c1234abcd",
      "https://bbc.co.uk/news/articles/c1234abcd.amp",
      "https://www.bbc.com/news/articles/c1234abcd?at_medium=social&at_campaign=64",
    ],
    "theguardian.com/science/2026/nov/09/medical-breakthrough": [
      "https://www.theguardian.com/science/2026/nov/09/medical-breakthrough",
      "https://amp.theguardian.com/science/2026/nov/09/medical-breakthrough",
      "https://www.theguardian.com/science/2026/nov/09/medical-breakthrough?CMP=share_btn_url",
    ],
    "cnn.com/2026/10/22/health/cancer-vaccine": [
      "https://www.cnn.com/2026/10/22/health/cancer-vaccine",
      "https://edition.cnn.com/2026/10/22/health/cancer-vaccine/index.html",
      "https://amp.cnn.com/cnn/2026/10/22/health/cancer-vaccine",
    ],
    "dailymail.co.uk/article-16271133": [
      "https://www.dailymail.co.uk/health/article-16271133/Heart-pill-hailed-Holy-Grail.html",
      "https://www.dailymail.co.uk/health/article-16271133/Heart-pill-hailed-Holy-Grail-high-blood-pressure-patients-effectively-cured-deadly-co",
      "https://www.dailymail.co.uk/health/article-16271133/amp/Heart-pill-hailed-Holy-Grail.html",
      "https://www.dailymail.co.uk/health/article-16271133/Heart-pill-hailed-Holy-Grail.html?ito=social-twitter_mailonline",
    ],
    "foxnews.com/health/knee-treatment-without-surgery": [
      "https://www.foxnews.com/health/knee-treatment-without-surgery",
      "https://www.foxnews.com/health/knee-treatment-without-surgery.amp",
    ],
    "independent.co.uk/news/science/gene-therapy-b3080366.html": [
      "https://www.independent.co.uk/news/science/gene-therapy-b3080366.html",
      "https://www.independent.co.uk/news/science/gene-therapy-b3080366.html?amp",
      "https://www.independent.co.uk/news/science/gene-therapy-b3080366.html?utm_source=reddit.com",
    ],
    "nytimes.com/2026/10/01/health/drug.html": [
      "https://www.nytimes.com/2026/10/01/health/drug.html",
      "https://www.nytimes.com/2026/10/01/health/drug.html?smid=tw-share&unlocked_article_code=1.abc",
      "https://mobile.nytimes.com/2026/10/01/health/drug.html",
    ],
    "sciencedaily.com/releases/2026/10/261020085013.htm": [
      "https://www.sciencedaily.com/releases/2026/10/261020085013.htm",
      "sciencedaily.com/releases/2026/10/261020085013.htm",
      "  https://www.sciencedaily.com/releases/2026/10/261020085013.htm  ",
    ],
  };
  for (const [key, addresses] of Object.entries(groups)) {
    for (const address of addresses) assert.equal(article(address), key, address);
  }
});

test("a link wrapped by a social site or a cache is read as the article inside it", () => {
  const inner = "https://www.example.org/news/tooth-study";
  const key = "example.org/news/tooth-study";
  for (const address of [
    `https://l.facebook.com/l.php?u=${encodeURIComponent(inner + "?fbclid=xyz")}&h=AT0abc`,
    `https://www.google.com/url?sa=t&url=${encodeURIComponent(inner)}&usg=AOv`,
    `https://www.google.com/url?q=${encodeURIComponent(inner)}`,
    `https://out.reddit.com/t3_abc?url=${encodeURIComponent(inner)}&token=x`,
    `https://www.linkedin.com/redir/redirect?url=${encodeURIComponent(inner)}&urlhash=x`,
    `https://l.instagram.com/?u=${encodeURIComponent(inner)}&e=x`,
    "https://www-example-org.cdn.ampproject.org/c/s/www.example.org/news/tooth-study",
    "https://www-example-org.cdn.ampproject.org/v/s/www.example.org/news/tooth-study?amp_js_v=0.1",
    "https://www.google.com/amp/s/www.example.org/news/tooth-study",
    "https://web.archive.org/web/20261101120000/https://www.example.org/news/tooth-study",
    "https://archive.ph/2026.11.01-120000/https://www.example.org/news/tooth-study",
    "https://12ft.io/https://www.example.org/news/tooth-study",
  ]) {
    assert.equal(article(address), key, address);
  }
});

test("a shortened link is named as one, because only opening it shows the article", () => {
  for (const address of [
    "https://t.co/AbCdEf123",
    "https://bit.ly/3xYzAbc",
    "https://lnkd.in/eAbc123",
    "bbc.in/4abc",
    "https://apple.news/AbCdEf",
    "https://news.google.com/rss/articles/CBMiABC?oc=5",
    "https://share.google/abc123",
  ]) {
    assert.equal(readAddress(address).kind, "short", address);
  }
});

test("a social media post is named as a post, not an article", () => {
  for (const address of [
    "https://x.com/someone/status/1234567890",
    "https://twitter.com/someone/status/1234567890",
    "https://www.facebook.com/someone/posts/123456",
    "https://www.reddit.com/r/Futurology/comments/abc123/scientists_regrow_teeth/",
    "https://www.linkedin.com/posts/someone_activity-123",
    "https://www.instagram.com/p/AbC123/",
    "https://www.tiktok.com/@someone/video/123",
    "https://bsky.app/profile/someone.bsky.social/post/abc",
  ]) {
    assert.equal(readAddress(address).kind, "post", address);
  }
});

test("words that are not an address are left for the ordinary search", () => {
  for (const input of ["tooth regrowth", "CTX310", "", "what happened to the baldness pill?"]) {
    assert.equal(readAddress(input).kind, "none", input);
  }
});

// --- closest matches ---------------------------------------------------------

const index = {
  claims: {
    "tooth-antibody": {
      headline: "Antibody against USAG-1 regrows teeth in mice",
      terms: "anti-usag-1 antibody trg035 congenital tooth agenesis new drug to regenerate lost teeth kyoto university",
    },
    "baldness-pill": {
      headline: "A daily oral minoxidil pill, VDPHL01, was reported to increase hair growth",
      terms: "vdphl01 male pattern baldness scientists tested an experimental baldness pill on 536 men vice",
    },
    "melanoma-vaccine": {
      headline: "A personalised mRNA vaccine was reported to cut the risk of melanoma returning",
      terms: "intismeran autogene mrna-4157 melanoma experimental mrna vaccine cuts risk melanoma returns cnn",
    },
  },
};
const slugs = (address) => closestClaims(index, address).map((match) => match.slug);

test("another outlet's report of a tracked story is offered as a close match", () => {
  assert.deepEqual(
    slugs("https://www.dailymail.co.uk/health/article-99/Baldness-pill-regrows-hair-536-men-trial.html"),
    ["baldness-pill"],
  );
  assert.deepEqual(
    slugs("https://nypost.com/2026/10/23/health/mrna-vaccine-slashes-melanoma-return-risk/"),
    ["melanoma-vaccine"],
  );
});

test("a drug's own name in the address is enough on its own", () => {
  assert.deepEqual(slugs("https://example.org/pharma/vdphl01-results"), ["baldness-pill"]);
});

test("an unrelated article has no close match", () => {
  assert.deepEqual(slugs("https://www.example.org/sport/football/cup-final-report-2026"), []);
  // Words every health story shares do not count.
  assert.deepEqual(slugs("https://www.example.org/health/news/new-study-scientists-breakthrough"), []);
});

test("the comparison form itself is unchanged for plain addresses", () => {
  assert.equal(articleKey("https://www.example.org/a/b/"), "example.org/a/b");
});
