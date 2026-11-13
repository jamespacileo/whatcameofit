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
import { capturePage, fingerprint, inspectVisible, publicPageUrl } from "./visual.js";

const api = globalThis.browser ?? globalThis.chrome;
const root = document.querySelector("#view");

document.querySelector("#name").textContent = SITE.name;

const controller = createPopupController({
  storage: api.storage.local,
  fetch,
  site: SITE,
  requiresSharingConsent: true,
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
    // A browser that cannot inspect media can still search readable text.
    const [{ result: visible }] = await api.scripting.executeScript({ target: { tabId: tab.id }, func: inspectVisible })
      .catch(() => [{ result: { address: result.address, media: [], sensitive: true, selectionOnly: result.selection.length >= 20 } }]);
    if (visible.address !== tab.url) throw Object.assign(new Error("Page changed"), { code: "page_changed" });
    const request = composeRequest(result, tab.url, { readAddress, readPage: readHtmlPage, pageAsText }) ??
      (visible.media.length ? { text: result.postTitle || result.title || "", links: [], platform: readAddress(tab.url).platform } : null);
    if (request) {
      request.links = await resolveShortLinks(request.links, (url, options) => fetch(url, { ...options, signal }));
      request.visualCandidate = visible.media.length > 0 && !visible.sensitive && !tab.incognito;
      request.selectionOnly = visible.selectionOnly;
      if (!visible.selectionOnly && !tab.incognito) {
        request.pageUrl = publicPageUrl(tab.url);
        request.contentFingerprint = await fingerprint({ text: request.text, links: request.links, media: visible.media });
      }
    }
    return request;
  },
  capturePage: (tab, signal) => capturePage(api, tab, signal),
  async isCurrentPage(tab) {
    const [current] = await api.tabs.query({ active: true, windowId: tab.windowId });
    return current?.id === tab.id && current.url === tab.url;
  },
  describeAnswer(found) {
    return { ...describeAnswer(found), likelyLead: LIVE.likelyLead, confidenceMeaning: LIVE.confidenceMeaning };
  },
  present(state, kept) {
    render(root, state, SITE, actions, kept);
  },
});

const actions = {
  open(address) {
    api.tabs.create({ url: address });
    window.close();
  },
  retry: controller.open,
  search: controller.search,
  previewVisual: controller.previewVisual,
  sendVisual: controller.sendVisual,
  cancelVisual: controller.cancelVisual,
  sharingView: controller.sharingView,
  enableSharing: controller.enableSharing,
  disableSharing: controller.disableSharing,
  // The reader's own lists, kept in this browser's storage and nowhere else.
  showRecent: controller.showRecent,
  showEntry: controller.showEntry,
  clearRecent: controller.clearRecent,
  showFollowing: controller.showFollowing,
  back: controller.back,
  follow: controller.follow,
  unfollow: controller.unfollow,
  async openFollowed(page) {
    await controller.seen(page);
    actions.open(SITE.url + page);
  },
};

window.addEventListener("pagehide", controller.close, { once: true });
controller.open();
