// Why a claim stands where it does, as a home page row's status card says it. Pure
// functions over the fixture export (synthetic data) with events set per case.
import assert from "node:assert/strict";
import fs from "node:fs";
import { test } from "node:test";
import { assertNeutral } from "../src/lib/status.ts";
import { sampleReasons, statusReason } from "../src/lib/status-reason.ts";

const fixture = JSON.parse(fs.readFileSync(new URL("./fixture-export.json", import.meta.url), "utf8"));
const base = () => structuredClone(fixture.claims.find((entry) => entry.slug === "phase-claim"));
const plain = (text) => text?.replace(/[\u00a0\u202f]/g, " ");

let next = 100;
function trialEvent(trial_id, type, event_date, { phases = ["not_applicable"], state = null } = {}) {
  return {
    ...base().events[0],
    id: next++,
    type,
    event_date,
    trial_id,
    trial_phases: phases,
    trial_state: state,
  };
}

function claimWith(code, events, explained) {
  const claim = base();
  claim.status = { ...claim.status, code, explained_by: explained.map((event) => event.id) };
  claim.events = events;
  return claim;
}

test("trials that started with no phase are said, with why they do not count", () => {
  const regs = ["NCT1", "NCT2", "NCT3"].map((id) => trialEvent(id, "trial_registered", "2021-02-01"));
  const starts = ["NCT1", "NCT2", "NCT3"].map((id) =>
    trialEvent(id, "trial_status_change", "2021-07-15", { state: "completed" }),
  );
  const reason = statusReason(claimWith("trial_registered", [...regs, ...starts], regs));
  assert.match(reason, /^3 trials are on record\. All 3 have started, and the registry gives them no phase\./);
  assert.match(reason, /only a started trial with a phase moves a claim to Phase 1 or later/);
});

test("a registered trial that has not started is said as not started, with no phase note", () => {
  const reg = trialEvent("NCT9", "trial_registered", "2024-01-01", { phases: ["phase_1"] });
  assert.equal(statusReason(claimWith("trial_registered", [reg], [reg])), "1 trial is on record. It has not started yet.");
});

test("a phase is said with its trial and the day it started", () => {
  const reg = trialEvent("NCT5", "trial_registered", "2020-01-01", { phases: ["phase_2"] });
  const start = trialEvent("NCT5", "trial_status_change", "2021-07-15", { phases: ["phase_2"], state: "started" });
  assert.equal(
    plain(statusReason(claimWith("phase_2", [reg, start], [reg, start]))),
    "Trial NCT5 is recorded as a Phase 2 trial and started on 15 Jul 2021. No trial at a later phase has started.",
  );
});

test("no record to cite gives no reason", () => {
  assert.equal(statusReason(claimWith("preclinical_only", [], [])), null);
});

test("every template passes the verdict check", () => {
  assert.doesNotThrow(() => assertNeutral(sampleReasons()));
});
