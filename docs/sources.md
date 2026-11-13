# Data sources

Terms, authentication and rate limits for each external source. Check an entry again before changing its client, and update the date.

"Observed" means seen in live responses on the date checked, not stated in documentation.

## ClinicalTrials.gov API v2

- **Checked:** 2026-11-11
- **Terms:** <https://clinicaltrials.gov/about-site/terms-conditions> (last updated 31 January 2023)
- **API:** <https://clinicaltrials.gov/data-api/api>
- **Authentication:** none. Requests without a key succeed (observed).
- **Rate limit:** not stated on the pages read. The client defaults to 2 requests per second, below the roughly 3 per second in `SPEC.md`.
- **Terms that bind the site:** attribute the data to ClinicalTrials.gov; keep it current; clearly display the date the data were processed by ClinicalTrials.gov; state any modifications; do not claim proprietary rights or present it as anything other than a United States Government database; do not use email addresses from it for promotion.
- **Behavior (observed):** an unknown but well-formed identifier returns 404; a malformed one returns 400, so the client checks the format first. Searches page with `nextPageToken`; the last page has no token and may be empty. Dates can be `YYYY-MM-DD` or `YYYY-MM`, each with a type of `ACTUAL` or `ESTIMATED`.
- **Search within a condition (observed 2026-11-11):** `countTotal=true` adds `totalCount` to the first page. `query.cond` narrows a search by condition and accepts `OR` between words. A condition worded the registry's way narrows well ("CAR-T cell therapy" has 2,071 trials, 2 with `query.cond=Stiff person syndrome`). A lay or long wording can return nothing ("Vitamin C" with "Pre-leukaemia blood disorders (CCUS and low-risk MDS)": 0; with "myelodysplastic syndrome": 16). The client therefore narrows only names with more than 100 trials, and tries the condition as worded and then its telling words joined with `OR`. A name that still has more than 100 trials within the condition, or none, contributes no candidates: the first live run met "the drug" recorded as another name for a treatment.

- **Search by a trial's name (observed 2026-11-12):** `query.titles="SURMOUNT-5"` searches titles and acronyms and returned that one trial. The lookup asks for at most 20 and treats a name that more trials carry as identifying none. The search fields now also ask for `Acronym`, `EnrollmentCount` and `CollaboratorName`, which the lookup compares with what an article says of its trial.

## Europe PMC RESTful web service

- **Checked:** 2026-11-11
- **Terms:** <https://europepmc.org/Copyright>
- **API:** <https://europepmc.org/RestfulWebService>
- **Authentication:** none (observed).
- **Rate limit:** not found on the pages read. The client defaults to 2 requests per second.
- **Terms that bind the site:** almost all material is copyright of publishers or authors, including abstracts. Crawling the website to download batches of articles is prohibited. The pipeline uses the web service only, stores abstracts in raw payloads for matching, and never publishes them. The site shows a paper's title and a link.
- **Behavior (observed):** a DOI is looked up with `query=DOI:"…"`; an unknown DOI returns `hitCount` 0, not an error. Citing papers come from `query=CITES:<id>_<source>` with `resultType=core` and are paged with `cursorMark`.

- **A paper's own trial (observed 2026-11-12):** a PubMed number is looked up with `query=EXT_ID:<number> AND SRC:MED`. The core record of a trial's report carries its ClinicalTrials.gov number in `abstractText` ("ClinicalTrials.gov number, NCT…"); `dbCrossReferenceList` was empty for the paper tried. The lookup reads the number from the abstract, shows no part of the abstract, and treats a paper that gives more than three numbers as a review. The Worker asks the same question from Cloudflare with the same contact address, and keeps no answer.

## Crossref REST API

