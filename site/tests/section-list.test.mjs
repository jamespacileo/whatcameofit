// The section list (lib/blocks.ts, sectionList): every section by name, linked to its place on
// the page, with what it holds when given, and the list named for a screen reader.
import assert from "node:assert/strict";
import { test } from "node:test";
import { parseHTML } from "linkedom";
import { sectionList } from "../src/lib/blocks.ts";

test("a section's id is encoded in its link, so any id leads to its section", () => {
  const document = parseHTML(`<main>${sectionList("On this page", [{ id: "coverage-50%", name: "Coverage" }])}</main>`).document;
  const href = document.querySelector("a").getAttribute("href");
  assert.equal(href, "#coverage-50%25");
  assert.equal(decodeURIComponent(href.slice(1)), "coverage-50%");
});

test("each section is a link to its place on the page, with its count when it has one", () => {
  const html = sectionList("On this page", [
    { id: "why", name: "Why this status" },
    { id: "trials", name: "The trials", count: 4 },
    { id: "about", name: "About the <treatment>", count: "" },
  ]);
  const document = parseHTML(`<main>${html}</main>`).document;
  const nav = document.querySelector("nav.onpage");
  assert.equal(nav.getAttribute("aria-label"), "On this page");
  const links = [...nav.querySelectorAll("a")];
  assert.deepEqual(links.map((link) => link.getAttribute("href")), ["#why", "#trials", "#about"]);
  assert.deepEqual(links.map((link) => link.querySelector(".n")?.textContent ?? null), [null, "4", null]);
  // Every name is text, never markup.
  assert.equal(links[2].querySelector("span").textContent, "About the <treatment>");
  assert.equal(document.querySelectorAll("[aria-current]").length, 0, "nothing is marked until the script sees what is in view");
});
