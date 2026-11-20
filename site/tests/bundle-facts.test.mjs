// What a deployment states it was built from (scripts/bundle-facts.mjs): the bundle's pairs and
// the launch measure, read from a copy of the fixture with the lab's manifest fields.
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { writeManifest } from "../../store/ingest/scripts/bundle-manifest.mjs";
import { bundleFacts, factsLine } from "../scripts/bundle-facts.mjs";

const FIXTURE = path.resolve("tests/bundle");

function copyWith(options) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-bundle-facts-"));
  fs.cpSync(FIXTURE, dir, { recursive: true });
  fs.rmSync(path.join(dir, "manifest.json"));
  writeManifest(dir, { madeAt: "2026-11-20T00:00:00Z", ...options });
  return dir;
}

test("the facts name the bundle, its pairs and the launch measure: distinct trials on pages over trials fetched", () => {
  const dir = copyWith({ labCommit: "93f3b99", trialsFetched: 40 });
  try {
    const facts = bundleFacts(dir);
    const manifest = JSON.parse(fs.readFileSync(path.join(dir, "manifest.json"), "utf8"));
    assert.equal(facts.version, manifest.checksum.slice("sha256:".length, "sha256:".length + 16));
    assert.equal(facts.pairs, manifest.counts.PairPage);
    assert.equal(facts.lab_commit, "93f3b99");
    // Each trial counts once, however many pairs show it.
    const shown = new Set();
    for (const name of fs.readdirSync(path.join(dir, "p12_pair_page"))) {
      for (const trial of JSON.parse(fs.readFileSync(path.join(dir, "p12_pair_page", name), "utf8")).trials) shown.add(trial.nct_id);
    }
    assert.equal(facts.trials_on_pages, shown.size);
    assert.equal(facts.launch_measure, Number((shown.size / 40).toFixed(4)));
    assert.match(factsLine(facts), new RegExp(`^Bundle ${facts.version}: 15 pairs, lab commit 93f3b99; launch measure [0-9.]+% \\(${shown.size} distinct trials on pages of 40 fetched\\)\\.$`));
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});

test("a manifest with no trials fetched states no launch measure, rather than one guessed", () => {
  const dir = copyWith({});
  try {
    const facts = bundleFacts(dir);
    assert.equal(facts.trials_fetched, null);
    assert.equal(facts.launch_measure, null);
    assert.match(factsLine(facts), /no launch measure: the manifest gives no coverage\.trials_fetched\.$/);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
});
