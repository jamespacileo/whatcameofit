// The background check's decisions. Scenario names are from openspec reader-follow-up.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  alarmName,
  alarmsFor,
  changeMessage,
  changesToTell,
  dueAt,
  reminderDay,
  reminderMessage,
  reminderOf,
  remind,
  unremind,
} from "../src/watch.js";

const index = (status, place = 2) => ({
  claims: { a: { headline: "Gel regrows enamel", page: "/enamel-gel", status, place } },
});
const followed = [{ headline: "Gel regrows enamel", page: "/enamel-gel", status: "Trial registered", place: 2 }];

test("Scenario: Change while the popup is closed", () => {
  const { tell, told } = changesToTell(followed, index("Phase 1 trial", 3));
  assert.equal(tell.length, 1);
  assert.deepEqual(changeMessage(tell[0]), {
    title: "Gel regrows enamel",
    message: "Was: Trial registered. Now: Phase 1 trial.",
  });
  assert.deepEqual(told, { "/enamel-gel": "Phase 1 trial|3" });
});

test("a change is told once, and again only if it moves on", () => {
  const first = changesToTell(followed, index("Phase 1 trial", 3));
  assert.equal(changesToTell(followed, index("Phase 1 trial", 3), first.told).tell.length, 0);
  assert.equal(changesToTell(followed, index("Phase 2 trial", 4), first.told).tell.length, 1);
});

test("an unchanged or unpublished claim is not told", () => {
  assert.equal(changesToTell(followed, index("Trial registered", 2)).tell.length, 0);
  assert.equal(changesToTell(followed, { claims: {} }).tell.length, 0);
});

test("a change into no signal is told in plain words", () => {
  const { tell } = changesToTell(followed, index("No trial record found", 1));
  assert.equal(changeMessage(tell[0]).message, "Was: Trial registered. Now: No trial record found.");
});

test("Scenario: Reminder falls due", () => {
  const reminders = remind([], { headline: "Gel regrows enamel", page: "/enamel-gel" }, "2027-05-13");
  const found = reminderOf(alarmName(reminders[0]), reminders);
  assert.deepEqual(found, { headline: "Gel regrows enamel", page: "/enamel-gel", date: "2027-05-13" });
  assert.deepEqual(reminderMessage(found, "Phase 1 trial"), {
    title: "Gel regrows enamel",
    message: "Time to look again. Now: Phase 1 trial.",
  });
  assert.equal(new Date(dueAt(found)).getHours(), 9);
});

test("Scenario: Reader removes a reminder", () => {
  const reminders = remind([], { headline: "Gel", page: "/enamel-gel" }, "2027-05-13");
  const name = alarmName(reminders[0]);
  const kept = unremind(reminders, "/enamel-gel");
  assert.equal(reminderOf(name, kept), null);
  assert.deepEqual(alarmsFor(kept, [name, "refresh"]), { add: [], clear: [name] });
});

test("one reminder per claim, and alarms follow the kept list", () => {
  let reminders = remind([], { headline: "Gel", page: "/enamel-gel" }, "2027-05-13");
  reminders = remind(reminders, { headline: "Gel", page: "/enamel-gel" }, "2027-11-13");
  assert.equal(reminders.length, 1);
  const { add, clear } = alarmsFor(reminders, ["remind:/enamel-gel|2027-05-13"]);
  assert.deepEqual(add.map((alarm) => alarm.name), ["remind:/enamel-gel|2027-11-13"]);
  assert.deepEqual(clear, ["remind:/enamel-gel|2027-05-13"]);
});

test("six months and a year, clamped to the month's end", () => {
  assert.equal(reminderDay("six-months", "2026-11-13"), "2027-05-13");
  assert.equal(reminderDay("year", "2026-11-13"), "2027-11-13");
  assert.equal(reminderDay("six-months", "2026-08-31"), "2027-02-28");
});
