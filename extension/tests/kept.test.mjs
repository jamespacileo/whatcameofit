import assert from "node:assert/strict";
import { test } from "node:test";
import {
  RECENT_CAP,
  acknowledged,
  addRecent,
  answerOf,
  candidatesOf,
  follow,
  followedNow,
  isFollowed,
  outletOf,
  unfollow,
} from "../src/kept.js";

const entry = (key, at = 1) => ({ key, url: `https://${key}`, title: key, outlet: "news.example.org", at, answer: { kind: "none" } });

test("the newest check leads, a page appears once, and the list is capped", () => {
  let list = [];
  for (let number = 0; number < RECENT_CAP + 3; number += 1) list = addRecent(list, entry(`news.example.org/${number}`, number));
  assert.equal(list.length, RECENT_CAP);
  assert.equal(list[0].key, `news.example.org/${RECENT_CAP + 2}`);

  const again = addRecent(list, entry(list[4].key, 99));
  assert.equal(again.length, RECENT_CAP);
  assert.equal(again[0].at, 99);
  assert.equal(again.filter((kept) => kept.key === list[4].key).length, 1);
});

test("an outlet is named by its host", () => {
  assert.equal(outletOf("https://www.news.example.org/a/b?c=1"), "news.example.org");
  assert.equal(outletOf("not an address"), "");
});

test("a check is kept as the little needed to show it again", () => {
  const tracked = answerOf({ kind: "tracked", claims: [{ headline: "One", page: "/one", status: "Phase 1 trial", meaning: "long words" }] });
  assert.deepEqual(tracked, { kind: "tracked", claims: [{ headline: "One", page: "/one", status: "Phase 1 trial" }] });

  const searched = answerOf({ kind: "answer", shown: {
    marked: "Automatic search. This has not been checked by a person.",
    lead: "This appears to report EX-1.",
    tracked: [{ headline: "Two", page: "/two" }],
    likely: [{ title: "Study", url: "https://clinicaltrials.gov/study/NCT00000001", why: "not kept" }],
  } });
  assert.equal(searched.kind, "searched");
  assert.equal(searched.unreviewed, "Automatic search. This has not been checked by a person.");
  assert.deepEqual(searched.records, [{ title: "Study", url: "https://clinicaltrials.gov/study/NCT00000001" }]);

  assert.deepEqual(answerOf({ kind: "untracked" }), { kind: "none" });
});

test("an entry's candidates are its claim pages, then its registry records", () => {
  const site = { url: "https://whatcameofit.example" };
  const kept = { ...entry("news.example.org/x"), answer: {
    kind: "searched",
    claims: [{ headline: "Two", page: "/two" }],
    records: [{ title: "Study", url: "https://clinicaltrials.gov/study/NCT00000001" }],
  } };
  assert.deepEqual(candidatesOf(kept, site).map((candidate) => candidate.url), [
    "https://whatcameofit.example/two",
    "https://clinicaltrials.gov/study/NCT00000001",
  ]);
  assert.deepEqual(candidatesOf(entry("news.example.org/y"), site), []);
});

const claim = { headline: "Reviewed claim", page: "/reviewed", status: "Trial registered", place: 2, meaning: "not kept" };
const index = (status, place) => ({ claims: { reviewed: { ...claim, status, place } } });

test("following remembers a claim as it stands, once", () => {
  const follows = follow(follow([], claim), claim);
  assert.deepEqual(follows, [{ headline: "Reviewed claim", page: "/reviewed", status: "Trial registered", place: 2 }]);
  assert.ok(isFollowed(follows, "/reviewed"));
  assert.deepEqual(unfollow(follows, "/reviewed"), []);
  assert.ok(!isFollowed([], "/reviewed"));
});

test("a followed claim is marked changed when its status or place moves", () => {
  const follows = follow([], claim);
  assert.equal(followedNow(follows, index("Trial registered", 2))[0].changed, false);

  const [moved] = followedNow(follows, index("Phase 1 trial", 3));
  assert.equal(moved.changed, true);
  assert.equal(moved.was, "Trial registered");
  assert.equal(moved.status, "Phase 1 trial");
});

test("a followed claim that is no longer published says so and shows no change", () => {
  const [gone] = followedNow(follow([], claim), { claims: {} });
  assert.equal(gone.gone, true);
  assert.equal(gone.changed, false);
});

test("seeing a changed claim remembers it as it now stands", () => {
  const now = index("Phase 1 trial", 3);
  const seen = acknowledged(follow([], claim), now, "/reviewed");
  assert.equal(followedNow(seen, now)[0].changed, false);
  assert.equal(seen[0].status, "Phase 1 trial");
});
