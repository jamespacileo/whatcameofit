// What the extension sends for a registry search of the open page. `composeRequest` is
// pure: what was read from the page is passed in. Every page here is made up, shaped as
// the real ones were on 2026-11-12.
import assert from "node:assert/strict";
import { test } from "node:test";

import { readAddress } from "../../site/src/lib/lookup-match.mjs";
import { pageAsText, readPage } from "../../site/worker/page.mjs";
import { composeRequest } from "../src/open-page.js";

const shared = { readAddress, readPage, pageAsText };
const ARTICLE = "https://news.example.org/health/ex1-regrows-teeth";
const collected = (more) => ({ title: "", selection: "", head: "<head></head>", focusHtml: "", focusText: "", links: [], postTitle: null, contentHref: null, ...more });

test("a post on a platform the site cannot read is sent as its own words and links, named by platform", () => {
  const post = collected({
    title: 'A Lab on X: "A drug that regrows teeth: EX-1 restored missing teeth in a first trial in people" / X',
    focusText: "A Lab\n@alab\nA drug that regrows teeth: EX-1 restored missing teeth in a first trial in people #teeth\nAntibody regrows teeth\nFrom news.example.org\n9:30 AM · Mar 4, 2026\n·\n1,045\nViews",
    links: [
      { href: "https://x.com/alab", text: "A Lab" },
      { href: "https://x.com/alab", text: "@alab" },
      { href: "https://x.com/hashtag/teeth", text: "#teeth" },
      { href: "https://t.co/AbCdEf", text: "Antibody regrows teeth" },
      { href: "https://t.co/AbCdEf", text: "From news.example.org" },
      { href: "https://x.com/alab/status/1234567890", text: "9:30 AM · Mar 4, 2026" },
      { href: "https://x.com/alab/status/1234567890", text: "1,045\nViews" },
    ],
  });

  const request = composeRequest(post, "https://x.com/alab/status/1234567890", shared);

  assert.equal(request.platform, "X");
  // Who wrote the post, when, and how many saw it are left out; so are the page's own links.
  assert.equal(
    request.text,
    "A drug that regrows teeth: EX-1 restored missing teeth in a first trial in people #teeth\nAntibody regrows teeth\nFrom news.example.org",
  );
  assert.deepEqual(request.links, ["https://t.co/AbCdEf"]);
  assert.doesNotMatch(JSON.stringify(request), /A Lab|alab|x\.com/);
});

test("a post that states the address it links to gives that address first", () => {
  const post = collected({
    focusText: "r/science\nu/someone\nA longer discussion of the study follows here for anyone interested.",
    postTitle: "Antibody regrows teeth in first human trial",
    contentHref: ARTICLE,
    links: [
      { href: "https://www.reddit.com/user/someone/", text: "u/someone" },
      { href: "https://doi.org/10.1234/example.2026.0042", text: "the paper" },
    ],
  });

  const request = composeRequest(post, "https://www.reddit.com/r/science/comments/abc123/antibody_regrows_teeth/", shared);

  assert.equal(request.platform, "Reddit");
  assert.ok(request.text.startsWith("Antibody regrows teeth in first human trial\nr/science\n"));
  assert.doesNotMatch(request.text, /u\/someone/);
  assert.deepEqual(request.links, [ARTICLE, "https://doi.org/10.1234/example.2026.0042"]);
});

test("a post whose words could not be found falls back to the tab's title, without the writer's name", () => {
  const post = collected({ title: 'A Lab on X: "EX-1 restored missing teeth in a first trial in people, a study says" / X' });

  const request = composeRequest(post, "https://x.com/alab/status/1234567890", shared);

  assert.equal(request.text, "EX-1 restored missing teeth in a first trial in people, a study says");
});

test("an article is read as the site reads one: headline first, then the article, with its links out", () => {
  const body = "EX-1 regrew teeth in people born without them. ".repeat(12).trim();
  const page = collected({
    head: '<head><title>Antibody regrows teeth | The Example</title><meta property="og:title" content="Antibody regrows teeth"><meta property="article:published_time" content="2026-03-04"></head>',
    focusHtml: `<article><p>${body}</p><a href="https://doi.org/10.1234/example.2026.0042">paper</a><a href="/health">More health</a></article>`,
    links: [
      { href: "https://doi.org/10.1234/example.2026.0042", text: "paper" },
      { href: "https://news.example.org/health", text: "More health" },
    ],
  });

  const request = composeRequest(page, ARTICLE, shared);

  assert.equal(request.platform, undefined);
  assert.ok(request.text.startsWith("Headline: Antibody regrows teeth\nPublished: 2026-03-04\n\n"));
  assert.match(request.text, /EX-1 regrew teeth in people born without them\./);
  assert.deepEqual(request.links, ["https://doi.org/10.1234/example.2026.0042"]);
});

test("text the reader selected is all that is sent of the page's words", () => {
  const chosen = "EX-1 restored missing teeth in thirty adults, the researchers said.";
  const page = collected({ selection: chosen, focusText: "A Lab\nEverything else on the page", links: [{ href: ARTICLE, text: "story" }] });

  const request = composeRequest(page, "https://x.com/alab/status/1234567890", shared);

  assert.deepEqual([request.text, request.links, request.platform], [chosen, [], "X"]);
});

