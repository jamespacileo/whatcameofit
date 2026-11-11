// Links a reader follows to write to the operator: to suggest a headline, or to report
// an error on a claim page. Plain JavaScript, pure: shared by the pages and the
// lookup's script in the browser. The site never sends what a link carries; the
// reader's own mail or the issue form they open does, if they choose to send it.

export const SUGGEST_SUBJECT = "A headline to track";
export const CORRECTION_SUBJECT = "Something wrong on a page";

/**
 * The link to a configured contact address, carrying a value forward: an article's
 * address, or a claim page's. A mail address gets the value as the message body under
 * a short subject; an issue form gets it as the query value `about`. With no value,
 * the link leads to the address alone (with the subject, for mail).
 *
 * Returns null when no address is configured. `opens` names what the link opens, so
 * the page can say so beside it.
 *
 * @param {string | null | undefined} address  a `mailto:` address or an http(s) form address
 * @param {string} [about]  the value to carry forward
 * @param {string} [subject]  the subject of a message, for a mail address
 * @returns {{ href: string, opens: "your mail" | "an issue form" } | null}
 */
export function contactLink(address, about = "", subject = SUGGEST_SUBJECT) {
  if (!address) return null;
  if (/^mailto:\S+$/i.test(address)) {
    const fields = [];
    if (!/[?&]subject=/i.test(address)) fields.push(`subject=${encodeURIComponent(subject)}`);
    if (about) fields.push(`body=${encodeURIComponent(about)}`);
    const joiner = address.includes("?") ? "&" : "?";
    return {
      href: fields.length > 0 ? `${address}${joiner}${fields.join("&")}` : address,
      opens: "your mail",
    };
  }
  if (/^https?:\/\//i.test(address)) {
    const url = new URL(address);
    if (about) url.searchParams.set("about", about);
    return { href: url.href, opens: "an issue form" };
  }
  throw new Error(
    `A contact address must be a mailto: address or the http(s) address of a public issue form, not "${address}". Set it in site/site.config.mjs.`,
  );
}
