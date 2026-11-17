// Drawn cards are kept between builds: a card is drawn once, read back the same, and
// drawn again when anything it shows changes or the kept file is lost.
import assert from "node:assert/strict";
import fs from "node:fs";
import { registerHooks } from "node:module";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";

// The image module imports its neighbours without an extension, as the site's
// bundler allows; here a missing extension is read as ".ts".
registerHooks({
  resolve(specifier, context, next) {
    try {
      return next(specifier, context);
    } catch (error) {
      if (specifier.startsWith(".") && !path.extname(specifier)) return next(`${specifier}.ts`, context);
      throw error;
    }
  },
});
const store = fs.mkdtempSync(path.join(os.tmpdir(), "card-store-"));
process.env.CARD_STORE = store;
process.env.EXPORT_FILE = "tests/fixture-export.json";
const { topicPng } = await import("../src/lib/card-image.ts");
const fixture = JSON.parse(fs.readFileSync("tests/fixture-export.json", "utf8"));
const vertical = fixture.verticals.find((entry) => fixture.claims.some((claim) => claim.vertical === entry.slug));
const claims = fixture.claims.filter((claim) => claim.vertical === vertical.slug);
const kept = () => fs.readdirSync(store).filter((name) => name.endsWith(".png"));

test("a card is drawn once and read back the same", async () => {
  const first = await topicPng(vertical, claims);
  assert.equal(kept().length, 1);
  const file = path.join(store, kept()[0]);
  const drawnAt = fs.statSync(file).mtimeMs;
  const second = await topicPng(vertical, claims);
  assert.deepEqual(second, first);
  assert.equal(kept().length, 1);
  // Marking sets the time to the clock's whole millisecond, which can be a fraction
  // under the time the file system gave the new file within the same millisecond.
  assert.ok(fs.statSync(file).mtimeMs >= Math.floor(drawnAt), "a card that is read is marked as used");
});

test("a card that shows something else is drawn and kept separately", async () => {
  await topicPng({ ...vertical, title: `${vertical.title} and more` }, claims);
  assert.equal(kept().length, 2);
});

test("a kept card that is lost is drawn again", async () => {
  for (const name of kept()) fs.rmSync(path.join(store, name));
  const again = await topicPng(vertical, claims);
  assert.ok(again.length > 1000);
  assert.equal(kept().length, 1);
});

test("the store holds nothing half-written", () => {
  assert.deepEqual(fs.readdirSync(store).filter((name) => !name.endsWith(".png")), []);
});
