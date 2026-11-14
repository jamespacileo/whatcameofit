# Design

## Context

See `proposal.md` for motivation. What shapes the approach:

- The Worker (`site/worker/index.mjs`) already runs first for every address except `/_astro/*` and `/pagefind/*` (`run_worker_first` in `site/wrangler.jsonc`), so it sees every page and card request without any script in the page. It exports only `fetch`; it has no scheduled run and no database. Its one store is the KV namespace `LOOKUP_RESULTS`.
- A tracked article never reaches `/api/lookup`: the home page and the extension answer it from `lookup.json`. A request that reaches the service with an article address is therefore already a miss, except for a post that links to a tracked article, which the service detects itself.
- `sourceUrl` in `site/src/lib/source-url.mjs` already cleans an address and refuses one with unknown query parameters. It is the cleaning rule the `lookup-demand` spec refers to.
- `site-measurement` forbids any count finer than one day and any stored network address. Worker logging is off (`observability.enabled: false`).
- Status history is already in the export (`status.history`) and `site/src/lib/changes.ts` already words a change ("Was: … Now: …") under the neutral-wording check.
- The site owns all wording; the Worker holds none.
- `thenwhat extract new <url> --slug` already drafts a claim from an article address, and `thenwhat claim import-csv` imports candidate rows.

## Goals / Non-Goals

**Goals:**

- Each of the eight parts ships on its own, in its own pull request, and none blocks another except where noted in `tasks.md`.
- Counting can fail or be switched off without any reader noticing.
- No new party sees a reader: no third-party script, no third-party request at page load.

**Non-Goals:**

- A dashboard. The operator reads counts from a command.
- Turning a missed address into a claim automatically. Intake stays a list the operator acts on.
- Replies, reposts or any reading of the networks the site posts to.
- iOS share-sheet support; iOS offers no share target to installed sites. The Safari extension is the route there.

## Decisions

### 1. Counts live in one D1 database, written by upsert

Three tables, each keyed so that a row is a count and nothing else:

- `page_counts(day, path, referrer_host, n)`
- `download_counts(day, path, n)`
- `lookup_misses(day, address, n)`

Each write is `INSERT … ON CONFLICT DO UPDATE SET n = n + 1`, issued through `ctx.waitUntil` so the response never waits on it, inside a `try` that swallows failure.

- *Analytics Engine* was rejected: every data point carries a timestamp, which is finer than a day and so breaks `site-measurement`.
- *KV* was rejected: it has no atomic increment, so concurrent requests lose counts.
- *Cloudflare Web Analytics* was rejected: it is another party's script in the page.

Schema lives in `site/migrations/`; `make deploy` applies migrations before deploying.

### 2. What counts as a reader's page view

A `GET` whose `Sec-Fetch-Dest` is `document`, whose response is HTML with status 200, and whose `User-Agent` does not match a short list of declared crawlers and link-preview fetchers (kept in one file with a test). `Sec-Fetch-Dest` is sent by browsers and not by crawlers, so it does most of the work; the list catches headless browsers that declare themselves. Embed pages are counted under their own path, so embeds on other sites are visible as a number. `referrer_host` is the `Referer` header's host, or `direct`; a referrer on the site's own host is stored as `self`.

A download is a `GET` for a square, tall or change card, or for a data file, whose `Sec-Fetch-Dest` is not `image` (which excludes the card shown inline on the claim page) and which passes the same crawler check. The wide card is fetched by preview bots, not readers, and is not counted.

### 3. Where a miss is counted

In `handle`, after `readArticle` succeeds for `read.kind === "article"`, keyed by `sourceUrl(read.address)`; skipped when that returns null. The post path, pasted text, screenshots and `cacheOnly` requests never reach this line. A cached answer returned earlier in the function is still a miss and is counted before returning, so popular misses are not undercounted by the 24-hour cache.

The in-flight `live-lookup` requirement "A lookup keeps nothing it read" is amended in that change to add: "It MAY add to the count of missed lookups described in `lookup-demand`."

### 4. The operator reads counts with two make targets

- `make counts` prints page and download counts for a period.
- `make demand` writes `data/intake/missed-<date>.csv` (address, total, days), most asked first, and prints the top rows. `data/intake/` is ignored by git: the addresses are public but the list is the operator's.

Both run a small script that calls `wrangler d1 execute --remote --json`. No public or authenticated HTTP endpoint is added, so there is nothing to protect. The operator turns a row into a claim with `thenwhat extract new`.

### 5. One daily scheduled run does clean-up and posting

A cron trigger at 09:00 UTC calls a new `scheduled` export:

1. Delete `lookup_misses` older than 90 days and page and download counts older than 400 days.
2. Fetch `/announce.json` from the site's own assets.
3. Post what is due and not yet recorded in a fourth table, `announced(id, account)`.

`/announce.json` is written by the site build, so every word of a post is the site's and passes `assertNeutral` at build time. It holds status changes from the last seven days (id `change:<slug>:<on>`) and, for every claim more than a year old, its month and day with the share sentence (id `anniversary:<slug>:<year>`, the year filled in by the Worker). The Worker only filters by today's date, orders changes first, takes four, and posts. A row is written to `announced` before the network call's result is known to matter: a failed post is not retried, which the spec requires and which makes a double post impossible. A preview build writes an empty file.

- *Posting from CI after deploy* was rejected: anniversaries need a daily clock, not a deploy.
- *Posting from the pipeline* was rejected: it runs on the home network at irregular times and would need the accounts' credentials there.

### 6. Bluesky and Mastodon, by their plain posting interfaces

- Bluesky: create a session with an app password, upload the card as a blob, create a post with the text, a link facet and an external embed (title, description, thumbnail).
- Mastodon: `POST /api/v1/statuses` with an access token and an `Idempotency-Key` equal to the announcement id. The server draws the preview from the claim page's own tags.

