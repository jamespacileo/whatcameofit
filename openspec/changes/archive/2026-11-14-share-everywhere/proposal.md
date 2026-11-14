# Proposal

## Why

On 2026-11-13 the operator asked for every search and link-preview element to be set correctly, and for sharing to be as complete as on sites that spread widely. An audit of the built site found the base in place (three card shapes, a sentence to copy, an embed, the device's share sheet, a sitemap, feeds), and these gaps:

- No `robots.txt`, so crawlers are not pointed at the sitemap.
- Link previews lack `og:url`, the image's size and type, `og:locale`, the X image alternative and the colour a browser tints its bar with. Every page claims to be an article, including the home and list pages.
- Only one of the two feeds is announced to feed readers.
- Structured data names the claim page only: no site, no publisher logo, no trail of pages, no description of the open data.
- On a computer there is no share sheet, so the Share button only copies the address. Readers there have no way to post straight to a network.
- Another site that turns pasted links into embeds (WordPress, Ghost, Notion and others read oEmbed) cannot find the embed.

Research on 2026-11-13 found no library worth adopting: the maintained SEO helpers only write the tags the layout already writes, and share-button widgets add third-party scripts, which the site's privacy promise and the embed's "loads nothing else" rule exclude. Prefilled post addresses are plain links. Google dropped fact-check rich results in June 2025, and fact-check markup states a verdict, so it stays out.

## What Changes

- `robots.txt` allows everything and names the sitemap. A preview build's `robots.txt` disallows everything.
- Every page states `og:url`, `og:locale` (`en_GB`), the image's width, height and type, the image alternative for X, and a theme colour. Home and list pages are `website`; claim pages are `article` with published and modified times.
- Both feeds are announced in every page's head.
- Structured data: the home page names the site and its publisher with a logo; claim, topic, source and year pages carry a breadcrumb trail; the claim page's data adds its description, image and the site it belongs to; the data page describes the open dataset and its licence.
- "Pass it on" offers prefilled posts to Bluesky, Mastodon, Threads, X, LinkedIn, Reddit, WhatsApp, Telegram and email, plus copying the address. Each is a plain link that works with no script, except Mastodon, which asks for the reader's server and remembers it in the reader's own browser. The post text is the share sentence, so it carries no verdict.
- Each claim has an oEmbed description of its embed, announced from the claim page, so sites that read oEmbed turn a pasted claim address into the embed.
- The privacy page says the Mastodon server is kept only in the reader's browser.

## Capabilities

### Modified Capabilities

- `sharing`: posting to a network; oEmbed discovery.
- `site-publishing`: link previews, `robots.txt`, feeds announced, structured data.

## Impact

- **Site:** `site/src/layouts/Base.astro`, `site/src/lib/structured.ts`, a new `site/src/lib/share-links.ts`, `site/src/pages/[slug].astro`, `site/src/pages/index.astro`, `site/src/pages/data.astro`, topic, source and year pages, new `robots.txt.ts` and `oembed/[slug].json.ts`, `privacy.astro`, `global.css`.
- **No new dependency.** No request to any other host is added: share links are followed only when a reader clicks one.
- **Wording risk:** prefilled post text is the existing share sentence, already held to the neutral-wording rule.
