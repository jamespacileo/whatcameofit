# Proposal

## Why

A growth review on 2026-11-13 found that the site answers and shares well but has no loop that compounds: 58 of its 84 published claims were first reported in 2026 and have nothing to show yet, a lookup that finds no tracked claim is thrown away, nothing is counted, a status change is not an event anyone sees, and a reader on a phone or without the extension has no trigger. The operator chose to close all eight gaps and agreed on 2026-11-13 to count lookup misses.

## What Changes

- **Older headlines (gap 1).** A third candidate list of widely carried headlines first reported from 2010 to 2020 is gathered, imported as pending drafts and prepared the same way as the two existing backfills. Data only; no behaviour changes.
- **Missed lookups are counted (gap 2).** When the lookup service reads a public article that no published claim cites, it adds one to a count for that cleaned address and that day. Nothing about the reader is kept. The operator reads the counts as an intake list for new claims. Lookups of pasted text, of screenshots and of posts are not counted.
- **Pages are counted (gap 3).** The site's own service counts page views per page per day with the referring site, and downloads of card images and the data file, as `site-measurement` already allows. Declared crawlers are left out. The method page says what is counted.
- **A status change is an event (gap 4).** A claim whose status has changed gets a card that says what it was and what it is now, with the date. The site posts each status change and each day's anniversaries from its own Bluesky and Mastodon accounts, in the share sentence's wording, with a daily cap. Posting is off until an account is configured.
- **The extension can be installed from a store (gap 5).** The Chrome and Safari builds are packaged with their listings and privacy declarations for submission by the operator. Once a store address is configured, the site links to it.
- **A phone can share an article to the site (gap 6).** The site can be installed, and an installed copy appears in Android's share sheet: sharing an article to it opens the lookup with that address, which still never enters the page's address.
- **List pages have their own card (gap 7).** Year and topic pages get a link-preview card stating the page's title, how many claims it lists, how many have an approval on record and the month checked.
- **Smaller search items (gap 8).** Pages allow large image previews; the sitemap says when each claim page last changed; a claim's title in a browser tab and a search result ends with its status; each claim has its own data file and the site describes itself in `llms.txt`; each claim page offers a dated line to cite.

Not in this change: email alerts, web push, outlet pages, any game, popularity shown to readers, posting to X (its posting interface is paid), and IndexNow.

## Capabilities

### New Capabilities

- `lookup-demand`: what the site counts about lookups that found no tracked claim, how long it keeps it, and how the operator reads it.
- `site-announcements`: what the site posts from its own accounts on other networks, in what wording and how often.

### Modified Capabilities

- `site-measurement`: counts are made by the site's own service and leave out declared crawlers; counts are deleted after a set time.
- `sharing`: the change card; cards for year and topic pages; a line to cite.
- `site-publishing`: large previews, sitemap dates and status in the title; the site can be installed and shared to; the site links to the extension's store pages.
- `open-data`: a data file per claim; a plain description of the site and its data for software that reads sites.

## Impact

- **Worker** (`site/worker/`): counts on every page request and on a missed lookup, a `/share` address for the share sheet, and a daily scheduled run that posts and deletes old counts. New bindings in `site/wrangler.jsonc`: one D1 database, one cron trigger, and optional secrets for the two accounts.
- **Site** (`site/src/`): manifest, layout head, sitemap, claim title, new card routes, per-claim data route, `llms.txt`, cite line, extension links, method and privacy pages.
- **Extension** (`extension/`): store packages and listing material only; no behaviour change.
- **Data** (`data/seed/`): a new candidate CSV and its notes file.
- **Docs**: `docs/deploy.md` (database, cron, secrets), `docs/sources.md` (Bluesky and Mastodon posting terms and limits), `GLOSSARY.md` (missed lookup, announcement).
- **Conflict to settle in the same work:** the in-flight `live-lookup` change says "A lookup keeps nothing it read" and its service "keeps nothing". A count per address per day is a deliberate, operator-approved exception; that change's wording is amended to name it.
- **Depends on** `share-everywhere` (PR 28) for the layout's preview tags and the breadcrumb data; this change adds requirements beside it and modifies none of its text.
- **Operator steps that software cannot do:** store developer accounts and submissions, creating the two network accounts, and the review of backfilled claims.
