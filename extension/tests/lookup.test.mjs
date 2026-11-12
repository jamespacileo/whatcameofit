// What the popup shows for a page, decided from the lookup file. Synthetic data.
import assert from "node:assert/strict";
import { test } from "node:test";
import { isFresh, stateFor } from "../src/lookup.js";

const claim = (headline) => ({ headline, page: "/x", status: "Phase 1 trial", meaning: "m" });
const index = {
  last_checked: "11 Nov 2026",
  notices: ["First notice.", "Second notice."],
  articles: {
    "news.example.org/1": ["one"],
    "news.example.org/both": ["one", "two"],
    "news.example.org/gone": ["withdrawn"],
  },
  claims: { one: claim("Claim one"), two: claim("Claim two") },
};
const loaded = { index, savedAt: null };

test("a tracked article shows its claim with the notices and check date", () => {
  const state = stateFor("news.example.org/1", loaded);
  assert.equal(state.kind, "tracked");
  assert.deepEqual(state.claims.map((c) => c.headline), ["Claim one"]);
  assert.deepEqual(state.notices, index.notices);
  assert.equal(state.lastChecked, "11 Nov 2026");
  assert.equal(state.savedAt, null);
});

test("an article reporting two claims shows both", () => {
  const state = stateFor("news.example.org/both", loaded);
  assert.deepEqual(state.claims.map((c) => c.headline), ["Claim one", "Claim two"]);
});

test("an article no claim cites is untracked", () => {
  assert.equal(stateFor("news.example.org/other", loaded).kind, "untracked");
  // An address that points at a claim no longer in the file is untracked too.
  assert.equal(stateFor("news.example.org/gone", loaded).kind, "untracked");
});

test("an untracked page carries a registry endpoint only where the site answers one", () => {
  assert.equal(stateFor("news.example.org/other", loaded).live, null);
  const offering = { index: { ...index, live: "/api/lookup" }, savedAt: null };
  assert.equal(stateFor("news.example.org/other", offering).live, "/api/lookup");
  // A tracked article has its reviewed page: no search is offered in its place.
  assert.equal(stateFor("news.example.org/1", offering).live, undefined);
});

test("a tab that is not a web page asks for an article", () => {
  assert.equal(stateFor(null, loaded).kind, "no-page");
});

test("with no lookup file at all the site is reported unreachable", () => {
  assert.equal(stateFor("news.example.org/1", { index: null, savedAt: null }).kind, "unreachable");
});

test("a saved copy is used and its date passed on", () => {
  const state = stateFor("news.example.org/1", { index, savedAt: 1794400000000 });
  assert.equal(state.kind, "tracked");
  assert.equal(state.savedAt, 1794400000000);
});

test("a copy is fresh for six hours", () => {
  const sixHours = 6 * 60 * 60 * 1000;
  assert.equal(isFresh(1000, 1000 + sixHours - 1, sixHours), true);
  assert.equal(isFresh(1000, 1000 + sixHours, sixHours), false);
  assert.equal(isFresh(undefined, 5000, sixHours), false);
});
