// The key a pull request's copy carries: the same for the same site, different when
// anything the copy is made from differs.
import assert from "node:assert/strict";
import { test } from "node:test";
import { SETTINGS, keyFrom } from "../scripts/build-key.mjs";

const FILES = [
  { path: "site/src/pages/index.astro", blob: "a1" },
  { path: "site/data/published-export.json", blob: "b2" },
  { path: "site/worker/index.mjs", blob: "c3" },
];
const SET = { SITE_URL: "https://example.org", PUBLIC_BUILD: "1" };

test("the same files and settings give the same key, in whatever order they are listed", () => {
  assert.equal(keyFrom(FILES, SET), keyFrom([...FILES].reverse(), { ...SET }));
  assert.match(keyFrom(FILES, SET), /^[0-9a-f]{64}$/);
});

test("a changed page, a changed export and a changed Worker each change the key", () => {
  for (const index of FILES.keys()) {
    const changed = FILES.map((file, at) => (at === index ? { ...file, blob: "changed" } : file));
    assert.notEqual(keyFrom(changed, SET), keyFrom(FILES, SET), FILES[index].path);
  }
});

test("an added file and a renamed file change the key", () => {
  assert.notEqual(keyFrom([...FILES, { path: "site/public/new.svg", blob: "d4" }], SET), keyFrom(FILES, SET));
  const renamed = FILES.map((file, at) => (at === 0 ? { ...file, path: "site/src/pages/home.astro" } : file));
  assert.notEqual(keyFrom(renamed, SET), keyFrom(FILES, SET));
});

test("every setting the build or the Worker reads changes the key", () => {
  for (const name of SETTINGS) {
    assert.notEqual(keyFrom(FILES, { ...SET, [name]: "another value" }), keyFrom(FILES, SET), name);
  }
});

test("a setting that is unset and one that is empty are the same", () => {
  assert.equal(keyFrom(FILES, { ...SET, LOOKUP_URL: "" }), keyFrom(FILES, SET));
});

test("a test or a note under site/ does not change the key", () => {
  const more = [
    ...FILES,
    { path: "site/tests/pages.test.mjs", blob: "e5" },
    { path: "site/README.md", blob: "f6" },
  ];
  assert.equal(keyFrom(more, SET), keyFrom(FILES, SET));
});

test("a setting nothing reads does not change the key", () => {
  assert.equal(keyFrom(FILES, { ...SET, HOME: "/somewhere" }), keyFrom(FILES, SET));
});
