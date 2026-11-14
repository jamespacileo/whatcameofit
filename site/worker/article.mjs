// Getting a news article, politely: its text and what its page says of itself. Both are
// returned to the caller and kept nowhere. The same manners as the pipeline's
// thenwhat.extract.retrieve: robots.txt is obeyed, and when its rules cannot be read the
// article is not fetched.

import { withDeadline } from "./deadline.mjs";
import { pageAsText, readPage } from "./page.mjs";

const ROBOTS_NAME = "thenwhat";
const VERSION = "1";
export const MAX_TEXT_CHARACTERS = 20_000;
// The whole of one reading, robots.txt and the article's headers and body together.
export const ARTICLE_TIMEOUT_MS = 10_000;
const NOT_PUBLIC = /^(localhost|.+\.localhost|.+\.local|.+\.internal|.+\.test|\d{1,3}(\.\d{1,3}){3}|\[.*\])$/i;

/** Whether robots.txt lets this client fetch the path: the longest matching rule decides. */
function allowedBy(robots, path) {
  const groups = [];
  let current = null;
  let lastWasAgent = false;
  for (const line of robots.split(/\r?\n/)) {
    const [field, ...rest] = line.replace(/#.*/, "").split(":");
    const value = rest.join(":").trim();
    const name = field.trim().toLowerCase();
    if (name === "user-agent") {
      if (!lastWasAgent) groups.push((current = { agents: [], rules: [] }));
      current.agents.push(value.toLowerCase());
      lastWasAgent = true;
    } else if ((name === "allow" || name === "disallow") && current) {
      if (value) current.rules.push({ allow: name === "allow", path: value });
      lastWasAgent = false;
    }
  }
  const mine =
    groups.find((group) => group.agents.some((agent) => agent !== "*" && ROBOTS_NAME.includes(agent))) ??
    groups.find((group) => group.agents.includes("*"));
  if (!mine) return true;
  const matches = (rule) => {
    const pattern = rule.path.replace(/[.+?^${}()|[\]\\]/g, "\\$&").replace(/\*/g, ".*").replace(/\\\$$/, "$");
    return new RegExp(`^${pattern}`).test(path);
  };
  const deciding = mine.rules
    .filter(matches)
    .sort((a, b) => b.path.length - a.path.length || Number(b.allow) - Number(a.allow))[0];
  return deciding ? deciding.allow : true;
}

/** How this client names itself to every site it reads. */
export function client(contact) {
  return { "User-Agent": `${ROBOTS_NAME}/${VERSION} (mailto:${contact})` };
}

/** Whether the address is a public web address, not one on a local or private network. */
export function isPublic(url) {
  return /^https?:$/.test(url.protocol) && !NOT_PUBLIC.test(url.hostname);
}

/**
 * Whether the site's robots.txt lets this client fetch the address. Rules that cannot be
 * read in time, or that are themselves refused, mean no. `signal` is the caller's own
 * deadline, when it has one.
 */
export async function allowedByRobots(url, { fetch, contact, signal, timeoutMs = ARTICLE_TIMEOUT_MS }) {
  try {
    return await withDeadline(timeoutMs, async (bounded) => {
      const robots = await fetch(`${url.origin}/robots.txt`, { headers: client(contact), redirect: "follow", signal: bounded });
      if (robots.status >= 500 || robots.status === 401 || robots.status === 403) return false;
      return robots.status !== 200 || allowedBy(await robots.text(), url.pathname + url.search);
    }, { label: "robots", parent: signal });
  } catch {
    return false;
  }
}

/**
 * @param {{ fetch: Function, contact: string, timeoutMs?: number }} given `timeoutMs` bounds
 *   the whole reading; past it the article is refused as unreadable.
 * @returns {Promise<{ text: string, page: object } | { refused: "address" | "robots" | "unreadable" }>}
 *   `text` opens with the page's headline, summary and date; `page` is worker/page.mjs's reading.
 */
export async function readArticle(address, { fetch, contact, timeoutMs = ARTICLE_TIMEOUT_MS }) {
  let url;
  try {
    url = new URL(address);
  } catch {
    return { refused: "address" };
  }
  if (!isPublic(url)) return { refused: "address" };

  try {
    return await withDeadline(timeoutMs, async (signal) => {
      if (!(await allowedByRobots(url, { fetch, contact, signal, timeoutMs }))) {
        return signal.aborted ? { refused: "unreadable" } : { refused: "robots" };
      }
      let page;
      try {
        page = await fetch(url.href, { headers: client(contact), redirect: "follow", signal });
      } catch {
        return { refused: "unreadable" };
      }
      if (!page || page.status !== 200) return { refused: "unreadable" };
      const read = readPage(await page.text());
      const text = pageAsText(read).slice(0, MAX_TEXT_CHARACTERS);
      return text ? { text, page: read } : { refused: "unreadable" };
    }, { label: "article" });
  } catch {
    // Out of time, or a body that could not be read: the article is not read.
    return { refused: "unreadable" };
  }
}
