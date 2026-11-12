// Learning where a shortened link in a post leads, in the reader's own browser.
//
// A post on X links out only through X's own shortener. Opened by a browser, that
// address answers with a small page that names the real one. The extension asks for
// that page, as a click on the link would, and reads the address from it; it does not
// go on to the article. It has permission for the shortener's host and no other.

// The shorteners that answer a browser with a page naming the address, and that the
// extension's manifest has permission for. Keep in step with build.mjs.
export const RESOLVABLE = ["t.co"];
// The most shortened links opened for one search.
const AT_MOST = 3;

function unescaped(address) {
  // Inside a script the address is written as a JavaScript string: "https:\/\/…".
  return address.replace(/\\\//g, "/").replace(/\\u([0-9a-f]{4})/gi, (_, code) => String.fromCharCode(parseInt(code, 16))).replace(/&amp;/g, "&");
}

/**
 * The address a shortener's page names, or null when it names none that can be used.
 * The page says it up to three ways; the first found is taken.
 */
export function addressIn(page, shortener) {
  const found =
    page.match(/http-equiv=["']?refresh["']?[^>]*content=["']\s*\d+\s*;\s*URL=([^"'>]+)/i)?.[1] ??
    page.match(/location\.replace\(\s*"((?:[^"\\]|\\.)+)"\s*\)/)?.[1] ??
    page.match(/<title>\s*(https?:\/\/[^<\s]+)\s*<\/title>/i)?.[1];
  if (!found) return null;
  try {
    const address = new URL(unescaped(found.trim()));
    if (!/^https?:$/.test(address.protocol)) return null;
    // An address on the shortener itself says nothing about where the link leads.
    return address.hostname.toLowerCase() === shortener ? null : address.href;
  } catch {
    return null;
  }
}

/**
 * The same links, with each resolvable shortened one replaced by the address it leads to.
 * A link that cannot be resolved is left as it was.
 * @param {string[]} links
 * @param {typeof fetch} get the browser's fetch
 */
export async function resolveShortLinks(links, get) {
  let opened = 0;
  const resolved = [];
  for (const link of links) {
    let host = "";
    try {
      host = new URL(link).hostname.toLowerCase();
    } catch {
      host = "";
    }
    if (!RESOLVABLE.includes(host) || opened >= AT_MOST) {
      resolved.push(link);
      continue;
    }
    opened += 1;
    try {
      // No cookies and no referrer: the shortener learns that the link was opened, not
      // by whom or from where.
      const response = await get(link, { redirect: "manual", credentials: "omit", referrerPolicy: "no-referrer" });
      const address = response.ok ? addressIn(await response.text(), host) : null;
      resolved.push(address ?? link);
    } catch {
      resolved.push(link);
    }
  }
  return [...new Set(resolved)];
}
