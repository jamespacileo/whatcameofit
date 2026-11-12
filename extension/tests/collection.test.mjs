import assert from "node:assert/strict";
import { test } from "node:test";
import { collectFromPage } from "../src/open-page.js";

function element(text, links = [], comment = null) {
  return {
    innerText: text,
    outerHTML: `<div>${text}</div>`,
    matches: (selector) => selector === "tr.athing",
    querySelector: () => comment,
    querySelectorAll: () => links,
    getAttribute: () => null,
  };
}

function collectHackerNews(row) {
  const names = ["document", "location", "getSelection"];
  const saved = new Map(names.map((name) => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  try {
    globalThis.location = new URL("https://news.ycombinator.com/item?id=12345678");
    globalThis.getSelection = () => "";
    globalThis.document = {
      title: "Hacker News",
      head: { outerHTML: "<head></head>" },
      body: element("Unrelated thread, commenters and navigation that must stay out."),
      querySelectorAll: () => [],
      querySelector: () => null,
      getElementById: (id) => id === "12345678" ? row : null,
    };
    return collectFromPage();
  } finally {
    for (const [name, descriptor] of saved) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor);
      else delete globalThis[name];
    }
  }
}

test("a Hacker News story reads its requested item instead of the discussion", () => {
  const title = "EX-1 is being studied for a specific medical condition";
  const link = { href: "https://news.example.org/ex1", innerText: title };
  const collected = collectHackerNews(element(title, [link]));
  assert.equal(collected.focusText, title);
  assert.deepEqual(collected.links, [{ href: link.href, text: title }]);
  assert.doesNotMatch(collected.focusText, /Unrelated|commenters/);
});

test("a Hacker News comment reads only the requested comment body", () => {
  const body = element("This comment links to an EX-1 trial for a specific condition.");
  const collected = collectHackerNews(element("Author and timestamp", [], body));
  assert.equal(collected.focusText, body.innerText);
  assert.doesNotMatch(collected.focusText, /Author|timestamp|Unrelated/);
});

test("a missing Hacker News item does not read unrelated discussion", () => {
  const collected = collectHackerNews(null);
  assert.equal(collected.focusText, "");
  assert.deepEqual(collected.links, []);
});
