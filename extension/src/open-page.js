// Reading the page the reader has open, inside their own browser, and choosing what of
// it a registry search needs. This happens when the reader opens the popup on an
// untracked page. What is sent to the site is the text read, the addresses that text links to,
// and, for a post, the platform's name. The popup adds a cleaned source URL for caching.

const MAX_TEXT = 20000;
const MAX_LINKS = 30;
const MAX_LINK = 500;
// A selection shorter than this is a slip of the mouse, not a choice of text.
const CHOSEN_FROM = 20;
// Less than this and there is nothing to search on.
const ENOUGH = 40;

/**
 * Runs inside the open page and hands back its raw materials. It is sent into the page
 * as it stands, so it uses nothing from outside itself.
 *
 * On a page that holds one post or one story, the part that matters is the element that
 * links to the page's own address (a post carries a link to itself), else the page's
 * post element, else its largest article, else its main content.
 */
export function collectFromPage() {
  const CAP = 300000;
  // YouTube keeps recommendations and inactive Shorts in the same document. Read
  // only the renderer bound to this URL's video, never the surrounding page.
  if (/^(?:www\.|m\.)?youtube\.com$/.test(location.hostname)) {
    const url = new URL(location.href);
    const id = url.pathname === "/watch" && url.searchParams.getAll("v").length === 1
      ? url.searchParams.get("v")
      : url.pathname.match(/^\/(?:shorts|live)\/([\w-]{11})\/?$/)?.[1];
    const empty = {
      address: location.href, title: "", selection: String(getSelection() ?? "").trim().slice(0, 20000),
      head: "", focusHtml: "", focusText: "", links: [], postTitle: null, contentHref: null,
      mediaScope: { address: location.href, selector: null, videoOnly: true },
    };
    if (!id || !/^[\w-]{11}$/.test(id)) return empty;
    const short = url.pathname.startsWith("/shorts/");
    const renderers = short
      ? ["ytd-reel-video-renderer[is-active]", "ytm-reel-video-renderer[is-active]"]
      : ["ytd-watch-flexy", "ytm-watch"];
    // IDs are deliberately restricted above, so they are safe in a CSS selector.
    const selectors = renderers.flatMap(tag => [
      `${tag}[video-id="${id}"]`, `${tag}[data-video-id="${id}"]`,
    ]);
    // Current desktop Shorts has no is-active/video-id attributes. Its player's
    // title link names the playing video. A recommendation link cannot bind it.
    if (short) selectors.push(...["ytd-reel-video-renderer", "ytm-reel-video-renderer"].flatMap(tag =>
      [`/shorts/${id}`, `https://www.youtube.com/shorts/${id}`].map(href =>
        `${tag}:not([video-id]):not([data-video-id]):has(#shorts-player .ytp-title-link[href="${href}"])`)));
    const selector = selectors.find(value => document.querySelector(value));
    const focus = selector && document.querySelector(selector);
    if (!focus || focus.hidden || focus.hasAttribute("hidden")) return empty;
    const text = node => (node?.innerText ?? "").trim();
    const title = text(focus.querySelector(short
      ? "h1, h2, .reel-player-header-title, .title"
      : "#title h1, h1.ytd-watch-metadata, h1, .slim-video-information-title"));
    const description = focus.querySelector(short
      ? "#description, .reel-player-header-description"
      : "ytd-watch-metadata #description, #description, .slim-video-metadata-description");
    // Read only captions/transcript already loaded into the page. No hidden player
    // state, authenticated caption API, audio capture or automatic transcript click.
    const captions = [...focus.querySelectorAll(
      'ytd-transcript-segment-renderer .segment-text, transcript-segment-view-model [role="text"], .ytp-caption-segment')]
      .map(text).filter(Boolean).join("\n").slice(0, 12000);
    const descriptionText = text(description).slice(0, 8000);
    return {
      ...empty, title, postTitle: title,
      focusText: [descriptionText, captions].filter(Boolean).join("\n").slice(0, 20000),
      links: [...(description?.querySelectorAll("a[href]") ?? [])].slice(0, 300)
        // YouTube adds help links for features such as automatic dubbing inside
        // the description container. They are not the creator's article sources.
        .filter(link => !/^https:\/\/support\.google\.com\/youtube(?:\/|$)/.test(link.href))
        .map(link => ({ href: link.href, text: text(link).slice(0, 200) })),
      mediaScope: { address: location.href, selector, videoOnly: true,
        mediaSelector: short ? "video" : "#movie_player video, #player video" },
    };
  }
  const own = location.pathname;
  const articles = [...document.querySelectorAll('article, [role="article"]')];
  const linksToItself = (part) =>
    [...part.querySelectorAll("a[href]")].some((link) => link.getAttribute("href") === own || link.href === location.origin + own);
  const largest = [...articles].sort((a, b) => b.innerText.length - a.innerText.length)[0];
  let focus =
    articles.find(linksToItself) ??
    document.querySelector("shreddit-post") ??
    largest ??
    document.querySelector("main") ??
    document.body;
  // Hacker News uses table rows, including one row for every reply. Its numeric
  // item address identifies the story or comment we may read.
  const itemId = location.hostname === "news.ycombinator.com" ? new URL(location.href).searchParams.get("id") : null;
  if (itemId && /^\d+$/.test(itemId)) {
    const item = document.getElementById(itemId);
    focus = item?.matches("tr.athing") ? (item.querySelector(".commtext") ?? item) : null;
  }
  return {
    // Used only to reject a navigation race before sending the composed request.
    address: location.href,
    title: document.title,
    selection: String(getSelection() ?? "").trim().slice(0, 20000),
    head: document.head.outerHTML.slice(0, CAP),
    focusHtml: (focus?.outerHTML ?? "").slice(0, CAP),
    focusText: (focus?.innerText ?? "").slice(0, 20000),
    links: [...(focus?.querySelectorAll("a[href]") ?? [])].slice(0, 300).map((link) => ({
      href: link.href,
      text: (link.innerText ?? "").trim().slice(0, 200),
    })),
    // Some platforms state a post's title and the address it links to on the post itself.
    postTitle: focus?.getAttribute("post-title"),
    contentHref: focus?.getAttribute("content-href"),
  };
}

