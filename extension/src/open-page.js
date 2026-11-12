// Reading the page the reader has open, inside their own browser, and choosing what of
// it a registry search needs. This happens only when the reader presses the search
// button. What is sent to the site is the text read, the addresses that text links to,
// and, for a post, the platform's name. The page's own address is not sent.

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
  const own = location.pathname;
  const articles = [...document.querySelectorAll("article")];
  const linksToItself = (part) =>
    [...part.querySelectorAll("a[href]")].some((link) => link.getAttribute("href") === own || link.href === location.origin + own);
  const largest = [...articles].sort((a, b) => b.innerText.length - a.innerText.length)[0];
  const focus =
    articles.find(linksToItself) ??
    document.querySelector("shreddit-post") ??
    largest ??
    document.querySelector("main") ??
    document.body;
  return {
    title: document.title,
    selection: String(getSelection() ?? "").trim().slice(0, 20000),
    head: document.head.outerHTML.slice(0, CAP),
    focusHtml: focus.outerHTML.slice(0, CAP),
    focusText: (focus.innerText ?? "").slice(0, 20000),
    links: [...focus.querySelectorAll("a[href]")].slice(0, 300).map((link) => ({
      href: link.href,
      text: (link.innerText ?? "").trim().slice(0, 200),
    })),
    // Some platforms state a post's title and the address it links to on the post itself.
    postTitle: focus.getAttribute("post-title"),
    contentHref: focus.getAttribute("content-href"),
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

/**
 * A post's own words. A line that is only a link within the platform is left out: the
 * writer's name and handle, the time, the counts. So is a line with no letter or digit.
 */
function postText(collected, host) {
  const chrome = new Set(
    collected.links
      .filter((link) => sameSite(link.href, host))
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
    text = postText(collected, host);
    // A platform's tab title is 'Name on Platform: "the post" / Platform': the writer's
    // name first and the platform's last, neither of which is the post.
    if (text.length < ENOUGH) {
      text = collected.title
        .replace(/^[^:]{1,80}:\s*/, "")
        .replace(/\s[/|]\s[^/|]{1,30}$/, "")
        .replace(/^["“](.*)["”]$/s, "$1");
    }
  } else {
    text = pageAsText(readPage(`${collected.head}<body>${collected.focusHtml}</body>`));
  }
  text = text.trim().slice(0, MAX_TEXT);
  if (text.length < ENOUGH) return null;

  const links = [collected.contentHref, ...collected.links.map((link) => link.href)]
    .filter((href) => typeof href === "string" && /^https?:\/\//i.test(href) && href.length <= MAX_LINK)
    .filter((href) => !sameSite(href, host));
  const request = { text, links: [...new Set(links)].slice(0, MAX_LINKS) };
  return isPost ? { ...request, platform: read.platform } : request;
}