Credentials are Worker secrets (`BLUESKY_HANDLE`, `BLUESKY_APP_PASSWORD`, `MASTODON_SERVER`, `MASTODON_TOKEN`); an account with any secret missing is not configured. Each network's current terms, automation rules and rate limits are read and written into `docs/sources.md` before its client is written. Tests use recorded responses; none posts.

### 7. Share target: a POST that leaves no address behind

The manifest gains `display: "standalone"` and a `share_target` with `action: "/share"`, `method: "POST"`, form encoding, and `title`, `text` and `url` fields. The Worker answers `POST /share` with a few lines of HTML that put the first web address found in `url` or `text` into `sessionStorage` and replace the location with `/`. The home page's script reads the key, removes it, fills the lookup box and runs the lookup as if pasted.

- *GET* was rejected: the shared address would be in the page's address, which `site-publishing` forbids.
- *A service worker* was rejected: it is a larger moving part than one Worker route, and installability no longer requires one in Chrome.

Android often puts the address in `text` with the article's title around it, so the route extracts the first `http(s)` address and ignores the rest.

### 8. Cards reuse the existing drawing code

`site/src/lib/card-image.ts` gains two content shapes drawn with its existing layouts and tokens:

- change card: `/og/changed/<slug>.png` (wide) and `/og/changed/square/<slug>.png`, built only for claims where `changesOf(claim)` has a second entry;
- list card: `/og/year/<year>.png` and `/og/topic/<slug>.png` (wide only), passed as `image` to the layout by those pages.

Their words come from `card.ts`, beside the status card's, and go through the same neutral check. "Was" and "Now" are set in the same weight and the site's blue; no arrow, no colour difference.

### 9. Claim titles drop the site's name to make room for the status

A claim's `<title>` becomes `<intervention> for <indication>: <status label>`, with the first part clipped at a word so the whole is at most 65 characters. The site's name is left off claim titles only: search engines show it from the `WebSite` data added by `share-everywhere`, and the status is worth more in that space. `og:title` stays the headline.

### 10. Small search items

- `max-image-preview:large` is a `robots` meta on every page of a non-preview build; a preview keeps `noindex` alone.
- Sitemap `<lastmod>` is the date part of `status.updated_at`, for claim pages only.
- Per-claim file: `/data/claims/<slug>.json`, the output of `openData` narrowed to one claim, linked with `rel="alternate" type="application/json"`. The export schema is unchanged.
- `llms.txt` is a static route built from `site.config.mjs`, the notices and the open-data constants.
- The cite line is built in `card.ts` beside the share sentence and uses the same copy control.

### 11. Extension stores

No code change. `make extension` already writes `extension/dist`; a new target zips it for the Chrome Web Store, and `extension/safari.sh` already produces the Safari project. Listing text, the permission justifications and the privacy declarations are written into `extension/store/` from the privacy page's wording. Store addresses reach the site as `CHROME_STORE_URL` and `SAFARI_STORE_URL`, read in `site.config.mjs` like `SUGGEST_URL`.

### 12. Backfill selection

`data/seed/claims-2010s.csv`, same columns as the existing lists, with a notes file. A row qualifies when the claim was first reported from 2010 to 2020 and was carried by at least two widely read outlets. Target: about 120 rows spread across the configured topics, weighted to those with few claims. Only titles, outlets, dates and addresses are recorded, never article text. Rows are imported as pending, prepared with `thenwhat prepare`, and decided by the existing rules; any decision made by the assistant is recorded `--as-assistant`.

## Risks / Trade-offs

- [A looked-up address could be one only its reader knows] → Only addresses the service fetched from the public web under robots rules are counted, in cleaned form, with unknown query parameters refused; nothing ties a count to a reader; rows are deleted after 90 days; the list is never published.
- [The crawler list goes stale and bots inflate counts] → `Sec-Fetch-Dest` is the main filter; the list is one tested file; counts are read as trends, and the method page says crawlers that do not declare themselves may be counted.
- [A D1 write on every page view adds cost or latency] → Writes run after the response; at this site's size they are far inside the free allowance; the binding can be removed and pages still serve.
- [A wrong status is announced before the operator archives the claim] → Same exposure as the page itself under `auto-publish`; the daily run gives up to a day to archive first, and a change older than seven days is never posted. The operator can delete a post by hand.
- [A burst of posts after a large backfill] → First statuses and old history are never posted; four posts a day at most.
- [A network changes its interface or automation rules] → Posting failure changes nothing on the site; terms are recorded in `docs/sources.md` with the date checked.
- [`display: standalone` hides the address bar in an installed copy] → Claim pages already carry Share and Copy link; verify on a phone that a reader can still get a page's address.
- [Claim titles in a search index go stale after a status change] → Same as the description today, which already leads with the status; the sitemap date tells crawlers when to return.
- [Store review rejects or delays the extension] → The site links only once an address is configured, so nothing waits on it.
- [This change is large] → Eight task groups, each its own pull request; the change is archived when all are merged or the remainder is split off.

## Migration Plan

1. Create the D1 database and apply migrations; deploy with counting on. Nothing reads the counts yet.
2. Ship the site-only groups (search items, cards, per-claim data, cite line) in any order.
3. Add the cron trigger with no account secrets: it only deletes old counts.
4. The operator creates the accounts and sets secrets; posting starts on the next daily run.
5. Rollback for any part: revert its pull request. Removing the D1 binding stops all counting and posting; pages, lookups and cards are unaffected. The database can be dropped; it holds nothing a page needs.

## Open Questions

- Which Mastodon server hosts the site's account, and the handles on both networks: the operator's choice at step 4.
- The hour of the daily run: 09:00 UTC unless the operator prefers another.
