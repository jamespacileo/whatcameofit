import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { test } from "node:test";
import { besideProblems, listingBeside } from "../scripts/listing-checks.mjs";

const fixture = JSON.parse(fs.readFileSync("tests/fixture-trials-listing.json", "utf8"));

test("only a listing that matches its schema and its export replaces the staged one", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-stage-listing-"));
  try {
    const source = path.join(temporary, "source.json");
    const target = path.join(temporary, "published-trials-listing.json");
    const exported = path.join(temporary, "published-export.json");
    fs.writeFileSync(exported, JSON.stringify({ claims: [{ slug: "phase-claim" }] }));
    const run = () => spawnSync(process.execPath, ["scripts/stage-trials-listing.mjs", source, target, exported], { encoding: "utf8" });
    const refused = (content, said) => {
      fs.writeFileSync(source, typeof content === "string" ? content : JSON.stringify(content));
      fs.writeFileSync(target, "previous snapshot");
      const result = run();
      assert.notEqual(result.status, 0);
      assert.match(result.stderr, said);
      assert.equal(fs.readFileSync(target, "utf8"), "previous snapshot");
      assert.deepEqual(fs.readdirSync(temporary).filter((name) => name.endsWith(".tmp")), []);
    };
    refused("invalid JSON", /snapshot unchanged/);
    const badState = structuredClone(fixture);
    badState.trials[1][4] = "recruiting";
    refused(badState, /does not match trials-listing\.schema\.json/);
    refused({ ...fixture, trials: [] }, /holds no trials/);
    // Stale: written against another export.
    const stale = structuredClone(fixture);
    stale.trials[1][8] = "a-claim-since-archived";
    refused(stale, /names 1 claim\(s\) the export does not publish \(a-claim-since-archived\)/);
    // Too large to be the one file a search fetches.
    const large = structuredClone(fixture);
    const title = "Synthetic ".repeat(40);
    large.trials = Array.from({ length: 21000 }, (_, at) => [`NCT${String(10000000 + at)}`, title, null, ["phase_3"], "under_way", "2026-01-01", [], [], null]);
    refused(large, /over the 8,388,608 a single file may be/);

    fs.writeFileSync(source, JSON.stringify(fixture, null, 2));
    const result = run();
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Staged 4 listed trials of active-since-2025 \(1 cited by a published claim/);
    const staged = fs.readFileSync(target, "utf8");
    assert.deepEqual(JSON.parse(staged), fixture);
    assert.equal(staged.trimEnd().includes("\n"), false, "the staged listing is one line");
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});

test("a deployment holds the listing beside its export to the staging checks", () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), "thenwhat-deploy-listing-"));
  try {
    const exported = path.join(temporary, "public-export.json");
    const beside = path.join(temporary, "public-trials-listing.json");
    assert.equal(listingBeside(exported), beside);
    assert.equal(listingBeside(path.join(temporary, "dated.json")), null);
    const data = { claims: [{ slug: "phase-claim" }] };
    // No listing: nothing to check, and no page opens for an uncited trial.
    assert.deepEqual(besideProblems(exported, data), []);
    fs.writeFileSync(beside, JSON.stringify(fixture));
    assert.deepEqual(besideProblems(exported, data), []);
    // Only published claims: the export no longer holds the claim the listing names.
    assert.match(besideProblems(exported, { claims: [] })[0], /names 1 claim\(s\) the export does not publish \(phase-claim\)/);
    const large = structuredClone(fixture);
    large.trials = Array.from({ length: 21000 }, (_, at) => [`NCT${String(10000000 + at)}`, "Synthetic ".repeat(40), null, ["phase_3"], "under_way", "2026-01-01", [], [], null]);
    fs.writeFileSync(beside, JSON.stringify(large));
    assert.match(besideProblems(exported, data)[0], /over the 8,388,608 a single file may be/);
    fs.writeFileSync(beside, "{}");
    assert.match(besideProblems(exported, data)[0], /does not match trials-listing\.schema\.json/);
    // An empty listing may be deployed: it opens nothing.
    fs.writeFileSync(beside, JSON.stringify({ ...fixture, trials: [] }));
    assert.deepEqual(besideProblems(exported, data), []);
  } finally {
    fs.rmSync(temporary, { recursive: true, force: true });
  }
});
