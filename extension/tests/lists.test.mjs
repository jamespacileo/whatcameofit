// The reader's own lists, through the popup's controller: what is kept, what is shown,
// and that none of it asks the network for anything.
import assert from "node:assert/strict";
import { test } from "node:test";
import { createPopupController } from "../src/controller.js";

const tab = { id: 7, url: "https://news.example.org/report", title: "A report", key: "news.example.org/report" };
const claim = { headline: "Reviewed claim", page: "/reviewed", status: "Trial registered", place: 2 };
const tracked = (status = claim.status, place = claim.place) => ({
  articles: { [tab.key]: ["reviewed"] },
  claims: { reviewed: { ...claim, status, place } },
});

function setup({ index = tracked(), stored = {}, current = tab } = {}) {
  const store = { ...stored };
  const calls = { fetch: [], shown: [] };
  const controller = createPopupController({
    storage: {
      get: async (names) => Object.fromEntries([].concat(names).filter((name) => name in store).map((name) => [name, store[name]])),
      set: async (values) => { Object.assign(store, structuredClone(values)); },
    },
    site: { url: "https://whatcameofit.example" },
    readTab: async () => current,
    readPage: async () => null,
    isCurrentPage: async () => true,
    fetch: async (url) => { calls.fetch.push(url); return { ok: true, json: async () => index }; },
    describeAnswer: (found) => found,
    present: (state, kept) => calls.shown.push({ state, kept }),
  });
  return { controller, calls, store };
}

const settle = () => new Promise((resolve) => setTimeout(resolve, 0));

test("a checked page joins the reader's list, in the browser's own storage", async () => {
  const { controller, calls, store } = setup();
  await controller.open();
  await settle();

  assert.equal(store.recent.length, 1);
  assert.equal(store.recent[0].title, "A report");
  assert.equal(store.recent[0].outlet, "news.example.org");
  assert.deepEqual(store.recent[0].answer.claims, [{ headline: "Reviewed claim", page: "/reviewed", status: "Trial registered" }]);
  assert.equal(calls.shown.at(-1).kept.recent, 1);
  // The lookup file is the only thing asked for.
  assert.deepEqual(calls.fetch, ["https://whatcameofit.example/lookup.json"]);
});

test("a tab that is not a web page is not kept", async () => {
  const { controller, store } = setup({ current: { id: 1, url: "chrome://settings", key: null } });
  await controller.open();
  await settle();
  assert.equal(store.recent, undefined);
});

test("the list opens, shows one check's candidates, clears, and goes back without a request", async () => {
  const { controller, calls, store } = setup();
  await controller.open();
  const asked = calls.fetch.length;

  controller.showRecent();
  const list = calls.shown.at(-1).state;
  assert.equal(list.kind, "recent");
  assert.equal(list.entries[0].candidates[0].url, "https://whatcameofit.example/reviewed");

  controller.showEntry(tab.key);
  assert.equal(calls.shown.at(-1).state.kind, "entry");

  controller.back();
  assert.equal(calls.shown.at(-1).state.kind, "tracked");

  controller.clearRecent();
  await settle();
  assert.deepEqual(store.recent, []);
  assert.deepEqual(calls.shown.at(-1).state, { kind: "recent", entries: [] });
  assert.equal(calls.fetch.length, asked);
});

test("following and stopping are kept, and the page's own answer stays in view", async () => {
  const { controller, calls, store } = setup();
  await controller.open();

  controller.follow(claim);
  await settle();
  assert.deepEqual(store.follows, [claim]);
  assert.equal(calls.shown.at(-1).state.kind, "tracked");
  assert.deepEqual(calls.shown.at(-1).kept.followed, ["/reviewed"]);

  controller.unfollow("/reviewed");
  await settle();
  assert.deepEqual(store.follows, []);
  assert.equal(calls.shown.at(-1).kept.following, 0);
});

test("a followed claim that moved is announced once, where the reader sees it", async () => {
  const stored = { follows: [claim] };
  const first = setup({ index: tracked("Phase 1 trial", 3), stored });
  await first.controller.open();
  await settle();
  const shown = first.calls.shown.at(-1);
  assert.equal(shown.kept.was["/reviewed"], "Trial registered");
  // Seen on its own page, it is remembered as it now stands.
  assert.equal(first.store.follows[0].status, "Phase 1 trial");

  const second = setup({ index: tracked("Phase 1 trial", 3), stored: first.store });
  await second.controller.open();
  assert.deepEqual(second.calls.shown.at(-1).kept.was, {});
});

test("the following list marks a moved claim until the reader opens it", async () => {
  const other = { id: 8, url: "https://news.example.org/other", title: "Other", key: "news.example.org/other" };
  const index = { articles: {}, claims: { reviewed: { ...claim, status: "Phase 1 trial", place: 3 } } };
  const { controller, calls, store } = setup({ index, stored: { follows: [claim] }, current: other });
  await controller.open();
  assert.equal(calls.shown.at(-1).kept.changed, 1);

  controller.showFollowing();
  const [listed] = calls.shown.at(-1).state.claims;
  assert.equal(listed.changed, true);
  assert.equal(listed.was, "Trial registered");

  await controller.seen("/reviewed");
  assert.equal(store.follows[0].status, "Phase 1 trial");
  controller.showFollowing();
  assert.equal(calls.shown.at(-1).state.claims[0].changed, false);

  controller.unfollow("/reviewed", { fromList: true });
  assert.deepEqual(calls.shown.at(-1).state, { kind: "following", claims: [] });
});
