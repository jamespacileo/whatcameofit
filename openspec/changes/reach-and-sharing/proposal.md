# Proposal

## Why

The site answers "what happened to that breakthrough?" well for a reader who is already on it, but gives that reader little to pass on and gives nobody else a reason to arrive. The operator asked on 2026-11-11 for the ways the site could spread to be written down and worked through in full, so that reach is designed with the same care as accuracy and none of it is left to chance.

## What Changes

- **Link-preview card, second version.** The card sets the outlet's own headline, in quotation marks with the outlet named, beside the status the records support, with the year first reported and the month the registries were last checked. It carries a short "not medical advice" line.
- **Card in three shapes.** Each claim gets the card as a wide image (link previews), a square one and a tall one (image-led networks), offered as downloads on the claim page.
- **A sentence to copy.** The claim page offers one plain sentence that states the claim's first report, its current status and the page's address, ready to paste.
- **Embed.** Each claim has a small page made to sit inside another site's frame, showing the status and linking back. The claim page gives the snippet.
- **Anniversaries.** A page and a feed list the claims whose first report has an anniversary, so there is something true and new to post every day without writing anything.
- **Suggest a headline, report an error.** Every page links to a way of telling the operator about a headline to track or a mistake to fix. The site itself collects nothing.
- **How it works.** One page explains how a status is derived, what the site never says, and where the data comes from.
- **A year at a time.** A page per year lists every tracked claim first reported in it, with where each stands now.
- **Findable.** Pages carry a canonical address and plain structured data, and the site publishes a sitemap. No fact-check or review markup is used, because it would state a verdict.
- **Open data.** The published claims are offered as a downloadable file under the data licence already in the repository.
- **Measuring without watching people.** A written rule for what may be counted (pages, referrers, downloads) and what may not (anything tied to a person), and the launch checklist that depends on it.

Deliberately left out, with reasons in `design.md`: automated reply accounts, tables that rank outlets, and following a claim by email (Phase 2, when subscriber emails are first collected).

**Depends on, but does not include:** a public deployment with a final address, the review of the pending claims, and the browser extension's store release (tracked in `browser-extension`). Nothing here spreads until those exist.

## Capabilities

### New Capabilities

- `sharing`: what a reader can take away from a claim page and what another site can show of it: the link-preview card in its shapes, the sentence to copy, and the embed.
- `anniversaries`: the dated list and feed of first-report anniversaries.
- `reader-contact`: how a reader suggests a headline or reports an error, and what the site does and does not collect when they do.
- `open-data`: the downloadable file of published claims and its licence.
- `site-measurement`: what the public site may count about its use, and what it may never record.

### Modified Capabilities

- `site-publishing`: adds the page that explains the method, the page per year, and the canonical address, structured data and sitemap every page carries.

## Impact

- **Site:** `site/src/pages/og/[slug].png.ts` (card), `site/src/lib/card.ts`, `site/src/pages/[slug].astro` (downloads, sentence, snippet), new pages for the embed, anniversaries, the method and each year, `site/src/layouts/Base.astro` (canonical, structured data, contact links), `site/site.config.mjs` (public address, contact addresses), `site/tests/site.test.mjs`.
- **Pipeline and export:** no change to the export's shape. The open-data file is written by the site from the export it already reads.
- **Browser extension:** none. Its lookup file is unchanged.
- **Docs:** `DESIGN.md` (card shapes, embed, new pages), `PRODUCT.md` (the "Not yet" list shrinks), a new `docs/launch.md`.
- **Dependencies:** none new. The card shapes use the image renderer already installed.
- **Personal data:** none collected by the site. A reader who writes to the operator does so through their own mail or the public issue tracker; the guardrail that subscriber emails are the only personal data, and none before Phase 2, is kept.
- **Risk that grows with reach:** a wrong status, a card read as a verdict, or "Phase 1" read as "available" travels further than a page does. Each is addressed by a requirement in `sharing` and a decision in `design.md`.
