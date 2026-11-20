import assert from "node:assert/strict";
import { test } from "node:test";

import { dist, installGlobals, launchEntry, manifest, SITE } from "./package-support.mjs";

const reminder = { page: "/example", headline: "Synthetic claim", date: "2026-01-01" };
const reminderAlarm = { name: `remind:${reminder.page}|${reminder.date}` };

async function startBackground(t, { notifications } = {}) {
  const listeners = {}, alarms = [], delivered = [], requests = [];
  const saved = {
    follows: [{ page: "/example", headline: "Synthetic claim", status: "Trial registered", place: 2 }],
    reminders: [reminder],
    told: {},
  };
  const event = (name) => ({ addListener: (fn) => { listeners[name] = fn; } });
  const browser = {
    runtime: { onInstalled: event("installed"), onStartup: event("startup") },
    alarms: { create: (name) => alarms.push(name), getAll: async () => [], onAlarm: event("alarm") },
    storage: {
      local: { get: async () => structuredClone(saved), set: async (value) => Object.assign(saved, value) },
      onChanged: event("changed"),
    },
  };
  if (notifications) {
    browser.notifications = {
      create: async (id) => { delivered.push(id); return id; },
      onClicked: event("clicked"),
    };
  }
  installGlobals(t, {
    browser,
    async fetch(url, options) {
      requests.push({ url, method: options?.method ?? "GET" });
      return Response.json({ claims: { example: { ...saved.follows[0], status: "Phase 1 trial", place: 3 } } }, {
        headers: { ETag: '"current"' },
      });
    },
  });

  assert.equal(manifest.background.type, "module");
  await launchEntry(new URL(manifest.background.service_worker, dist));
  return { listeners, alarms, delivered, requests, saved };
}

test("packaged background refreshes the lookup in Safari and keeps undelivered reminders", async (t) => {
  const { listeners, alarms, requests, saved } = await startBackground(t);
  await listeners.installed();
  assert.ok(alarms.includes("refresh"));
  await listeners.alarm({ name: "refresh" });
  assert.deepEqual(requests, [{ url: `${SITE.url}/lookup/2.json`, method: "GET" }]);
  assert.equal(saved.lookup.file.claims.example.status, "Phase 1 trial");
  assert.equal(saved.lookup.path, "/lookup/2.json");
  assert.equal(saved.lookup.etag, '"current"');
  assert.deepEqual(saved.told, {});
  await listeners.alarm(reminderAlarm);
  assert.deepEqual(saved.reminders, [reminder]);
});

test("packaged background delivers a change and a reminder once when notifications are available", async (t) => {
  const { listeners, delivered, saved } = await startBackground(t, { notifications: true });
  for (let i = 0; i < 2; i++) {
    await listeners.alarm({ name: "refresh" });
    await listeners.alarm(reminderAlarm);
  }
  assert.deepEqual(delivered, ["change:/example", "remind:/example"]);
  assert.deepEqual(saved.reminders, []);
});
