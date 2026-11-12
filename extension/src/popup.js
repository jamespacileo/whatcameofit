// Opening the popup checks the current tab locally, then automatically searches an
// untracked page where live lookup is enabled. No page is read in the background.
import { articleKey } from "./article-key.js";
import { SITE } from "./config.js";
import { createPopupController } from "./controller.js";
import { LIVE, describeAnswer } from "./live-lookup.js";
import { readAddress } from "./lookup-match.js";
import { collectFromPage, composeRequest } from "./open-page.js";
import { pageAsText, readPage as readHtmlPage } from "./page.js";
import { resolveShortLinks } from "./short-links.js";
import { render } from "./view.js";

const api = globalThis.browser ?? globalThis.chrome;
const root = document.querySelector("#view");

document.querySelector("#name").textContent = SITE.name;

const controller = createPopupController({
  storage: api.storage.local,
  fetch,
  site: SITE,
  async readTab() {
    const [tab] = await api.tabs.query({ active: true, currentWindow: true });
    return tab ? { ...tab, key: articleKey(tab.url) } : null;
  },
  async readPage(tab, signal) {
    const [{ result }] = await api.scripting.executeScript({ target: { tabId: tab.id }, func: collectFromPage });
    if (articleKey(result.address) !== tab.key) {
      const error = new Error("The open page changed during lookup.");
      error.code = "page_changed";
      throw error;
    }
    const request = composeRequest(result, tab.url, { readAddress, readPage: readHtmlPage, pageAsText });
    if (request) {
      request.links = await resolveShortLinks(request.links, (url, options) => fetch(url, { ...options, signal }));
    }
    return request;
  },
  async isCurrentPage(tab) {
    const current = await api.tabs.get(tab.id);
    return articleKey(current.url) === tab.key;
  },
  describeAnswer(found) {
    return { ...describeAnswer(found), likelyLead: LIVE.likelyLead, confidenceMeaning: LIVE.confidenceMeaning };
  },
  present(state) {
    render(root, state, SITE, actions);
  },
});

const actions = {
  open(address) {
    api.tabs.create({ url: address });
    window.close();
  },
  retry: controller.open,
  search: controller.search,
};

window.addEventListener("pagehide", controller.close, { once: true });
controller.open();
