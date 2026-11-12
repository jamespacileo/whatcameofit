// Getting a news article, politely: its text and what its page says of itself. Both are
// returned to the caller and kept nowhere. The same manners as the pipeline's
// thenwhat.extract.retrieve: robots.txt is obeyed, and when its rules cannot be read the
// article is not fetched.

import { pageAsText, readPage } from "./page.mjs";

const ROBOTS_NAME = "thenwhat";
const VERSION = "1";
export const MAX_TEXT_CHARACTERS = 20_000;
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

/**
 * @returns {Promise<{ text: string, page: object } | { refused: "address" | "robots" | "unreadable" }>}
 *   `text` opens with the page's headline, summary and date; `page` is worker/page.mjs's reading.
 */
export async function readArticle(address, { fetch, contact }) {
  let url;
  try {
    url = new URL(address);
  } catch {
    return { refused: "address" };
  }
  if (!/^https?:$/.test(url.protocol) || NOT_PUBLIC.test(url.hostname)) return { refused: "address" };

  const headers = { "User-Agent": `${ROBOTS_NAME}/${VERSION} (mailto:${contact})` };
  const get = async (target) => {
    try {
      return await fetch(target, { headers, redirect: "follow" });
    } catch {
      return null;
    }
  };

  const robots = await get(`${url.origin}/robots.txt`);
  // Rules that cannot be read, or that are themselves refused, mean: do not fetch.
  if (!robots || robots.status >= 500 || robots.status === 401 || robots.status === 403) {
    return { refused: "robots" };
  }
  if (robots.status === 200 && !allowedBy(await robots.text(), url.pathname + url.search)) {
    return { refused: "robots" };
  }

  const page = await get(url.href);
  if (!page || page.status !== 200) return { refused: "unreadable" };
  const read = readPage(await page.text());
  const text = pageAsText(read).slice(0, MAX_TEXT_CHARACTERS);
  return text ? { text, page: read } : { refused: "unreadable" };
}