- **Checked:** 2026-11-11
- **Documentation:** <https://www.crossref.org/documentation/retrieve-metadata/rest-api/> and its "Tips and tricks" page
- **Authentication:** none; no sign-up is required.
- **Etiquette:** identify the client with a contact address (the `mailto` of the "polite pool"). The client sends it in the User-Agent. Cache results and back off on 429.
- **Rate limit:** response headers showed 5 requests per second for the public pool (observed). The client defaults to 2 per second.
- **Terms that bind the site:** almost none of the metadata is subject to copyright and it may be used for any purpose; some abstracts may be copyrighted, so they are not published.
- **Behavior (observed):** an unknown DOI returns 404. Retraction and correction notices, including Retraction Watch data, arrive on the work itself under `updated-by`, each with a type, a date and the notice's own DOI.

## Internet Archive Wayback availability API

- **Checked:** 2026-11-11
- **Documentation:** <https://archive.org/help/wayback_api.php>
- **Authentication:** none.
- **Rate limit:** not stated. Used at most once per article that cannot be retrieved.
- **Behavior (documented):** `GET https://archive.org/wayback/available?url=…` returns the closest snapshot under `archived_snapshots.closest` with `available`, `url`, `timestamp` and `status`, or an empty `archived_snapshots` when there is none.

## Outlet sites (icons)

