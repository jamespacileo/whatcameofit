// Exercise startup against the browser API shape, including Safari without notifications.
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";
import { test } from "node:test";

async function background(notifications, action) {
  const directory = await fs.mkdtemp(path.join(os.tmpdir(), "whatcameofit-background-"));
  const names = ["browser", "fetch"];
  const previous = new Map(names.map(name => [name, Object.getOwnPropertyDescriptor(globalThis, name)]));
  const listeners = {}, alarms = [], delivered = [];
  const saved = { follows: [{ page: "/example", headline: "Synthetic claim", status: "Trial registered", place: 2 }],
    reminders: [{ page: "/example", headline: "Synthetic claim", date: "2026-01-01" }], told: {} };
  const event = name => ({ addListener: fn => { listeners[name] = fn; } });
  try {
    for (const file of ["background.js", "watch.js", "kept.js", "lookup.js"]) {
      await fs.copyFile(new URL(`../src/${file}`, import.meta.url), path.join(directory, file));
    }
    await fs.writeFile(path.join(directory, "package.json"), '{"type":"module"}');
    await fs.writeFile(path.join(directory, "config.js"), 'export const SITE={url:"https://whatcameofit.example"};');
    globalThis.browser = {
      runtime: { onInstalled: event("installed"), onStartup: event("startup") },
      alarms: { create: (name, options) => { alarms.push({ name, ...options }); }, getAll: async () => [], clear: async () => {}, onAlarm: event("alarm") },
      storage: { local: { get: async () => structuredClone(saved), set: async value => Object.assign(saved, value) }, onChanged: event("changed") },
      ...(notifications ? { notifications: { create: async (id, message) => { delivered.push({ id, ...message }); return id; }, clear: async () => {}, onClicked: event("clicked") } } : {}),
    };
    globalThis.fetch = async () => Response.json({ claims: { example: { page: "/example", headline: "Synthetic claim", status: "Phase 1 trial", place: 3 } } });
    await import(pathToFileURL(path.join(directory, "background.js")));
    await action({ listeners, alarms, delivered, saved });
  } finally {
    for (const [name, descriptor] of previous) {
      if (descriptor) Object.defineProperty(globalThis, name, descriptor);
      else delete globalThis[name];
    }
    await fs.rm(directory, { recursive: true, force: true });
  }
}

test("Safari background starts and refreshes without notifications, preserving undelivered reminders", async () => {
  await background(false, async ({ listeners, alarms, saved }) => {
    await listeners.installed();
    assert.ok(alarms.some(alarm => alarm.name === "refresh"));
    await listeners.alarm({ name: "refresh" });
    assert.equal(saved.lookup.index.claims.example.status, "Phase 1 trial");
    assert.deepEqual(saved.told, {});
    await listeners.alarm({ name: "remind:/example|2026-01-01" });
    assert.equal(saved.reminders.length, 1);
    assert.equal(listeners.clicked, undefined);
  });
});

test("a browser with notifications delivers and records changes and reminders once", async () => {
  await background(true, async ({ listeners, delivered, saved }) => {
    await listeners.alarm({ name: "refresh" });
    await listeners.alarm({ name: "refresh" });
    assert.equal(delivered.length, 1);
    assert.equal(delivered[0].id, "change:/example");
    await listeners.alarm({ name: "remind:/example|2026-01-01" });
    assert.equal(delivered.length, 2);
    assert.deepEqual(saved.reminders, []);
  });
});
