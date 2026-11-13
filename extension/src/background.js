// The extension's background check: twice a day it refreshes the site's lookup file and
// tells the reader, once, when a claim they follow has moved; and it shows a reminder
// the reader set when its day comes. It sends nothing but the request for the lookup
// file, which carries no address and nothing about the reader. Decisions are in
// watch.js; this file only wires them to the browser.
// Behaviour: openspec reader-follow-up, "Notification of a change", "Reminder in the extension".
import { SITE } from "./config.js";
import { CACHE_VERSION } from "./lookup.js";
import { alarmsFor, changeMessage, changesToTell, REFRESH_MINUTES, reminderMessage, reminderOf } from "./watch.js";

const api = globalThis.browser ?? globalThis.chrome;
const REFRESH = "refresh";
const ICON = "icons/128.png";

function notify(id, { title, message }) {
  return api.notifications.create(id, { type: "basic", iconUrl: ICON, title, message });
}

async function refresh() {
  const response = await fetch(`${SITE.url}/lookup.json`, { cache: "no-store" });
  if (!response.ok) return;
  const index = await response.json();
  await api.storage.local.set({ lookup: { version: CACHE_VERSION, index, savedAt: Date.now() } });
  const { follows = [], told = {} } = await api.storage.local.get(["follows", "told"]);
  const { tell, told: nowTold } = changesToTell(follows, index, told);
  for (const claim of tell) await notify(`change:${claim.page}`, changeMessage(claim));
  await api.storage.local.set({ told: nowTold });
}

async function syncReminders() {
  const { reminders = [] } = await api.storage.local.get("reminders");
  const existing = (await api.alarms.getAll()).map((alarm) => alarm.name);
  const { add, clear } = alarmsFor(reminders, existing);
  for (const name of clear) await api.alarms.clear(name);
  for (const { name, when } of add) api.alarms.create(name, { when: Math.max(when, Date.now() + 60_000) });
}

async function remindNow(name) {
  const { reminders = [], lookup = null } = await api.storage.local.get(["reminders", "lookup"]);
  const reminder = reminderOf(name, reminders);
  if (!reminder) return;
  const status = Object.values(lookup?.index?.claims ?? {}).find((claim) => claim.page === reminder.page)?.status ?? null;
  await notify(`remind:${reminder.page}`, reminderMessage(reminder, status));
  await api.storage.local.set({ reminders: reminders.filter((kept) => kept !== reminder) });
}

function setUp() {
  api.alarms.create(REFRESH, { periodInMinutes: REFRESH_MINUTES, delayInMinutes: 1 });
  void syncReminders();
}

api.runtime.onInstalled.addListener(setUp);
api.runtime.onStartup.addListener(setUp);

api.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === REFRESH) void refresh().catch(() => {});
  else void remindNow(alarm.name).catch(() => {});
});

api.storage.onChanged.addListener((changes, area) => {
  if (area === "local" && changes.reminders) void syncReminders();
});

// Pressing a notification opens the claim page it names.
api.notifications.onClicked.addListener((id) => {
  const page = id.replace(/^(change|remind):/, "");
  if (page.startsWith("/")) api.tabs.create({ url: `${SITE.url}${page}` });
  api.notifications.clear(id);
});
