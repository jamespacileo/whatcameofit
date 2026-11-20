// Every pair page, listing page and embed of tests/bundle, as the shared renderers write them,
// is the HTML kept in tests/goldens/ (tests/goldens.mjs). A change to a renderer that changes
// what a page shows changes these files with it, in the same pull request.
import assert from "node:assert/strict";
import { test } from "node:test";
import path from "node:path";
import { GOLDENS, keptGoldens, renderedGoldens, writeGoldens } from "./goldens.mjs";

test("every page the renderers write for the fixture is the HTML kept for it", () => {
  const rendered = renderedGoldens();
  // The built condition pages' goldens are held by tests/pair-pages.build-test.mjs.
  const renderers = (name) => !name.split(path.sep).join("/").startsWith("condition/");
  if (process.env.UPDATE_GOLDENS === "1") writeGoldens(rendered, GOLDENS, renderers);
  const kept = keptGoldens(GOLDENS, { within: renderers });
  assert.deepEqual([...kept.keys()].sort(), [...rendered.keys()].sort(), "a page has no golden, or a golden no page");
  for (const [name, html] of rendered) assert.equal(html, kept.get(name), name);
  // Each kind of page is held.
  for (const kind of ["pairs/", "embeds/", "listings/intervention-", "listings/clinical-", "listings/topic-"]) {
    assert.ok([...rendered.keys()].some((name) => name.startsWith(kind)), kind);
  }
});