function sameSite(href, host) {
  try {
    const other = new URL(href).hostname.replace(/^www\./, "");
    return other === host || other.endsWith(`.${host}`) || host.endsWith(`.${other}`);
  } catch {
    return true;
  }
}

function destination(href, readAddress) {
  // Social sites wrap outgoing article links on their own host.
  try {
    const linked = readAddress(href);
    return linked.kind === "article" ? linked.address : href;
  } catch {
    return href;
  }
}

function articleLink(href) {
  try {
    return !/\.(?:png|jpe?g|gif|webp|avif|mp4|webm)(?:[?#]|$)/i.test(href) &&
      !/^(?:preview|external-preview|i|v)\.redd\.it$/.test(new URL(href).hostname);
  } catch { return false; }
}

/**
 * A post's own words. A line that is only a link within the platform is left out: the
 * writer's name and handle, the time, the counts. So is a line with no letter or digit.
 */
function postText(collected, host, readAddress) {
  const chrome = new Set(
    collected.links
      .filter((link) => sameSite(destination(link.href, readAddress), host))
      .flatMap((link) => link.text.split("\n"))
      .map((line) => line.trim())
      .filter(Boolean),
  );
  const lines = String(collected.focusText ?? "")
    .split("\n")
    .map((line) => line.trim())
    .filter((line) => /[\p{L}\p{N}]/u.test(line) && !chrome.has(line) && !/^@[\w.-]+$/.test(line));
  return [collected.postTitle, ...lines].filter(Boolean).join("\n");
}

/**
 * What to send for a registry search of the open page, or null when too little of it
 * could be read to search on.
 *
 * @param {ReturnType<typeof collectFromPage>} collected
 * @param {string} address the page's address: used here to tell a post from an article
 *   and to leave out the page's links to itself, and not sent
 * @param {{ readAddress: Function, readPage: Function, pageAsText: Function }} shared the
 *   site's own readers, so the site and the extension read a page the same way
 * @returns {{ text: string, links: string[], platform?: string } | null}
 */
export function composeRequest(collected, address, { readAddress, readPage, pageAsText }) {
  const read = readAddress(address);
  if (read.kind === "none") return null;
  const host = new URL(address).hostname.replace(/^www\./, "");
  const isPost = read.kind === "post";

  let text;
  if (collected.selection.length >= CHOSEN_FROM) {
    // The reader chose the words themselves: only those are sent.
    text = collected.selection;
  } else if (isPost) {
    text = postText(collected, host, readAddress);
    // A platform's tab title is 'Name on Platform: "the post" / Platform': the writer's
    // name first and the platform's last, neither of which is the post.
    if (!text) {
      text = collected.title.match(/^[^:]{1,80}:\s*["“]([\s\S]+)["”](?:\s[/|]\s[^/|]{1,30})?$/)?.[1] ?? "";
    }
  } else {
    text = pageAsText(readPage(`${collected.head}<body>${collected.focusHtml}</body>`));
  }
  text = text.trim().slice(0, MAX_TEXT);

  const links = [collected.contentHref, ...collected.links.map((link) => link.href)]
    .filter((href) => typeof href === "string" && /^https?:\/\//i.test(href))
    .map((href) => destination(href, readAddress))
    // A media file carries pixels, not an article the service can read as HTML.
    .filter(articleLink)
    .filter((href) => href.length <= MAX_LINK)
    .filter((href) => !sameSite(href, host));
  const outgoing = collected.selection.length >= CHOSEN_FROM ? [] : [...new Set(links)].slice(0, MAX_LINKS);
  if (text.length < ENOUGH && collected.selection.length < CHOSEN_FROM) {
    const hasArticle = isPost && outgoing.some((href) => {
      try {
        return ["article", "short"].includes(readAddress(href).kind);
      } catch {
        return false;
      }
    });
    if (!hasArticle) return null;
  }
  const request = { text, links: outgoing };
  return isPost ? { ...request, platform: read.platform } : request;
}
