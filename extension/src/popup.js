// The popup: reads the current tab's address when opened, compares it with the site's
// lookup file inside the browser, and shows the result. The address is never sent anywhere,
// and opening the popup makes one request: for the lookup file itself.
//
// For a page that is not tracked, the reader may ask for a registry search. Only then is
// the page read, here in the browser, and its text and the links in it sent to the site.
import { articleKey } from "./article-key.js";
import { SITE } from "./config.js";
import { LIVE, describeAnswer } from "./live-lookup.js";
import { readAddress } from "./lookup-match.js";
import { isFresh, stateFor } from "./lookup.js";
import { collectFromPage, composeRequest } from "./open-page.js";
import { pageAsText, readPage } from "./page.js";
import { render } from "./view.js";

const api = globalThis.browser ?? globalThis.chrome;
const SIX_HOURS = 6 * 60 * 60 * 1000;
const root = document.querySelector("#view");

document.querySelector("#name").textContent = SITE.name;

async function currentAddress() {
  try {
    const [tab] = await api.tabs.query({ active: true, currentWindow: true });
    return tab?.url ?? null;
  } catch {
    return null;
  }
}

/** The lookup file: the saved copy while fresh, else a new one, else the saved copy with its date. */
async function loadIndex() {
  const { lookup: saved = null } = await api.storage.local.get("lookup");
  if (saved && isFresh(saved.savedAt, Date.now(), SIX_HOURS)) {
    return { index: saved.index, savedAt: null };
  }
  try {
    const response = await fetch(`${SITE.url}/lookup.json`, { cache: "no-store" });
    if (!response.ok) throw new Error(`status ${response.status}`);
    const index = await response.json();
    await api.storage.local.set({ lookup: { index, savedAt: Date.now() } });
    return { index, savedAt: null };
  } catch {
    return saved ? { index: saved.index, savedAt: saved.savedAt } : { index: null, savedAt: null };
  }
}

// Where the site answers a registry search; set once the lookup file is read.
let live = null;

/** Read the open page in the browser and ask the site which trial records it reports. */
async function search() {
  render(root, { kind: "searching" }, SITE, actions);
  let request = null;
  try {
    const [tab] = await api.tabs.query({ active: true, currentWindow: true });
    const [{ result }] = await api.scripting.executeScript({ target: { tabId: tab.id }, func: collectFromPage });
    request = composeRequest(result, tab.url, { readAddress, readPage, pageAsText });
  } catch {
    request = null;
  }
  if (request === null) {
    render(root, { kind: "too-little" }, SITE, actions);
    return;
  }
  try {
    const response = await fetch(SITE.url + live, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
    const found = await response.json();
    if (!response.ok) {
      render(root, { kind: "refused", code: found?.error ?? "failed" }, SITE, actions);
      return;
    }
    const shown = { ...describeAnswer(found), likelyLead: LIVE.likelyLead };
    render(root, { kind: "answer", shown }, SITE, actions);
  } catch {
    render(root, { kind: "refused", code: "failed" }, SITE, actions);
  }
}

const actions = {
  open(address) {
    api.tabs.create({ url: address });
    window.close();
  },
  retry: run,
  search,
};

async function run() {
  render(root, { kind: "checking" }, SITE, actions);
  const address = await currentAddress();
  const key = address ? articleKey(address) : null;
  const loaded = key === null ? { index: null, savedAt: null } : await loadIndex();
  const state = stateFor(key, loaded);
  live = state.live ?? null;
  render(root, state, SITE, actions);
}

run();
