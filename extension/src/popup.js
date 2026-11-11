// The popup: reads the current tab's address when opened, compares it with the site's
// lookup file inside the browser, and shows the result. The address is never sent anywhere;
// the only request made is for the lookup file itself.
import { articleKey } from "./article-key.js";
import { SITE } from "./config.js";
import { isFresh, stateFor } from "./lookup.js";
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

const actions = {
  open(address) {
    api.tabs.create({ url: address });
    window.close();
  },
  retry: run,
};

async function run() {
  render(root, { kind: "checking" }, SITE, actions);
  const address = await currentAddress();
  const key = address ? articleKey(address) : null;
  const loaded = key === null ? { index: null, savedAt: null } : await loadIndex();
  render(root, stateFor(key, loaded), SITE, actions);
}

run();
