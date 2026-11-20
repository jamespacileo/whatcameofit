// Reach and sharing, checked against openspec/specs (reader-contact, site-publishing, site-measurement): the contact
// links (reader-contact), canonical addresses, structured data, the sitemap and the
// public-build check (site-publishing), and what a page may ask of other hosts
// (site-measurement). Builds tests/bundle (real pair pages from the lab's recorded slice)
// into temporary directories.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { before, test } from "node:test";
import { CORRECTION_SUBJECT, SUGGEST_SUBJECT, contactLink } from "../src/lib/contact.mjs";
import { mastodonShare, shareLinks } from "../src/lib/share.ts";
import { canonicalAddress } from "../src/lib/structured.ts";
import { readBundle } from "../src/lib/bundle.ts";
import { pairView } from "../src/lib/pair-view.ts";
import { oembedOf } from "../src/lib/embed-render.ts";
import { SITE } from "../site.config.mjs";
import { sitemapAddresses } from "./sitemap-read.mjs";

const BUNDLE = "tests/bundle";
// A pair, and a topic whose file lists a pair with a page. Both pages are made on request by the
// Worker into the frames the build leaves (tests/pair-on-request.build-test.mjs holds their
// canonical addresses, previews and trails as served); the sitemap lists both.
const PAIR = "ambroxol--dementia";
const TOPIC = "infections";
const ORIGIN = process.env.SITE_URL || "https://whatcameofit.com";
const SUGGEST_URL = "mailto:tips@example.org";
const CORRECTIONS_URL = "https://issues.example.org/new?template=correction";

const temporary = (name) => fs.mkdtempSync(path.join(os.tmpdir(), `thenwhat-reach-${name}-`));
const dist = temporary("site");
const contactDist = temporary("contact");
const page = (relative, root = dist) => fs.readFileSync(path.join(root, relative), "utf8");
const unescape = (text) => text.replaceAll("&amp;", "&");

function files(directory) {
  return fs.readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    const full = path.join(directory, entry.name);
    return entry.isDirectory() ? files(full) : [full];
  });
}
const htmlFiles = (directory) => files(directory).filter((file) => file.endsWith(".html"));

// No contact address and no public flag reach a build unless a test sets them.
function build(bundle, outDir, env = {}) {
  return spawnSync("npx", ["astro", "build", "--outDir", outDir], {
    env: {
      ...process.env,
      PAIRS_BUNDLE: bundle,
      ASTRO_TELEMETRY_DISABLED: "1",
      SUGGEST_URL: "",
      CORRECTIONS_URL: "",
      PUBLIC_BUILD: "",
      ...env,
    },
    encoding: "utf8",
  });
}

// The tags that make a browser fetch something as a page loads, and of those the ones
// that name another host. Canonical and alternate links are addresses, not fetches.
const LOADING_TAG = /<(script|img|link|source)\b[^>]*>/gi;
const ADDRESS = /(?:^|\s)(src|srcset|href)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+))/gi;