- **Checked:** 2026-11-11
- **What is read:** per outlet domain, `robots.txt`, then `/favicon.ico`, and when that is not an image the home page and at most two icons it names with `<link rel="icon">` or `apple-touch-icon`. Another host an icon lives on has its own robots.txt read first. The home page is read to find the icon's address and is kept nowhere.
- **Authentication:** none.
- **Terms:** each outlet has its own and they are not read one by one. The rule applied to all: robots.txt decides. A host whose rules refuse the client, or cannot be read, is sent nothing more.
- **Rate limit:** none published for this. The client sends one request per second at most and asks each domain once; `thenwhat icons --retry-missing` asks again only the domains that had no usable icon.
- **What is kept:** one raster image (PNG, ICO, GIF, JPEG or WebP, told from its bytes) of at most 100,000 bytes, with its address and fetch time. SVG is not kept: it can carry script and the site would serve it from its own address.
- **Terms that bind the site:** the icons are the outlets' own marks. The site shows one only beside the outlet's name and a link to its article, to say where a report came from. Remove an outlet's row from `outlet_icon` if it asks.
- **Behavior (observed):** kyoto-u.ac.jp has no `/favicon.ico`; its home page names a 32-pixel ICO, which is the icon in the seed file. That one fetch was made with a generic client name.
- **Safari asset audit (2026-11-13):** Dental Tribune's global and Indian editions now use its [declared DT mark](https://www.dental-tribune.com/wp-content/themes/dt/images/favicon/favicon-96x96.png), replacing a generic WordPress icon. USC Dentistry's [crest](https://dentistry.usc.edu/wp-content/uploads/2019/11/cropped-fevicon-180x180.png) is on the university's cardinal background for contrast; [ZME Science](https://cdn.zmescience.com/wp-content/uploads/2021/08/cropped-logo-zmescience-180x180.png) uses its current black mark. Griffith's [declared icon](https://cdn-ildedah.nitrocdn.com/nYYorQKadnvAORgWEyKkpWpwPIyqNOMp/assets/images/source/rev-14be058/news.griffith.edu.au/wp-content/uploads/2024/05/griffith-favicon.svg) was inspected and rasterised, so no SVG document is served. These replacements are bounded to 96 pixels and stored in the operator database as well as the public snapshot. Courthouse News's generic WordPress image was cleared; it uses the letter fallback. Hosts that block icon retrieval remain on letter fallbacks.

## UKCRC Health Research Classification System (HRCS)

Not an API. A fixed list of 21 health categories, used to check that the site's groups cover every area of health.

- **Checked:** 2026-11-12
- **Terms:** <https://hrcsonline.net/getting-started/conditions-of-use/>. All content on the site is licensed CC BY-NC-ND 2.0 England & Wales. The system may be used and distributed, but not altered or used for commercial benefit.
- **Categories:** <https://hrcsonline.net/health-categories/>
- **How it is used:** the category names sit, unaltered and with attribution, in `pipeline/src/thenwhat/claims/verticals.py` as anchors for each group. A configuration check reads them. Neither the export nor the site carries HRCS codes or names, and the groups' titles are our own wording, not an adaptation of HRCS.
- **What would change this:** any commercial use of the project. The non-commercial term then needs checking again with UKCRC before the anchors are kept.

## Not yet checked

ISRCTN, EU CTIS, WHO ICTRP, PubMed E-utilities, OpenAlex, NIH RePORTER, UKRI Gateway to Research, Companies House, SEC EDGAR, openFDA, EMA and MHRA have no client. Add an entry here before writing one.


## OpenAI Decisions API

- **Checked:** 2026-11-12
- **Guide:** <https://developers.openai.com/api/docs/guides/decisions>. **Reference:** <https://developers.openai.com/api/reference/resources/decisions/methods/create>
- **What it is:** `POST /v1/decisions` takes shared evidence (`input`) and 1 to 400 questions, and returns typed answers without writing text. The guide says it answers about ten times faster than the Responses API. A `choice` question takes 2 to 255 options, each a value and a description, and returns the chosen value, a probability for every option and a separate `confidence`.
- **Authentication:** the same key as other OpenAI calls (`OPENAI_API_KEY`).
- **Model:** one model is supported at the date checked; its name comes from `DECISIONS_MODEL`, or from `LLM_MODEL` when that names an OpenAI model. No model is named in code.
- **Price:** input tokens only, 0.10 US dollars per million at the date checked; output is not charged. Set it in `DECISIONS_INPUT_USD_PER_MTOK`; the pipeline refuses to call without it.
- **Data:** the guide says Zero Data Retention is available to eligible customers. What a lookup sends is the same as before: the reading of the article in one line and registry records, never the article's text.
- **Behavior (observed 2026-11-12):** three made-up trial records as three `choice` questions were answered in 1.96 seconds using 709 input tokens: the right option for each, probabilities summing to 1. A question the model declines comes back as `{"type": "refusal"}`; the pipeline treats it as no answer.
- **How the pipeline uses it:** as the decision backend `openai-decisions` (`DECISION_BACKEND`), for scoring candidate records and any other bounded choice. The probabilities are the model's own estimate and are not calibrated, like the other backend's.

## Social media posts

A reader may give the address of a post in place of an article's. A post is read only on a platform that offers posts to software without signing in, and only that one post, once, when a reader asks. The text is shown to the model and dropped; who wrote the post is never read out. Code: `site/worker/post.mjs`, `thenwhat.extract.post`.

### Bluesky public API

- **Checked:** 2026-11-12
- **Documentation:** <https://docs.bsky.app/docs/advanced-guides/rate-limits>, read from its source at <https://github.com/bluesky-social/bsky-docs>
- **Authentication:** none. The documentation says the hosts `api.bsky.app` and `public.api.bsky.app` "do not support authentication", that the second is cached, and that developers are asked to use it for "public web" use.
- **Rate limit:** by network address; the page read gives no number for this host. Responses carry rate-limit headers, and a 429 means stop. The lookup sends one request per post.
- **Behavior (observed):** `GET public.api.bsky.app/xrpc/app.bsky.feed.getPostThread?uri=at://<handle>/app.bsky.feed.post/<id>&depth=0&parentHeight=0` returns the post with the handle as written, no separate step to resolve it. The text is in `thread.post.record.text`, links in `record.facets[].features[].uri`, and the link card (address, title, description) in `thread.post.embed.external`. An unknown post answers 400.

### Hacker News API

- **Checked:** 2026-11-12
- **Documentation:** <https://github.com/HackerNews/API>
- **Authentication:** none. **Rate limit:** the documentation says "There is currently no rate limit." The lookup sends one request per item.
- **Behavior (observed):** `GET hacker-news.firebaseio.com/v0/item/<id>.json` returns a story with `title` and `url`, or a comment with `text` as HTML. An unknown item answers 200 with `null`. A removed item carries `deleted` or `dead`.

### Mastodon servers

- **Checked:** 2026-11-12
- **Documentation:** <https://docs.joinmastodon.org/methods/statuses/>, which marks `GET /api/v1/statuses/:id` as "Public for public statuses".
- **Terms:** each server has its own and they are not read one by one. The rule applied to all, as for outlets: the server's robots.txt decides, a server that refuses or whose rules cannot be read is sent nothing more, and only a post whose `visibility` is `public` is used. A server can also turn this interface off; then the post is refused like any unreadable one.
- **Which addresses:** any host with a path shaped `/@name/<digits>` or `/users/name/statuses/<digits>`. A local or private address is never asked.
- **Behavior (observed on one server):** the post's text is HTML in `content`; links to tags and people carry the class `mention` or `hashtag`; the link card is in `card` (`url`, `title`, `description`).

### Platforms whose posts are not read

Checked 2026-11-12 by reading each platform's own terms and documentation. No platform was asked for a post. The three robots.txt lines given below were read again directly; the rest is one reading of long legal pages, so re-read the page linked before acting on any line here.

| Platform | Finding | What decides it | What would change it |
| --- | --- | --- | --- |
| X | Not read | Its embed interface (`publish.x.com/oembed`) needs no sign-in and returns the post's text, but its robots.txt says `Disallow: /oembed`, and the Developer Agreement (updated 27 April 2026) licenses analysis only "as explicitly approved by X". The Terms of Service (effective 9 October 2026) forbid scraping without written consent. | A developer account and the X API's post lookup, paid per post read ($0.005 at the date checked). The operator's step. |
| Reddit | Not read | robots.txt is `Disallow: /` for every client. The Data API Terms (revised 20 July 2026) allow access only with the credentials Reddit issues. Its embed interface is licensed for embedding only. | A registered app with Reddit's approval. Whether a free one covers this use, and its rate limit, could not be confirmed: the help pages sit behind a bot check. The operator's step. |
| Facebook, Instagram, Threads | Not read | Their embed interfaces need no token since 15 June 2026, but their documentation forbids any use other than showing the embed, "extracting" content included, and they return no text or links. | Nothing found. |
| LinkedIn | Not read | The User Agreement (effective 3 November 2025) forbids automated access; robots.txt allows named search engines only. | Nothing found. |
| Telegram | Not read | Its content-licensing terms forbid access to user content other than as a user, and its use with AI models. No robots.txt exists (404). | Nothing found. |
| TikTok | Not read | The documented embed answer carries no caption, title or links, so there is nothing to read; the terms forbid automated extraction. | Nothing useful to gain. |
| YouTube | Not fetched by the service | A video URL alone is not used to fetch video, description or captions. The extension can read the current video's loaded page content when opened. | A separate authorised API client would need its own terms, permissions and quota review. |

Pages read: for X, `docs.x.com/x-for-websites/oembed-api`, `docs.x.com/developer-terms/agreement`, `x.com/en/tos`; for Reddit, `redditinc.com/policies/data-api-terms`, `/developer-terms`, `/embeds-terms`, `/user-agreement`; for Meta, `developers.facebook.com/docs/graph-api/reference/instagram-oembed`, `/documentation/threads/reference/oembed`, `/blog/post/2026/06/15/tokenless-access-to-meta-oembed-apis`; for LinkedIn, `linkedin.com/legal/user-agreement`, `/legal/crawling-terms`; for Telegram, `telegram.org/tos/content-licensing`; for TikTok, `developers.tiktok.com/doc/embed-videos` and its terms of service; for YouTube, `developers.google.com/youtube/terms/developer-policies`, `/youtube/v3/docs/videos/list`.

For every platform in this table the site names the platform, asks nothing of it, and offers to take the post's text or the article's address.

### YouTube in the reader's browser

- **Checked:** 2026-11-13. [YouTube transcript help](https://support.google.com/youtube/answer/15930243?co=GENIE.Platform%3DDesktop&hl=en) explains that videos with captions offer **Show transcript** from the description. [Captions download API](https://developers.google.com/youtube/v3/docs/captions/download) requires OAuth and permission to edit the video; it is not a general transcript service for arbitrary videos.
- **Implementation:** no new network client, API credentials or caption endpoint. On popup opening, the extension reads the current video's title, loaded description and captions/transcript from the DOM. It does not open the transcript automatically, access hidden player state, capture audio or download media. It can send one cropped visible frame under the existing capture guards and spending controls. No extra host permissions.
- **Reuse:** watch, share, Shorts and live URLs identify the same video. Playback, playlist and sharing parameters are dropped from the source URL; unknown parameters disqualify that URL. Browser-only answers remain private to that reader's local result cache; they do not establish independently public evidence for a shared result.
- **Verification:** live Chrome DOM inspection on this date confirmed the watch renderer's `video-id`, title/description/player selectors, current `transcript-segment-view-model [role="text"]` segments after opening Show transcript, and current Shorts' player-title permalink plus `h1` title. Shorts navigation briefly exposed a new renderer before the URL updated; identity matching rejects that intermediate state. Synthetic fixtures cover these layouts, recommendation/ad/overlay rejection and navigation. Installed-extension end-to-end acceptance in Safari/Chrome remains a release check in `extension/agent-test-brief.md`.

### Link shorteners

- **Checked:** 2026-11-12, by reading each one's robots.txt.
- **Followed by the service:** a shortened link in a post, when the shortener's robots.txt allows it. `bit.ly`, `trib.al`, `tinyurl.com` and `buff.ly` allowed everything on that date; `redd.it` too. Only the redirect is read (`site/worker/short.mjs`), four steps at most, three links per post.
- **Not followed by the service:** `t.co`, X's shortener, whose robots.txt says `Disallow: /` to every client but named search engines.
- **Opened by the reader's browser instead:** the extension asks `t.co` for the link's page, as a click would, without cookies or a referrer, and reads the address the page names (observed: a 200 page that gives the address in a refresh tag, in its title and in a script). It does not go on to the article. One request per link, three links at most per search (`extension/src/short-links.js`).


## OpenAlex literature search

- **Checked:** 2026-11-13. [Authentication](https://help.openalex.org/api/authentication/), [pricing](https://help.openalex.org/access/pricing/), [licensing](https://help.openalex.org/hc/en-us/articles/24397285563671-OpenAlex-data-license). Metadata is CC0.
- **Access:** activated free API key for the service contact, sent only in the Authorization header. Never included in a URL, cache key, client bundle, fixture or log.
- **Free limits:** the account reports $1/day, $0 prepaid; a basic search costs $0.001. No top-ups or paid plan. Before each uncached search the service verifies the current allowance and absence of prepaid credit; unknown limits fail closed. OpenAlex enforces the free account ceiling across concurrent requests. No anonymous fallback, paid endpoints, full-text downloads or automatic retries.
- **Use:** up to two keyword queries per lookup, ten results each, no pagination. Seven-day cache of public bibliographic metadata. 402/budget exhaustion pauses further searches until the UTC reset; 429 respects Retry-After. Papers are unreviewed search results, never clinical evidence events or status changes. Abstracts are not requested, stored or published.

## Research Organization Registry (ROR) v2

- **Checked:** 2026-11-13. [REST API](https://ror.readme.io/docs/rest-api), [client IDs](https://ror.readme.io/docs/client-id), [terms](https://ror.org/terms/). ROR metadata is CC0.
- **Access:** public API, no key or account required. Client-ID registration is paused; no identifier is invented.
- **Free limits:** 2,000 requests per five minutes per IP. At most three explicit organisation names per lookup, modest request pacing, seven-day metadata cache and shared 429 cooldown. No automatic retries.
- **Use:** affiliation matching returns an organisation only when ROR marks it chosen. Names come from the supplied report, not from paper affiliations; the ROR identifier establishes organisation identity, not involvement in a study or an endorsement.
