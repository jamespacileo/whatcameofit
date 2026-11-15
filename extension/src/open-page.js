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
// An article this long, in characters and in words, is read from its words alone.
const READABLE_FROM = 1000;
const READABLE_WORDS = 150;
// What a page's structured data may call an ordinary written article.
const ARTICLE_TYPES = new Set([
  "Article", "NewsArticle", "ReportageNewsArticle", "AnalysisNewsArticle", "BackgroundNewsArticle",
  "OpinionNewsArticle", "ReviewNewsArticle", "AskPublicNewsArticle", "ScholarlyArticle",
  "MedicalScholarlyArticle", "TechArticle", "Report",
]);
// A post, a thread or a live page is not an ordinary article whatever its length.
const POST_TYPES = new Set(["SocialMediaPosting", "DiscussionForumPosting", "LiveBlogPosting", "BlogPosting"]);
// Words saying that the claim is in a picture, chart or clip rather than in the text.
const IMAGE_CLAIM = new RegExp([
  String.raw`\b(?:screenshot|screen grab|infographic)s?\b`,
  String.raw`\b(?:see|watch|look at|shown in|pictured in|in) (?:the|this|our) (?:image|photo|picture|chart|graph|graphic|video|clip|slide|figure)s?\b`,
  String.raw`\b(?:image|photo|picture|chart|graph|graphic|video|clip)s? (?:above|below)\b`,
  String.raw`\b(?:above|below) (?:image|photo|picture|chart|graph|graphic|video|clip)s?\b`,
].join("|"), "i");

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
  const host = location.hostname.replace(/^www\./, "");
  // These detail pages also render replies, recommendations or neighbouring posts.
  // Bind the reading to the requested post before collecting any words or pixels.
  if (["instagram.com", "threads.com", "threads.net", "t.me", "telegram.me", "tiktok.com", "linkedin.com", "bsky.app"].includes(host)) {
    const empty = {
      address: location.href, title: "", selection: String(getSelection() ?? "").trim().slice(0, 20000),
      head: "", focusHtml: "", focusText: "", links: [], postTitle: null, contentHref: null, structured: [],
      mediaScope: { address: location.href, selector: null, videoOnly: false },
    };
    const visible = node => {
      const r = node.getBoundingClientRect();
      let left = Math.max(0, r.left), right = Math.min(innerWidth, r.right);
      let top = Math.max(0, r.top), bottom = Math.min(innerHeight, r.bottom);
      // This collector is injected on its own. Keep clipping in step with the
      // independently injected screenshot inspector in visual.js.
      for (let item = node; item; item = item.parentElement) {
        const style = getComputedStyle(item);
        if (item.hidden || style.display === "none" || style.visibility === "hidden") return false;
        if (item === node) continue;
        const bounds = item.getBoundingClientRect();
        if (/^(hidden|clip|auto|scroll)$/.test(style.overflowX)) {
          left = Math.max(left, bounds.left); right = Math.min(right, bounds.right);
        }
        if (/^(hidden|clip|auto|scroll)$/.test(style.overflowY)) {
          top = Math.max(top, bounds.top); bottom = Math.min(bottom, bounds.bottom);
        }
      }
      return r.width > 0 && r.height > 0 && right > left && bottom > top;
    };
    const selectorFor = node => {
      const parts = [];
      for (let item = node; item && item !== document.documentElement; item = item.parentElement) {
        const peers = [...(item.parentElement?.children ?? [])].filter(other => other.tagName === item.tagName);
        parts.unshift(`${item.tagName.toLowerCase()}:nth-of-type(${peers.indexOf(item) + 1})`);
      }
      return parts.length ? `html > ${parts.join(" > ")}` : null;
    };
    const fromNode = (node, mediaRoot = node) => ({
      ...empty, focusText: (node?.innerText ?? "").slice(0, 20000),
      links: [...(node?.querySelectorAll("a[href]") ?? [])].slice(0, 300)
        .map(a => ({ href: a.href, text: (a.innerText ?? "").slice(0, 200) })),
      mediaScope: { address: location.href, selector: mediaRoot ? selectorFor(mediaRoot) : null,
        videoOnly: host === "tiktok.com" && location.pathname.includes("/video/") },
    });
    if (host === "linkedin.com" || host === "bsky.app") {
      const postKey = value => {
        try {
          const u = new URL(value, location.href);
          if (u.hostname.replace(/^www\./, "") !== host) return null;
          if (host === "linkedin.com") return u.pathname.match(/-(?:activity|ugcPost|share)-(\d+)(?:-|\/|$)/)?.[1] ??
            u.pathname.match(/^\/feed\/update\/urn:li:(?:activity|ugcPost|share):(\d+)(?:\/|$)/)?.[1] ?? null;
          return u.pathname.match(/^\/profile\/([^/]+)\/post\/([\w]+)(?:\/|$)/)?.slice(1).join("/") ?? null;
        } catch { return null; }
      };
      const wanted = postKey(location.href);
      if (!wanted) return empty;
      const selector = host === "linkedin.com" ? '[role="listitem"][componentkey^="update-card-focus"]'
        : '[data-testid^="postThreadItem-by-"]';
      const ownedLinks = node => [...node.querySelectorAll("a[href]")].filter(link => {
        if (link.closest(selector) !== node) return false;
        if (host === "bsky.app") return postKey(link.href) && /\/(?:liked-by|reposted-by|quotes)\/?$/.test(new URL(link.href, location.href).pathname) &&
          !!link.querySelector('[data-testid="likeCount-expanded"], [data-testid="repostCount-expanded"], [data-testid="quoteCount-expanded"]');
        return !link.closest('[data-testid="expandable-text-box"], [componentkey^="comment"]') &&
          !!link.querySelector('figure img, [aria-labelledby], svg[id^="paper-plane"]');
      });
      const bound = [...document.querySelectorAll(selector)].filter(node => {
        if (!visible(node) || node.querySelector(selector)) return false;
        const keys = new Set(ownedLinks(node).map(link => postKey(link.href)).filter(Boolean));
        return keys.size === 1 && keys.has(wanted);
      });
      // Never fall back to main: signed-in sidebars and replies are outside the
      // addressed report, even when no post has finished loading yet.
      if (bound.length === 1) {
        const node = bound[0];
        if (host === "bsky.app") return fromNode(node);
        const captions = [...node.querySelectorAll('[data-testid="expandable-text-box"]')]
          .filter(item => !item.closest('[componentkey^="comment"]'));
        const media = ownedLinks(node).flatMap(link => [...link.querySelectorAll('figure img')]).filter(visible);
        // LinkedIn can nest replies and the reader's draft below the post. Only
        // its caption and uniquely owned attachment supply words and pixels.
        if (captions.length === 1) return fromNode(captions[0], media.length === 1 ? media[0] : null);
      }
      // Public caption metadata also supports signed-out or changing layouts,
      // but cannot authorize a screenshot of an unbound page.
      const metaUrl = document.querySelector('meta[property="og:url"]')?.getAttribute("content");
      const caption = document.querySelector('meta[property="og:description"]')?.getAttribute("content");
      if (!bound.length && metaUrl && postKey(metaUrl) === wanted && caption?.trim()) {
        return { ...empty, focusText: caption.trim().slice(0, 20000),
          links: [...caption.matchAll(/https?:\/\/[^\s<>"“”]+/g)].slice(0, 30)
            .map(([href]) => ({ href: href.replace(/[.,;)]+$/, ""), text: "" })) };
      }
      return empty;
    }
    if (host === "t.me" || host === "telegram.me") {
      const match = location.pathname.match(/^\/(?:s\/)?([\w]+)\/(\d+)\/?$/);
      if (!match) return empty;
      const post = document.querySelector(`[data-post="${match[1]}/${match[2]}"]`);
      return fromNode(post?.querySelector(".tgme_widget_message_text"), post);
    }
    if (host === "tiktok.com") {
      const key = value => {
        if (typeof value !== "string" || !value.trim()) return null;
        try { const u = new URL(value, location.href); return u.hostname.replace(/^www\./, "") === host
          ? u.pathname.match(/^\/@([^/]+)\/(video|photo)\/(\d+)\/?$/)?.slice(1).join("/") : null; }
        catch { return null; }
      };
      const wanted = key(location.href);
      if (!wanted) return empty;
      const items = [...document.querySelectorAll('article[data-e2e="recommend-list-item-container"]')];
      // Some layouts carry a permalink on the current item. The initial feed layout
      // instead binds item zero through its canonical URL; never guess another item.
      const bound = items.filter(item => visible(item) && [...item.querySelectorAll("a[href]")].some(a => key(a.href) === wanted));
      const canonical = document.querySelector('link[rel="canonical"]')?.getAttribute("href");
      const initial = items.find(item => item.getAttribute("data-scroll-index") === "0" && visible(item));
      const post = bound.length === 1 ? bound[0] : bound.length === 0 && canonical && key(canonical) === wanted ? initial : null;
      if (!post) return empty;
      const caption = post.querySelector('[data-e2e="video-desc"], [data-e2e="browse-video-desc"]');
      const collected = fromNode(caption, post);
      const metaUrl = document.querySelector('meta[property="og:url"]')?.getAttribute("content");
      const description = document.querySelector('meta[property="og:description"]')?.getAttribute("content");
      if (metaUrl && key(metaUrl) === wanted && description?.trim()) {
        collected.focusText = description.trim().slice(0, 20000);
        collected.links = [...description.matchAll(/https?:\/\/[^\s<>"“”]+/g)].slice(0, 30)
          .map(([href]) => ({ href: href.replace(/[.,;)]+$/, ""), text: "" }));
      }
      return collected;
    }
    const key = value => {
      if (typeof value !== "string" || !value.trim()) return null;
      try {
        const u = new URL(value, location.href), h = u.hostname.replace(/^www\./, "");
        if (host === "instagram.com") return h === host ? u.pathname.match(/^\/(?:[^/]+\/)?(?:p|reel|tv)\/([\w-]+)(?:\/|$)/)?.[1] : null;
        return ["threads.com", "threads.net"].includes(h) ? u.pathname.match(/^\/@[^/]+\/post\/([\w-]+)(?:\/|$)/)?.[1] : null;
      } catch { return null; }
    };
    const meta = property => document.querySelector(`meta[property="${property}"]`)?.getAttribute("content") ?? "";
    const wanted = key(location.href);
    if (!wanted || key(meta("og:url")) !== wanted) return empty;
    let caption = meta("og:description");
    if (host === "instagram.com") {
      // Instagram wraps the public caption in attribution/counts. Preserve only the
      // quoted caption, including its internal quotes and non-Latin writing.
      const unwrap = value => value.replace(/[\u200e\u200f]/g, "").match(/:\s*["“]([\s\S]*)["”]\.?\s*$/)?.[1] ?? "";
      caption = unwrap(caption) || unwrap(meta("og:title"));
    }
    const links = [...caption.matchAll(/https?:\/\/[^\s<>"“”]+/g)].slice(0, 30)
      .map(([href]) => ({ href: href.replace(/[.,;)]+$/, ""), text: "" }));
    // Media identity is independent of caption availability. An image-only post
    // still has a visual path; a lone unrelated video never supplies that path.
    const mediaKey = value => {
      if (!value) return "";
      try { const u = new URL(value, location.href); return u.origin + u.pathname; }
      catch { return ""; }
    };
    const imageKey = mediaKey(meta("og:image"));
    const videoKey = mediaKey(meta("og:video:secure_url") || meta("og:video"));
    const allMedia = [...document.querySelectorAll("main img, main video")];
    const media = allMedia.filter(visible);
    const anchors = imageKey ? allMedia.filter(n => n.tagName === "IMG" && mediaKey(n.currentSrc || n.src) === imageKey) : [];
    const images = anchors.filter(visible);
    const videos = media.filter(n => n.tagName === "VIDEO" &&
      (videoKey && mediaKey(n.currentSrc || n.src) === videoKey ||
       imageKey && mediaKey(n.poster || n.getAttribute("poster")) === imageKey));
    let primary = images.length === 1 ? images[0] : videos.length === 1 ? videos[0] : null;
    if (host === "instagram.com" && anchors.length === 1) {
      const anchor = anchors[0], list = anchor.closest("li")?.parentElement;
      if (list?.matches("ul, ol") && [...list.children].filter(n => n.tagName === "LI").length > 1) {
        // A metadata image identifies this slide list even after it scrolls out of
        // view. Never widen this boundary to main or a list of recommended posts.
        primary = null;
        let viewport = list.parentElement;
        while (viewport && !viewport.matches("main, article, body") &&
          !/^(hidden|clip|auto|scroll)$/.test(getComputedStyle(viewport).overflowX)) viewport = viewport.parentElement;
        const frame = viewport?.getBoundingClientRect(), original = anchor.getBoundingClientRect();
        const bounded = viewport && !viewport.matches("main, article, body") && frame.width > 0 && frame.height > 0 &&
          frame.width <= original.width * 1.25 && frame.height <= original.height * 1.25;
        const conflicting = [...list.querySelectorAll("a[href]")].some(link => key(link.href) && key(link.href) !== wanted);
        const slides = media.filter(node => node.closest("li")?.parentElement === list);
        if (bounded && !conflicting && slides.length === 1) primary = slides[0];
      }
    }
    return { ...empty, focusText: caption.slice(0, 20000), links,
      mediaScope: { address: location.href, selector: primary ? selectorFor(primary) : null, videoOnly: primary?.tagName === "VIDEO" } };
  }
  // YouTube keeps recommendations and inactive Shorts in the same document. Read
  // only the renderer bound to this URL's video, never the surrounding page.
  if (/^(?:www\.|m\.)?youtube\.com$/.test(location.hostname)) {
    const url = new URL(location.href);
    const id = url.pathname === "/watch" && url.searchParams.getAll("v").length === 1
      ? url.searchParams.get("v")
      : url.pathname.match(/^\/(?:shorts|live)\/([\w-]{11})\/?$/)?.[1];
    const empty = {
      address: location.href, title: "", selection: String(getSelection() ?? "").trim().slice(0, 20000),
      head: "", focusHtml: "", focusText: "", links: [], postTitle: null, contentHref: null, structured: [],
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
    // What the page says it is, for other software: read here only to tell an ordinary
    // article from a post or a gallery, and never sent.
    structured: [...document.querySelectorAll('script[type="application/ld+json"]')].slice(0, 20)
      .map((node) => (node.textContent ?? "").slice(0, 100000)),
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

/** The types a page's structured data gives its top-level things, in an @graph too. */
function structuredTypes(collected) {
  const blocks = [...(Array.isArray(collected.structured) ? collected.structured : [])];
  for (const match of String(collected.head ?? "").matchAll(/<script\b[^>]*\btype\s*=\s*["']application\/ld\+json["'][^>]*>([\s\S]*?)<\/script\s*>/gi)) {
    blocks.push(match[1]);
  }
  const types = new Set();
  const add = (node) => {
    if (Array.isArray(node)) { node.forEach(add); return; }
    if (!node || typeof node !== "object") return;
    for (const type of [node["@type"]].flat()) if (typeof type === "string") types.add(type.replace(/^https?:\/\/schema\.org\//, ""));
    if (Array.isArray(node["@graph"])) node["@graph"].forEach(add);
  };
  for (const block of blocks.slice(0, 40)) {
    try { add(JSON.parse(block)); } catch { /* Malformed structured data says nothing. */ }
  }
  return types;
}

function openGraphType(head) {
  for (const [tag] of String(head ?? "").matchAll(/<meta\b[^>]*>/gi)) {
    if (/\bproperty\s*=\s*["']og:type["']/i.test(tag)) return (tag.match(/\bcontent\s*=\s*["']([^"']*)["']/i)?.[1] ?? "").trim().toLowerCase();
  }
  return "";
}

/**
 * Whether the open page is an ordinary written article whose words can be read on their
 * own: it says so in its structured data, is not a post, carries substantial text, shows
 * no video or canvas, and does not point to a picture for its claim. Such a page is not
 * screenshotted automatically when its words name no treatment. When unsure, false.
 *
 * @param {ReturnType<typeof collectFromPage>} collected
 * @param {{ text: string, platform?: string } | null} request what composeRequest made of it
 * @param {string} address the page's address
 * @param {{ readAddress: Function, media?: { kind: string }[] }} context the visible media
 */
export function readableArticle(collected, request, address, { readAddress, media = [] }) {
  if (!collected || !request || request.platform) return false;
  if (String(collected.selection ?? "").length >= CHOSEN_FROM) return false;
  try { if (readAddress(address).kind !== "article") return false; } catch { return false; }
  const types = structuredTypes(collected);
  const og = openGraphType(collected.head);
  if ([...types].some((type) => POST_TYPES.has(type)) || /^(?:video|music|profile)\b/.test(og)) return false;
  if (![...types].some((type) => ARTICLE_TYPES.has(type)) && og !== "article") return false;
  const text = String(request.text ?? "");
  if (text.length < READABLE_FROM || (text.match(/[\p{L}\p{N}]+/gu) ?? []).length < READABLE_WORDS) return false;
  if ((Array.isArray(media) ? media : []).some((one) => one?.kind !== "img")) return false;
  return !IMAGE_CLAIM.test(text);
}

/**
 * What a page's content fingerprint is taken over. An ordinary article is its words and
 * links only, so a decorative photo moving as the reader scrolls does not make the page
 * new. Other pages include the visible media, and a video page its words only.
 */
export function fingerprintInput(request, media, { videoOnly = false } = {}) {
  if (request.readableArticle) return { text: request.text, links: request.links, media: null, article: true };
  return { text: request.text, links: request.links, media: videoOnly ? null : media };
}
