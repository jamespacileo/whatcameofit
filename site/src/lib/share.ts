// What leaves the site when a reader passes a claim on: the embed snippet and the
// addresses that open a prefilled post on each network. Every post carries the share
// sentence and the page's address and nothing else: no tracking parameters, no wording
// of our own. Pure: the links are plain addresses, followed only when a reader clicks.
import { clip } from "./card.ts";

/** The embed's frame, as the snippet and the oEmbed description both give it. */
export const EMBED_SIZE = { width: 440, height: 420 };

/** The whole of what another site needs to show a claim's status. */
export function embedSnippet(siteUrl: string, slug: string, headline: string): string {
  const title = headline.replaceAll("&", "&amp;").replaceAll('"', "&quot;");
  return `<iframe src="${siteUrl}/embed/${slug}" title="${title}" width="${EMBED_SIZE.width}" height="${EMBED_SIZE.height}" style="border:0;max-width:100%" loading="lazy"></iframe>`;
}

export interface ShareLink {
  /** A short name for the network, used as the link's data attribute. */
  network: string;
  label: string;
  href: string;
}

// Bluesky counts a post's length in graphemes and stops at 300.
const BLUESKY_LIMIT = 300;

/**
 * Prefilled posts for one claim. `text` is the share sentence without the address;
 * `url` is the page's address; `title` is the claim's headline, for the networks that
 * take a title of their own. Mastodon has no one address, so it is not here: the page
 * asks the reader for their server (see mastodonShare).
 */
export function shareLinks(text: string, url: string, title: string): ShareLink[] {
  const q = (params: Record<string, string>) => new URLSearchParams(params).toString();
  const whole = `${text} ${url}`;
  const bluesky = `${clip(text, BLUESKY_LIMIT - url.length - 1)} ${url}`;
  return [
    { network: "bluesky", label: "Bluesky", href: `https://bsky.app/intent/compose?${q({ text: bluesky })}` },
    { network: "threads", label: "Threads", href: `https://www.threads.com/intent/post?${q({ text, url })}` },
    { network: "x", label: "X", href: `https://x.com/intent/tweet?${q({ text, url })}` },
    {
      network: "linkedin",
      label: "LinkedIn",
      href: `https://www.linkedin.com/sharing/share-offsite/?${q({ url })}`,
    },
    { network: "reddit", label: "Reddit", href: `https://www.reddit.com/submit?${q({ url, title })}` },
    { network: "whatsapp", label: "WhatsApp", href: `https://wa.me/?${q({ text: whole })}` },
    { network: "telegram", label: "Telegram", href: `https://t.me/share/url?${q({ url, text })}` },
    {
      network: "email",
      label: "Email",
      // mailto takes percent-encoding, not form encoding: a "+" would stay a plus sign.
      href: `mailto:?subject=${encodeURIComponent(title)}&body=${encodeURIComponent(whole)}`,
    },
  ];
}

/**
 * A Mastodon server's share page, or null when what the reader typed is not a server's
 * name. Accepts "mastodon.social", "https://mastodon.social/" or "@me@mastodon.social".
 */
export function mastodonShare(server: string, text: string, url: string): string | null {
  const host = server
    .trim()
    .replace(/^@?[^@\s/]+@/, "")
    .replace(/^https?:\/\//i, "")
    .replace(/\/.*$/, "")
    .toLowerCase();
  if (!/^[a-z0-9-]+(\.[a-z0-9-]+)+(:\d+)?$/.test(host)) return null;
  return `https://${host}/share?${new URLSearchParams({ text: `${text} ${url}` })}`;
}

/** "November 2026": the month a date falls in, in full, for a sentence a reader passes on. */
export function checkedMonth(isoDate: string): string {
  return new Date(`${isoDate.slice(0, 7)}-01T00:00:00Z`).toLocaleDateString("en-GB", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

/**
 * What "Copy sentence" copies on a topic page: where the topic's claims stand, the
 * month the registries were checked, and the page's address. Dated, so it stays true.
 */
export function topicSentence(summary: string, lastCheckedAt: string | null, address: string): string {
  const checked = lastCheckedAt ? ` Checked ${checkedMonth(lastCheckedAt)}.` : "";
  return `${summary}${checked} ${address}`;
}