function foreignFetches(html) {
  return [...html.matchAll(LOADING_TAG)].flatMap(([tag, name]) => {
    if (name.toLowerCase() === "link" && /\brel=["']?(canonical|alternate)\b/i.test(tag)) return [];
    const addresses = [...tag.slice(name.length + 1).matchAll(ADDRESS)].flatMap((match) =>
      (match[2] ?? match[3] ?? match[4]).split(",").map((part) => part.trim().split(/\s+/)[0]),
    );
    const foreign = addresses.some(
      (address) => /^(https?:)?\/\//i.test(address) && new URL(address, ORIGIN).origin !== ORIGIN,
    );
    return foreign ? [tag] : [];
  });
}

// A stylesheet that pulls a file from another host.
const FOREIGN_CSS = /(?:url\(\s*["']?|@import\s+["'])(?:https?:)?\/\//i;
const COOKIE = /document\.cookie|cookieStore/;
const POSTING_FORM = /<form\b[^>]*\bmethod\s*=\s*["']?post\b/i;

before(() => {
  const result = build(BUNDLE, dist);
  assert.equal(result.status, 0, result.stdout + result.stderr);
  const configured = build(BUNDLE, contactDist, { SUGGEST_URL, CORRECTIONS_URL });
  assert.equal(configured.status, 0, configured.stdout + configured.stderr);
});

// reader-contact

test("contact link to a mail address carries the value in the body", () => {
  const article = "https://news.example.org/9?ref=feed&id=1";
  const link = contactLink(SUGGEST_URL, article, SUGGEST_SUBJECT);
  assert.equal(link.opens, "your mail");
  assert.ok(link.href.startsWith(`${SUGGEST_URL}?`));
  // Spaces are written %20: a mail program may show "+" as it is.
  assert.doesNotMatch(link.href, /\+/);
  const fields = new URL(link.href).searchParams;
  assert.equal(fields.get("subject"), SUGGEST_SUBJECT);
  assert.equal(fields.get("body"), article);

  const correction = contactLink(SUGGEST_URL, `${ORIGIN}/ambroxol--dementia`, CORRECTION_SUBJECT);
  assert.equal(new URL(correction.href).searchParams.get("subject"), CORRECTION_SUBJECT);
  // With nothing to carry, the message has its subject and no body.
  const bare = new URL(contactLink(SUGGEST_URL, "", SUGGEST_SUBJECT).href).searchParams;
  assert.equal(bare.get("subject"), SUGGEST_SUBJECT);
  assert.equal(bare.has("body"), false);
});

test("contact link to an issue form carries the value as about", () => {
  const link = contactLink(CORRECTIONS_URL, `${ORIGIN}/ambroxol--dementia`, CORRECTION_SUBJECT);
  assert.equal(link.opens, "an issue form");
  const url = new URL(link.href);
  assert.equal(url.origin + url.pathname, "https://issues.example.org/new");
  assert.equal(url.searchParams.get("template"), "correction");
  assert.equal(url.searchParams.get("about"), `${ORIGIN}/ambroxol--dementia`);
  // With nothing to carry, the link is the form's own address.
  assert.equal(contactLink(CORRECTIONS_URL).href, CORRECTIONS_URL);
});

test("contact link with no address configured is none", () => {
  for (const address of [null, undefined, ""]) {
    assert.equal(contactLink(address, "https://news.example.org/9"), null);
  }
  assert.throws(() => contactLink("ftp://example.org/inbox", "x"), /mailto: address or the http\(s\)/);
});

test("Scenario: No suggestion address", () => {
  // The default build has neither address, so no page offers to suggest or report.
  for (const file of htmlFiles(dist)) {
    const html = fs.readFileSync(file, "utf8");
    assert.doesNotMatch(html, /class="(suggest|report)"|data-suggest|Suggest (a|this) headline \(opens|Report an error \(opens/, file);
  }
});

test("Scenario: Pasted link is not tracked", () => {
  // With an address set, the lookup's answers read it from the page, to carry a pasted
  // article address into their own link. The pasted address is never fetched.
  const home = page("index.html", contactDist);
  assert.match(home, new RegExp(`id="results"[^>]*data-suggest="${SUGGEST_URL}"`));
  const scripts = files(path.join(contactDist, "_astro"))
    .filter((file) => file.endsWith(".js"))
    .map((file) => fs.readFileSync(file, "utf8"))
    .join("\n");
  assert.match(scripts + home, /Suggest this headline \(opens /);
});

test("Scenario: Reader chooses not to write", () => {
  // No page holds a form that sends anything to a server.
  assert.match('<form action="/x" method="POST">', POSTING_FORM);
  assert.match("<form method=post>", POSTING_FORM);
  assert.doesNotMatch('<form class="search" role="search" id="search">', POSTING_FORM);
  for (const root of [dist, contactDist]) {
    for (const file of htmlFiles(root)) {
      assert.doesNotMatch(fs.readFileSync(file, "utf8"), POSTING_FORM, file);
    }
  }
});

// site-publishing: Pages can be found and cited

test("every page states its own canonical address", () => {
  const expected = {
    "index.html": `${ORIGIN}/`,
    "topics/index.html": `${ORIGIN}/topics`,
  };
  for (const [file, address] of Object.entries(expected)) {
    assert.ok(page(file).includes(`<link rel="canonical" href="${address}">`), file);
  }
  // Embeds are not indexed. The private trial template receives its canonical ID
  // from the Worker; the public route is checked in trials.test.mjs.
  for (const file of htmlFiles(dist)) {
    const relative = path.relative(dist, file);
    // The frames the Worker fills state their address once filled.
    if (relative.startsWith(`embed${path.sep}`) || relative.startsWith(`pair-shell${path.sep}`) || relative.startsWith(`embed-shell${path.sep}`)) continue;
    if (relative === path.join("trial-reader", "index.html")) {
      const html = fs.readFileSync(file, "utf8");
      assert.match(html, /name="robots" content="noindex, follow"/);
      assert.match(html, /data-pagefind-ignore="all"/);
      assert.ok(html.includes(`${ORIGIN}/trials/__TRIAL_ID__`));
      continue;
    }
    const own = `/${relative.replace(/(\/?index)?\.html$/, "").split(path.sep).join("/")}`;
    const found = [...fs.readFileSync(file, "utf8").matchAll(/<link rel="canonical" href="([^"]+)">/g)];
    assert.equal(found.length, 1, relative);
    assert.equal(found[0][1], canonicalAddress(own), relative);
  }
});

test("no page carries fact-check, review or rating markup", () => {
  for (const file of htmlFiles(dist)) {
    assert.doesNotMatch(
      fs.readFileSync(file, "utf8"),
      /"@type"\s*:\s*"(ClaimReview|Review|Rating|AggregateRating)"|schema\.org\/(ClaimReview|Review|Rating|AggregateRating)/,
      file,
    );
  }
});

const structuredOf = (html) =>
  [...html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)].flatMap(
    ([, block]) => [JSON.parse(block)].flat(),
  );

test("the home page names the site and its publisher; the data page describes the dataset", () => {
  const home = structuredOf(page("index.html"));
  assert.equal(home.find((entry) => entry["@type"] === "WebSite").url, `${ORIGIN}/`);
  assert.equal(home.find((entry) => entry["@type"] === "Organization").logo.url, `${ORIGIN}/icon-512.png`);
  const dataset = structuredOf(page("data/index.html")).find((entry) => entry["@type"] === "Dataset");
  assert.equal(dataset.distribution.contentUrl, `${ORIGIN}/data/pairs.json`);
  assert.match(dataset.license, /creativecommons\.org/);
  assert.ok(structuredOf(page("clinical/index.html")).some((entry) => entry["@type"] === "BreadcrumbList"));
});

// site-publishing: Every page has a complete link preview

const meta = (html, name) =>
  html.match(new RegExp(`<meta (?:property|name)="${name}" content="([^"]*)"`))?.[1] ?? null;

test("Scenario: A pair's link pasted into a chat", () => {
  // The frame a pair's page is made in: its address goes where the frame marks it, and its
  // picture is the site's own card, since no pair has a picture of its own (task 4.6).
  const html = page("pair-shell/index.html");
  assert.equal(meta(html, "og:url"), `${ORIGIN}/__PAIR_ADDRESS__`);
  const image = new URL(meta(html, "og:image"));
  assert.equal(image.origin + image.pathname, `${ORIGIN}/brand-card.png`);
  assert.match(image.searchParams.get("v"), /^[a-f0-9]{12}$/);
  assert.equal(meta(html, "og:image:width"), "1200");
  assert.equal(meta(html, "og:image:height"), "630");
  assert.equal(meta(html, "og:image:type"), "image/png");
  assert.equal(meta(html, "twitter:image:alt"), meta(html, "og:image:alt"));
});

test("Scenario: Home page shared", () => {
  const html = page("index.html");
  assert.equal(meta(html, "og:type"), "website");
  const image = new URL(meta(html, "og:image"));
  assert.equal(image.origin + image.pathname, `${ORIGIN}/brand-card.png`);
  assert.match(image.searchParams.get("v"), /^[a-f0-9]{12}$/);
  assert.equal(meta(html, "article:published_time"), null);
});

test("every page states the whole link preview and announces the status changes feed", () => {
  for (const file of htmlFiles(dist)) {
    const relative = path.relative(dist, file);
    // An embed sits in another site's page and is never shared itself.
    if (relative.startsWith(`embed${path.sep}`) || relative.startsWith(`embed-shell${path.sep}`)) continue;
    const html = fs.readFileSync(file, "utf8");
    for (const name of ["og:title", "og:description", "og:url", "og:site_name", "og:image", "og:image:alt", "twitter:card", "twitter:image:alt", "theme-color"]) {
      assert.ok(meta(html, name), `${relative} lacks ${name}`);
    }
    assert.equal(meta(html, "og:locale"), "en_GB", relative);
    assert.ok(html.includes('href="/changes.xml"'), relative);
  }
});

test("Scenario: Crawler arrives", () => {
  const robots = page("robots.txt");
  assert.match(robots, /^User-agent: \*$/m);
  assert.match(robots, /^Allow: \/$/m);
  assert.ok(robots.includes(`Sitemap: ${ORIGIN}/sitemap.xml`));
});

// sharing

test("share links carry the sentence and address and nothing else", () => {
  const url = `${ORIGIN}/ambroxol--dementia`;
  const text = "A synthetic claim. First reported May 2019. Status: Phase 2 trial. Not medical advice.";
  const links = shareLinks(text, url, "A synthetic claim");
  assert.deepEqual(
    links.map((link) => link.network),
    ["bluesky", "threads", "x", "linkedin", "reddit", "whatsapp", "telegram", "email"],
  );
  for (const link of links) {
    assert.doesNotMatch(link.href, /utm_|[?&]ref=|fbclid/i, link.network);
    assert.ok(decodeURIComponent(link.href).includes(url), link.network);
  }
  const bluesky = new URL(links[0].href).searchParams.get("text");
  assert.equal(bluesky, `${text} ${url}`);
  // A long sentence is cut at a word to fit Bluesky's 300, the address kept whole.
  const long = new URL(shareLinks("word ".repeat(80).trim(), url, "t")[0].href).searchParams.get("text");
  assert.ok([...long].length <= 300);
  assert.ok(long.endsWith(` ${url}`));
  // A mail program may show "+" as it is, so the email link uses %20.
  assert.doesNotMatch(links.at(-1).href, /\+/);
});

test("Scenario: Reader posts to Mastodon for the first time", () => {
  const url = `${ORIGIN}/ambroxol--dementia`;
  for (const typed of ["mastodon.social", " https://Mastodon.Social/about ", "@me@mastodon.social"]) {
    const href = new URL(mastodonShare(typed, "Status: Phase 2 trial.", url));
    assert.equal(href.origin + href.pathname, "https://mastodon.social/share", typed);
    assert.equal(href.searchParams.get("text"), `Status: Phase 2 trial. ${url}`);
  }
  for (const typed of ["", "mastodon", "javascript:alert(1)", "a b.social"]) {
    assert.equal(mastodonShare(typed, "x", url), null, typed);
  }
});

// sharing: An embed can be found from the pair's address

test("Scenario: A pair's address pasted into a site that reads oEmbed", () => {
  // The frame announces the pair's description at the pair's own address once filled; the
  // Worker writes the description (tests/pair-on-request.build-test.mjs serves it).
  const html = page("pair-shell/index.html");
  assert.ok(html.includes(`<link rel="alternate" type="application/json+oembed" href="${ORIGIN}/oembed/__PAIR_ADDRESS__.json"`));
  const card = meta(html, "og:image");
  const oembed = oembedOf(pairView(readBundle(BUNDLE).pages.PairPage[PAIR]), SITE.name, ORIGIN, card);
  assert.equal(oembed.type, "rich");
  assert.equal(oembed.version, "1.0");
  assert.ok(oembed.html.includes(`${ORIGIN}/embed/${PAIR}`));
  assert.equal(oembed.width, 440);
  assert.equal(new URL(oembed.thumbnail_url).pathname, "/brand-card.png");
});

test("the sitemap lists every public page and no embed", () => {
  const listed = sitemapAddresses(dist);
  for (const address of ["/", `/${PAIR}`, "/topics", `/topic/${TOPIC}`, "/data", "/about"]) {
    assert.ok(listed.includes(canonicalAddress(address)), `${address} is not listed`);
  }
  assert.ok(listed.every((address) => address.startsWith(`${ORIGIN}/`)));
  assert.ok(!listed.some((address) => /\/embed\/|\/404$|\/pair-shell$|\/embed-shell$/.test(address)));
  // Each built page but these is listed. A pair made on request is listed and not built.
  const built = htmlFiles(dist).map((file) => {
    const relative = path.relative(dist, file).split(path.sep).join("/");
    return canonicalAddress(`/${relative.replace(/(\/?index)?\.html$/, "")}`);
  });
  // A topic no pair is filed under has its page and is not listed.
  const emptyTopic = (address) =>
    /\/topic\/[^/]+$/.test(address) && !page(`${new URL(address).pathname.slice(1)}/index.html`).includes("data-pair=");
  const unlisted = built.filter(
    // Error pages, embeds, the private trial template and the frame for pages made on request.
    (address) => !listed.includes(address) && !/\/404$|\/embed\/|\/trial-reader$|\/pair-shell$|\/embed-shell$/.test(address) && !emptyTopic(address),
  );
  assert.deepEqual(unlisted, []);
});

test("Scenario: Public address not configured", () => {
  const result = build(BUNDLE, temporary("public"), { PUBLIC_BUILD: "1", SITE_URL: "http://localhost:4321" });
  assert.notEqual(result.status, 0);
  assert.match(result.stdout + result.stderr, /public address must be set as SITE\.url in site\/site\.config\.mjs/);
});

// site-measurement

test("Scenario: Reader visits a page", () => {
  // The checks would catch another party's script, image or stylesheet, and a cookie.
  assert.deepEqual(foreignFetches('<script async src="https://counter.example.com/count.js"></script>'), [
    '<script async src="https://counter.example.com/count.js">',
  ]);
  assert.equal(foreignFetches('<img alt="" src="//pixel.example.net/p.gif">').length, 1);
  assert.equal(foreignFetches('<link href="https://fonts.example.com/a.css" rel="stylesheet">').length, 1);
  assert.equal(foreignFetches('<img srcset="/a.png 1x, https://cdn.example.com/a@2x.png 2x">').length, 1);
  assert.deepEqual(
    foreignFetches(`<script src="/_astro/a.js"></script><link rel="canonical" href="https://other.example/x"><img src="${ORIGIN}/og/a.png">`),
    [],
  );
  assert.match("@import url(https://fonts.example.com/a.css);", FOREIGN_CSS);
  assert.doesNotMatch("src: url(/_astro/face.woff2)", FOREIGN_CSS);
  assert.match("document.cookie = 'id=1'", COOKIE);

  for (const file of htmlFiles(dist)) {
    const html = fs.readFileSync(file, "utf8");
    assert.deepEqual(foreignFetches(html), [], file);
    assert.doesNotMatch(html, COOKIE, file);
    for (const [, css] of html.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/g)) {
      assert.doesNotMatch(css, FOREIGN_CSS, file);
    }
  }
  for (const file of files(path.join(dist, "_astro"))) {
    if (!/\.(js|css)$/.test(file)) continue;
    const text = fs.readFileSync(file, "utf8");
    assert.doesNotMatch(text, COOKIE, file);
    if (file.endsWith(".css")) assert.doesNotMatch(text, FOREIGN_CSS, file);
  }
});
