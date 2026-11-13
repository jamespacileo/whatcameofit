// Source pages: one per tracked article, with the claims that cite it.
import assert from "node:assert/strict";
import { test } from "node:test";

import { slugify, sourcesOf } from "../src/lib/sources.ts";

const article = (url, title, outlet = "Example News") => ({
  url,
  outlet,
  title,
  published_date: "2026-01-02",
  archive_url: null,
});
const claim = (slug, ...articles) => ({ slug, headline: slug, articles });

test("Scenario: Reader opens a source page", () => {
  const [source] = sourcesOf([claim("a", article("https://news.example.org/1", "Gel regrows enamel"))]);
  assert.equal(source.slug, "example-news-gel-regrows-enamel");
  assert.equal(source.title, "Gel regrows enamel");
  assert.deepEqual(source.claims.map((c) => c.slug), ["a"]);
  assert.equal("text" in source, false);
});

test("an article cited by two claims is one source naming both", () => {
  const shared = article("https://news.example.org/1", "Two findings");
  const sources = sourcesOf([claim("a", shared), claim("b", shared)]);
  assert.equal(sources.length, 1);
  assert.deepEqual(sources[0].claims.map((c) => c.slug), ["a", "b"]);
});

test("two articles with the same outlet and title get distinct slugs, in address order", () => {
  const sources = sourcesOf([
    claim("a", article("https://news.example.org/2", "Same title")),
    claim("b", article("https://news.example.org/1", "Same title")),
  ]);
  assert.deepEqual(
    sources.map((s) => [s.url, s.slug]),
    [
      ["https://news.example.org/1", "example-news-same-title"],
      ["https://news.example.org/2", "example-news-same-title-2"],
    ],
  );
});

test("slugs are lower case words, accents dropped, and not too long", () => {
  assert.equal(slugify("Le Monde: Café’s “cure”!"), "le-monde-cafes-cure");
  const [long] = sourcesOf([claim("a", article("https://x.example/1", "word ".repeat(40)))]);
  assert.ok(long.slug.length <= 70);
  assert.doesNotMatch(long.slug, /-$/);
});