test("a page with too little to read, or a tab that is not a web page, gives nothing to send", () => {
  assert.equal(composeRequest(collected({ focusHtml: "<main><p>Loading</p></main>" }), ARTICLE, shared), null);
  assert.equal(composeRequest(collected({ focusText: "x".repeat(200) }), "chrome://extensions", shared), null);
});

test("no more than thirty links are sent, none of them long", () => {
  const many = Array.from({ length: 50 }, (_, n) => ({ href: `https://other.example.org/${n}`, text: "" }));
  const long = { href: `https://other.example.org/${"x".repeat(600)}`, text: "" };
  const page = collected({ focusText: "EX-1 restored missing teeth in a first trial in people.", links: [long, ...many] });

  const request = composeRequest(page, "https://x.com/alab/status/1234567890", shared);

  assert.equal(request.links.length, 30);
  assert.equal(request.links[0], "https://other.example.org/0");
});

test("Facebook and Reddit outgoing wrappers retain the linked article", () => {
  for (const [page, wrapper] of [
    ["https://www.facebook.com/example/posts/123", `https://l.facebook.com/l.php?u=${encodeURIComponent(ARTICLE)}`],
    ["https://www.reddit.com/r/science/comments/abc123/report/", `https://out.reddit.com/?url=${encodeURIComponent(ARTICLE)}`],
  ]) {
    const post = collected({
      focusText: "EX-1 is being studied as a treatment for missing teeth.",
      links: [{ href: wrapper, text: "Read the article" }],
    });
    assert.deepEqual(composeRequest(post, page, shared).links, [ARTICLE]);
  }
});

test("a wrapped article card's headline stays in the post text", () => {
  const headline = "EX-1 is being studied as a treatment for missing teeth.";
  const post = collected({
    focusText: `Research Account\n${headline}`,
    links: [
      { href: "https://www.facebook.com/example", text: "Research Account" },
      { href: `https://l.facebook.com/l.php?u=${encodeURIComponent(ARTICLE)}`, text: headline },
    ],
  });
  const request = composeRequest(post, "https://www.facebook.com/example/posts/123", shared);
  assert.equal(request.text, headline);
  assert.deepEqual(request.links, [ARTICLE]);
});

test("common social web apps preserve public post text and outgoing articles", () => {
  const pages = [
    ["https://bsky.app/profile/science.example/post/3abc123", "Bluesky"],
    ["https://news.ycombinator.com/item?id=12345678", "Hacker News"],
    ["https://science.social/@research/123456789", "Mastodon"],
    ["https://www.linkedin.com/posts/science_trial-123", "LinkedIn"],
    ["https://www.threads.com/@science/post/ABC123", "Threads"],
    ["https://www.instagram.com/p/ABC123/", "Instagram"],
  ];
  for (const [page, platform] of pages) {
    const post = collected({
      focusText: "Research Account\nEX-1 is being studied as a treatment for missing teeth.",
      links: [
        { href: new URL("/profile", page).href, text: "Research Account" },
        { href: ARTICLE, text: "Read the article" },
      ],
    });
    const request = composeRequest(post, page, shared);
    assert.equal(request.platform, platform);
    assert.doesNotMatch(request.text, /Research Account/);
    assert.deepEqual(request.links, [ARTICLE]);
    assert.equal(Object.hasOwn(request, "address"), false);
  }
});

test("an unreadable outgoing address does not prevent useful article links", () => {
  const post = collected({
    focusText: "EX-1 is being studied as a treatment for missing teeth.",
    links: [
      { href: "https://bsky.app/profile/%/post/abc123", text: "Malformed profile" },
      { href: ARTICLE, text: "Read the article" },
    ],
  });
  const request = composeRequest(post, "https://www.facebook.com/example/posts/123", shared);
  assert.ok(request.links.includes(ARTICLE));
});

test("short and link-only posts can search their outgoing article without invented text", () => {
  for (const words of ["Read this", ""]) {
    const post = collected({ title: "", focusText: words, links: [{ href: ARTICLE, text: "" }] });
    const request = composeRequest(post, "https://x.com/research/status/123456789", shared);
    assert.deepEqual(request, { text: words, links: [ARTICLE], platform: "X" });
  }
  const shortened = collected({ focusText: "Read this", links: [{ href: "https://t.co/AbCdEf", text: "" }] });
  assert.ok(composeRequest(shortened, "https://x.com/research/status/123456789", shared));
  const genericTitle = collected({ title: "Post by @someone.example — Bluesky", links: [{ href: ARTICLE, text: "" }] });
  assert.equal(composeRequest(genericTitle, "https://bsky.app/profile/someone.example/post/3abc123", shared).text, "");
});

test("short text without an article link keeps the too-little refusal", () => {
  for (const href of ["https://x.com/other/status/987654321", "https://www.linkedin.com/in/research"]) {
    const post = collected({ focusText: "Read this", links: [{ href, text: "" }] });
    assert.equal(composeRequest(post, "https://x.com/research/status/123456789", shared), null);
  }
  const page = collected({ focusHtml: "<main>Read this</main>", links: [{ href: ARTICLE, text: "" }] });
  assert.equal(composeRequest(page, "https://news.example.org/short", shared), null);
});

test("a short deliberate selection is preserved instead of a post title or image", () => {
 const chosen = "EX-1 for missing teeth";
 const request = composeRequest(collected({selection: chosen, postTitle: "Unrelated title"}), "https://x.com/lab/status/1234567890", shared);
 assert.equal(request.text, chosen);
 assert.deepEqual(request.links, []);
});
