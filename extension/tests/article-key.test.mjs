// The comparison form of an article address, shared by the site and the extension.
import assert from "node:assert/strict";
import { test } from "node:test";
import { articleKey } from "../../site/src/lib/article-key.mjs";

test("the same article reached in different ways has one key", () => {
  const key = "example.org/news/2026/tooth-study";
  for (const address of [
    "https://example.org/news/2026/tooth-study",
    "https://www.example.org/news/2026/tooth-study/",
    "http://m.example.org/news/2026/tooth-study",
    "https://WWW.Example.org/news/2026/tooth-study#comments",
    "https://www.example.org/news/2026/tooth-study?utm_source=feed&utm_medium=rss&fbclid=abc",
    "https://www.example.org/news/2026/tooth-study/amp",
    "https://www.example.org/news/2026/tooth-study.amp",
  ]) {
    assert.equal(articleKey(address), key, address);
  }
});

test("parameters that name the article are kept, in a fixed order", () => {
  assert.equal(
    articleKey("https://example.org/story.php?page=2&id=7&utm_campaign=x"),
    "example.org/story.php?id=7&page=2",
  );
});

test("the path keeps its letter case", () => {
  assert.equal(articleKey("https://example.org/News/AllNews"), "example.org/News/AllNews");
});

test("an address that is not a web page has no key", () => {
  for (const address of ["chrome://extensions", "about:blank", "file:///tmp/a.html", "", "not an address"]) {
    assert.equal(articleKey(address), null, address);
  }
});
