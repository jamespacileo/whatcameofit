// Following a shortened link to the address it leads to, politely. A shortener is asked
// only if its own robots.txt allows it, and only for where the link points: the answer
// read is the redirect, never a page. Some shorteners refuse software (X's does); a link
// through one of those is left unfollowed.
import { readAddress } from "../src/lib/lookup-match.mjs";
import { allowedByRobots, client, isPublic } from "./article.mjs";

// A shortened link may lead to another one. This many steps are taken at most.
const MAX_STEPS = 4;

/**
 * @returns {Promise<string | null>} the first address on the way that is not itself a
 *   shortened link, or null when the link cannot be followed to one.
 */
export async function followShort(address, { fetch, contact }) {
  let current = address;
  for (let step = 0; step < MAX_STEPS; step += 1) {
    let url;
    try {
      url = new URL(current);
    } catch {
      return null;
    }
    if (!isPublic(url) || !(await allowedByRobots(url, { fetch, contact }))) return null;
    let response;
    try {
      response = await fetch(url.href, { headers: client(contact), redirect: "manual" });
    } catch {
      return null;
    }
    const next = response.status >= 300 && response.status < 400 ? response.headers.get("Location") : null;
    if (!next) return null;
    try {
      current = new URL(next, url).href;
    } catch {
      return null;
    }
    if (readAddress(current).kind !== "short") return current;
  }
  return null;
}
