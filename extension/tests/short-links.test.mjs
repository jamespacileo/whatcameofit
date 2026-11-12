// Learning where a shortened link leads, in the reader's browser. The shortener's page
// here is shaped as X's answered a browser on 2026-11-12; the addresses are made up.
import assert from "node:assert/strict";
import { test } from "node:test";

import { addressIn, resolveShortLinks } from "../src/short-links.js";

const ARTICLE = "https://news.example.org/health/ex1-regrows-teeth?a=1&b=2";
const pageFor = (address) =>
  `<head><noscript><META http-equiv="refresh" content="0;URL=${address}"></noscript><title>${address}</title></head><script>window.opener = null; location.replace(${JSON.stringify(address).replaceAll("/", "\\/")})</script>`;

test("the address a shortener's page names is read, whichever way the page says it", () => {
  assert.equal(addressIn(pageFor(ARTICLE), "t.co"), ARTICLE);
  assert.equal(addressIn(`<script>location.replace("https:\\/\\/news.example.org\\/a")</script>`, "t.co"), "https://news.example.org/a");
  assert.equal(addressIn("<title>https://news.example.org/b</title>", "t.co"), "https://news.example.org/b");
});

test("a page that names no address, a script address, or the shortener itself gives nothing", () => {
  assert.equal(addressIn("<title>Sign in</title>", "t.co"), null);
  assert.equal(addressIn(pageFor("javascript:alert(1)"), "t.co"), null);
  assert.equal(addressIn(pageFor("https://t.co/AbCdEf"), "t.co"), null);
});

function browser(pages) {
  const asked = [];
  const get = async (address, options) => {
    asked.push({ address, options });
    const page = pages[address];
    if (page === undefined) throw new TypeError("Failed to fetch");
    return typeof page === "number" ? new Response("", { status: page }) : new Response(page);
  };
  return { get, asked };
}

test("a link through X's shortener is replaced by the address it leads to, asked without cookies or referrer", async () => {
  const { get, asked } = browser({ "https://t.co/AbCdEf": pageFor(ARTICLE) });

  const links = await resolveShortLinks(["https://t.co/AbCdEf", "https://doi.org/10.1234/example"], get);

  assert.deepEqual(links, [ARTICLE, "https://doi.org/10.1234/example"]);
  // Only the shortened link was opened, and the article itself was not.
  assert.deepEqual(asked.map((one) => one.address), ["https://t.co/AbCdEf"]);
  assert.deepEqual(asked[0].options, { redirect: "manual", credentials: "omit", referrerPolicy: "no-referrer" });
});

test("a link that cannot be resolved is left as it was, and any other shortener is not opened", async () => {
  const { get, asked } = browser({ "https://t.co/gone": 404, "https://t.co/odd": "<title>Nothing here</title>" });

  const links = await resolveShortLinks(["https://t.co/gone", "https://t.co/odd", "https://t.co/offline", "https://bit.ly/3abc", "not an address"], get);

  assert.deepEqual(links, ["https://t.co/gone", "https://t.co/odd", "https://t.co/offline", "https://bit.ly/3abc", "not an address"]);
  assert.ok(!asked.some((one) => one.address.includes("bit.ly")));
});

test("no more than three shortened links are opened for one search, and two that lead to one article are one link", async () => {
  const pages = Object.fromEntries([1, 2, 3, 4].map((n) => [`https://t.co/${n}`, pageFor(ARTICLE)]));
  const { get, asked } = browser(pages);

  const links = await resolveShortLinks(["https://t.co/1", "https://t.co/2", "https://t.co/3", "https://t.co/4"], get);

  assert.equal(asked.length, 3);
  assert.deepEqual(links, [ARTICLE, "https://t.co/4"]);
});
