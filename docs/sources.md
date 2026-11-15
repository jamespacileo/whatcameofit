# Data sources

Terms, authentication and rate limits for each external source. Check an entry again before changing its client, and update the date.

"Observed" means seen in live responses on the date checked, not stated in documentation.

## ClinicalTrials.gov API v2

- **Checked:** 2026-11-11
- **Terms:** <https://clinicaltrials.gov/about-site/terms-conditions> (last updated 31 January 2023)
- **API:** <https://clinicaltrials.gov/data-api/api>
- **Local trial reader (2026-11-14):** the server reuses the single-study public API, with the configured contact identity, an eight-second deadline, a dedicated 60-per-minute request limit per Cloudflare location, and a 24-hour fresh cache. Only identifiers cited by the published export are read. The reader labels its formatted selection, retrieval date and registry update date; a copy up to seven days old is shown only during a transient outage and is labelled as older. Visitor cookies and credentials are never forwarded. The registry's browser-only internal API is not used.
- **Authentication:** none. Requests without a key succeed (observed).
- **Rate limit:** not stated on the pages read. The client defaults to 2 requests per second, below the roughly 3 per second in `SPEC.md`.
- **Terms that bind the site:** attribute the data to ClinicalTrials.gov; keep it current; clearly display the date the data were processed by ClinicalTrials.gov; state any modifications; do not claim proprietary rights or present it as anything other than a United States Government database; do not use email addresses from it for promotion.
- **Behavior (observed):** an unknown but well-formed identifier returns 404; a malformed one returns 400, so the client checks the format first. Searches page with `nextPageToken`; the last page has no token and may be empty. Dates can be `YYYY-MM-DD` or `YYYY-MM`, each with a type of `ACTUAL` or `ESTIMATED`.
- **A search it cannot read (observed 2026-11-14):** the search answers 400 with a plain-text reason, such as `Error parsing query in Intervention / treatment: Too complicated query` for a thirteen-word phrase, or an error for a bare `AND`, `NOT`, `AREA` or `COVERAGE`. The client raises it as an unsearchable term naming the term and the reason. `resolve` reports the term, searches the claim's other terms, and sends nothing simpler in its place.
- **Search within a condition (observed 2026-11-11):** `countTotal=true` adds `totalCount` to the first page. `query.cond` narrows a search by condition and accepts `OR` between words. A condition worded the registry's way narrows well ("CAR-T cell therapy" has 2,071 trials, 2 with `query.cond=Stiff person syndrome`). A lay or long wording can return nothing ("Vitamin C" with "Pre-leukaemia blood disorders (CCUS and low-risk MDS)": 0; with "myelodysplastic syndrome": 16). The client therefore narrows only names with more than 100 trials, and tries the condition as worded and then its telling words joined with `OR`. A name that still has more than 100 trials within the condition, or none, contributes no candidates: the first live run met "the drug" recorded as another name for a treatment.

- **Search by a trial's name (observed 2026-11-12):** `query.titles="SURMOUNT-5"` searches titles and acronyms and returned that one trial. The lookup asks for at most 20 and treats a name that more trials carry as identifying none. The search fields now also ask for `Acronym`, `EnrollmentCount` and `CollaboratorName`, which the lookup compares with what an article says of its trial.
- **Fields republished as trial facts (checked 2026-11-14, openspec `trial-facts`):** from the full record already stored with each trial event: `designModule` (study type, allocation, masking, enrolment count and whether it is actual or estimated), arm group types, `eligibilityModule.healthyVolunteers` and `stdAges`, the lead sponsor's name and class, planned primary outcomes (measure and time frame), `statusModule.whyStopped`, and from `resultsSection` the posted primary outcomes with each group's title, number analysed and value, and each posted analysis's p value and method. Never republished: eligibility criteria, locations, contacts, and any free-text description of a group, outcome or analysis (one read on this date said a treatment "significantly reduced" a measure). The registry's overall status is reduced to seven states, so the site never says a trial is recruiting. No request is added: the facts are read at export from stored records.
- **How the terms are met for trial facts:** each trial entry shows the date its record was fetched, the section says the facts are a selection, unaltered, from the linked record, and the footer attributes ClinicalTrials.gov.
- **A lead sponsor can be a person (observed 2026-11-14):** of fourteen records with results, three had a person's name as `leadSponsor.name`, all with `class` `OTHER`, and all with `responsibleParty.type` `SPONSOR_INVESTIGATOR`. The class `INDIV` alone does not find them. Trial facts treat either sign as a person and export the kind without the name.
- **A reference's type (read 2026-11-14, openspec `paper-facts`):** a record's `referencesModule.references` each carry `pmid`, `type` and `citation`. The API's enumeration (<https://clinicaltrials.gov/api/v2/studies/enums>, `ReferenceType`) has three values and defines none of them; the definitions are on two other pages.
  - `RESULT` and `BACKGROUND` are the sponsor's answer to one question. The Protocol Registration Data Element Definitions (<https://clinicaltrials.gov/policy/protocol-definitions>, "References") define "Citations" as "Citations to publications related to the protocol: background and/or results", and "Results Reference?" as "Indicate if the reference provided reports on results from this clinical study. Select Yes/No." The Study Data Structure page (<https://clinicaltrials.gov/data-api/about-api/study-data-structure>) gives `ReferenceType` the definition "Results Reference". So `RESULT` is a publication the sponsor says reports results from the study, and `BACKGROUND` is one the sponsor listed and did not say that of.
  - `DERIVED` is not in the sponsor's definitions: the registry adds it. A study's own page (<https://clinicaltrials.gov/study/NCT01596231>, "Publications") heads these "From PubMed" and says: "These publications are automatically filled in from PubMed, a public database of scientific and medical articles, and may or may not be about the study." The one `DERIVED` reference in that record is the paper whose PubMed record carries the trial's number.
  - **What follows for wording:** `RESULT` may be worded as listed by the sponsor as reporting the study's results. `DERIVED` may be worded only as linked by the registry from PubMed, and the site says the registry's own caution that such a paper may or may not be about the study. Neither is called "the results" by the site. `BACKGROUND` references are not read. The `citation` string names authors and is read nowhere.

- **Bulk loads through the list endpoint (observed 2026-11-14):** `GET /studies` accepts `pageSize` up to 1,000 with a chosen list of `fields` and a `filter.advanced` expression, and pages with `nextPageToken`. The 43,320 phase 3 interventional trials of a drug or biological came back in 44 requests; the whole registry (611,771 studies) is about 620. `thenwhat backfill load-trials` uses this instead of one request per trial, at the same 2 requests per second, and counts its requests against the registry's allowance (`SOURCE_ALLOWANCES`). A load of changes adds `AREA[LastUpdatePostDate]RANGE[<date>,MAX]` to the expression. The loaded trials are kept in the private database only and are not exported.

## Europe PMC RESTful web service

- **Checked:** 2026-11-11
- **Terms:** <https://europepmc.org/Copyright>
- **API:** <https://europepmc.org/RestfulWebService>
- **Authentication:** none (observed).
- **Rate limit:** not found on the pages read. The client defaults to 2 requests per second. The live lookup starts at most three linked-paper requests, at least 500 ms apart, with a five-second allowance for all of them together.
- **Terms that bind the site:** almost all material is copyright of publishers or authors, including abstracts. Crawling the website to download batches of articles is prohibited. The pipeline uses the web service only, stores abstracts in raw payloads for matching, and never publishes them. The site shows a paper's title and a link.
- **Behavior (observed):** a DOI is looked up with `query=DOI:"…"`; an unknown DOI returns `hitCount` 0, not an error. Citing papers come from `query=CITES:<id>_<source>` with `resultType=core` and are paged with `cursorMark`.

- **A paper's own trial (observed 2026-11-12):** a PubMed number is looked up with `query=EXT_ID:<number> AND SRC:MED`. The core record of a trial's report carries its ClinicalTrials.gov number in `abstractText` ("ClinicalTrials.gov number, NCT…"); `dbCrossReferenceList` was empty for the paper tried. The lookup reads the number from the abstract, shows no part of the abstract, and treats a paper that gives more than three numbers as a review. The Worker asks the same question from Cloudflare with the same contact address. It may cache the extracted trial identifiers for up to 24 hours under a versioned query digest; it never caches the abstract.
- **A core record not asked for lately is slow (observed 2026-11-14):** `resultType=core` for a DOI took 17 to 25 seconds on the first request for each of two recent papers, and one request answered 500 after 32 seconds. The same requests took under 0.3 seconds a minute later, and `resultType=lite`, which has no abstract, took under 0.1 seconds throughout. The Worker therefore does not wait for a paper once the model has read that the text reports no treatment. A lookup that does report a treatment starts at most three paper requests, at least 500 ms apart, and gives them five seconds together. Name-based registry searching and optional enrichment overlap these requests. A paper not answered in that time, or answered with an error, is passed over: the answer counts it, the site says a linked paper could not be looked up, and the answer is not cached, so the next lookup asks again, by when Europe PMC usually answers quickly. The pipeline's own lookup has no such deadline.
- **Fields republished as paper facts (terms read 2026-11-14, openspec `paper-facts`):**
  - **What the terms say.** Europe PMC's Copyright page (<https://europepmc.org/Copyright>) is about articles: "All of the material available through the Europe PMC site is provided by the respective publishers or authors. Almost all of it is protected by U.K. and/or foreign copyright laws", and the web services are "the only services that may be used for automated downloading". It says nothing of its own about index fields (publication types, journal titles, subject headings). The Articles RESTful API page (<https://europepmc.org/RestfulWebService>) describes the `core` result as "full metadata for a given publication ID; including abstract, full text links, and MeSH terms" and states no licence and no rate limit for it. The publication types and subject headings of a `MED` record are the National Library of Medicine's MEDLINE indexing. NLM's terms for its data (<https://www.nlm.nih.gov/databases/download/terms_and_conditions.html>, last reviewed 21 May 2019) ask a user to acknowledge NLM as the source, not to imply its endorsement, and, when republishing, to keep the data current or make known that it may not be.
  - **Our reading.** A paper's title, journal title, year, publication types, open access mark and the two check tags "Humans" and "Animals" are bibliographic facts about the paper, not its text. The site republishes them with a link to the paper, the name of the index, and the date the record was read, and refreshes a stored record after thirty days (`PAPER_RECORD_MAX_AGE_DAYS`). This is a reading of pages that do not address the question directly; read them again before republishing any further field.
  - **Republished:** `title`, `journalInfo.journal.title`, `pubYear`, `pubTypeList` reduced to twelve kind codes (a type with no mapping is dropped), `isOpenAccess`, whether `pubTypeList` holds "Retracted Publication", and whether `meshHeadingList` holds the descriptor "Humans" or "Animals". No other subject heading is read or shown.
  - **Never stored for paper facts:** `abstractText`, `authorList`, `authorString`, `authorIdList`, `affiliation`, `investigatorList`, `fullTextUrlList` and `fullTextIdList` are removed before the record is stored in `paper_record`. This is the one stored payload that is reduced: an evidence event's payload is stored as received. **Never republished:** every other field, citation counts, grants and chemicals included.
  - **Requests:** one per distinct paper (`query=DOI:"…"` or `query=EXT_ID:<PubMed number> AND SRC:MED`, `resultType=core`), at the client's 2 a second, and none for a paper whose stored record is younger than the configured age.

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
- **What is read:** per outlet domain, `robots.txt`, then `/favicon.ico`, and when that is not an image, or is a blank placeholder (an ICO with every pixel transparent), the home page and at most two icons it names with `<link rel="icon">` or `apple-touch-icon`. Another host an icon lives on has its own robots.txt read first. The home page is read to find the icon's address and is kept nowhere.
- **Authentication:** none.
- **Terms:** each outlet has its own and they are not read one by one. The rule applied to all: robots.txt decides. A host whose rules refuse the client, or cannot be read, is sent nothing more.
- **Rate limit:** none published for this. The client sends one request per second at most and asks each domain once; `thenwhat icons --retry-missing` asks again only the domains that had no usable icon. `make public-export` runs `thenwhat icons` first, so outlets added since the last run are asked.
- **What is kept:** one raster image (PNG, ICO, GIF, JPEG or WebP, told from its bytes) of at most 100,000 bytes, with its address and fetch time. SVG is not kept: it can carry script and the site would serve it from its own address.
- **Terms that bind the site:** the icons are the outlets' own marks. The site shows one only beside the outlet's name and a link to its article, to say where a report came from. Remove an outlet's row from `outlet_icon` if it asks.
- **Behavior (observed):** extra.ie, futurism.com and vice.com answer `/favicon.ico` with a 198-byte, fully transparent 16-pixel ICO (seen 2026-11-11, found blank 2026-11-13). kyoto-u.ac.jp has no `/favicon.ico`; its home page names a 32-pixel ICO, which is the icon in the seed file. That one fetch was made with a generic client name.
- **Safari asset audit (2026-11-13):** Dental Tribune's global and Indian editions now use its [declared DT mark](https://www.dental-tribune.com/wp-content/themes/dt/images/favicon/favicon-96x96.png), replacing a generic WordPress icon. [Daily Express](https://cdn.images.express.co.uk/appletouchicons/20160608/apple-touch-icon-180x180.png) uses its high-resolution touch icon instead of the faint favicon. USC Dentistry's [crest](https://dentistry.usc.edu/wp-content/uploads/2019/11/cropped-fevicon-180x180.png) is on the university's cardinal background for contrast; [ZME Science](https://cdn.zmescience.com/wp-content/uploads/2021/08/cropped-logo-zmescience-180x180.png) uses its current black mark. Griffith's [declared icon](https://cdn-ildedah.nitrocdn.com/nYYorQKadnvAORgWEyKkpWpwPIyqNOMp/assets/images/source/rev-14be058/news.griffith.edu.au/wp-content/uploads/2024/05/griffith-favicon.svg) was inspected and rasterised, so no SVG document is served. These replacements are bounded to 96 pixels and stored in the operator database as well as the public snapshot. Courthouse News's generic WordPress image was cleared; it uses the letter fallback. Hosts that block icon retrieval remain on letter fallbacks.

## UKCRC Health Research Classification System (HRCS)

Not an API. A fixed list of 21 health categories, used to check that the site's groups cover every area of health.

- **Checked:** 2026-11-12
- **Terms:** <https://hrcsonline.net/getting-started/conditions-of-use/>. All content on the site is licensed CC BY-NC-ND 2.0 England & Wales. The system may be used and distributed, but not altered or used for commercial benefit.
- **Categories:** <https://hrcsonline.net/health-categories/>
- **How it is used:** the category names sit, unaltered and with attribution, in `pipeline/src/thenwhat/claims/verticals.py` as anchors for each group. A configuration check reads them. Neither the export nor the site carries HRCS codes or names, and the groups' titles are our own wording, not an adaptation of HRCS.
- **What would change this:** any commercial use of the project. The non-commercial term then needs checking again with UKCRC before the anchors are kept.

## Not yet checked

ISRCTN, EU CTIS, WHO ICTRP, PubMed E-utilities, NIH RePORTER, UKRI Gateway to Research, Companies House, SEC EDGAR, openFDA, EMA and MHRA have no client. Add an entry here before writing one. OpenAlex and ROR are implemented for live lookup enrichment; their entries are below.


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

Reddit submission dumps published by third parties are a separate matter, decided by the operator on 2026-11-14: see "Link datasets for the social-link backfill" at the end of this file. Reddit itself is still asked nothing.

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
- **Use:** up to two keyword queries per lookup, then one query per organisation the report names and ROR identified (at most three): the treatment's terms joined with `OR`, filtered to works with an author at that organisation (`authorships.institutions.ror`) and, when the report's date is known, published from two years before it to a month after. Ten results each, no pagination. So an uncached lookup sends at most five searches ($0.005). Before them, up to three papers the article itself links to (by DOI or PubMed number) are fetched by identifier (`/works/doi:…`, `/works/pmid:…`): a single-record request the account reports as costing $0, sent only while it still does and no prepaid credit exists. Seven-day cache of public bibliographic metadata. 402/budget exhaustion pauses further searches until the UTC reset; 429 respects Retry-After. Papers are unreviewed search results, never clinical evidence events or status changes. Abstracts are not requested, stored or published.
- **Headers (observed 2026-11-14):** every answer to a search states its price and what is left of the day: `X-RateLimit-Cost-USD` (0.001), `X-RateLimit-Limit-USD` (1), `X-RateLimit-Remaining-USD`, `X-RateLimit-Prepaid-Remaining-USD` (0) and `X-RateLimit-Reset` (seconds to the UTC reset). A lookup of one work by its identifier (`/works/doi:…`) costs nothing.
- **Pipeline use:** `thenwhat resolve` sends one search per claim: every name, other name and search phrase of the intervention as quoted phrases joined by `OR`, together with the indication as a quoted phrase (`("a" OR "b") AND "condition"`), twenty results, no second page. That is the only search. When it finds nothing, `resolve` says the claim has no related paper and nothing looser is tried; the operator can give the intervention a search phrase and resolve again. A search's answer is kept for seven days, so resolving a claim again within the week spends nothing. Looking one work up by its identifier is free and is used to score pending papers again, to date the papers offered as the origin paper and to read a PubMed number. No request is sent while `OPENALEX_API_KEY` is empty. The pipeline does request the abstract (`abstract_inverted_index`), to score a paper and find its reasons. It stays in memory and in the HTTP cache, and is never exported, logged or shown; recorded fixtures have it replaced.
- **Pipeline search by organisation:** after that search, `thenwhat resolve` sends one more for each organisation the article named and ROR identified (not rejected, at most three per claim): the same terms as quoted phrases joined by `OR`, without the indication, with `filter=authorships.institutions.ror:https://ror.org/<id>` and, when the claim has a first reported date, `from_publication_date` two years before it and `to_publication_date` 31 days after. Ten results, one page. So a claim costs at most four searches ($0.004). Observed 2026-11-14 for a King's College London report: the search with the indication did not return the report's paper; this one returned it second of six.
- **Pipeline allowance rules:** the client reads the headers above on every answer to a search. It stops sending searches until the reset the source states (or the next midnight UTC) when the day's remainder is less than one search, when the source answers 402 or 429 with nothing left, when the answer does not state the remainder or the prepaid amount, or when the account holds prepaid credit. The stop is kept in the database, so every process of `thenwhat prepare` and every later run of the day stops too. Nothing is retried. `resolve` ends with one line saying how many searches were sent, what they cost, how many were answered from the cache, what is left of the day and, if searches have stopped, why.

## Research Organization Registry (ROR) v2

- **Checked:** 2026-11-13. [REST API](https://ror.readme.io/docs/rest-api), [client IDs](https://ror.readme.io/docs/client-id), [terms](https://ror.org/terms/). ROR metadata is CC0.
- **Access:** public API, no key or account required. Client-ID registration is paused; no identifier is invented.
- **Free limits:** 2,000 requests per five minutes per IP. At most three explicit organisation names per lookup, modest request pacing, seven-day metadata cache and shared 429 cooldown. No automatic retries.
- **Use:** affiliation matching returns an organisation only when ROR marks it chosen. Names come from the supplied report, not from paper affiliations; the ROR identifier establishes organisation identity, not involvement in a study or an endorsement.
- **Pipeline use:** `thenwhat resolve` asks once per institution and company entity of a claim, at two requests a second, with the 24-hour HTTP cache. Only the organisation ROR marks chosen becomes a match, scored by ROR's own measure and approved by rule only on strong evidence (openspec `organisations`): ROR chose it, the name given is exactly one of the record's names, labels, aliases or acronyms, the record is not typed only as ROR's catch-all "other", the name is not a journal title held in the paper records, and a government body's name states its country. Any other chosen record stays a pending match and the organisation unidentified; no looser match is tried. An operator can reject an approved one. A person is never looked up. `thenwhat fetch` adds the lead sponsor of each trial with approved events as an institution or company entity, so sponsors are looked up the same way.
- **What is republished (read 2026-11-14, openspec `organisations`):** five fields of an identified organisation's record and no more: the display name (the name typed `ror_display`), the types as lower-case codes, the country name of the first location, the website (only an `https` link typed `website`), and the record's address `https://ror.org/<id>`. With them go ROR's match score for the name and the time the record was read. CC0 asks for no credit; the claim page still names ROR and says it identifies an organisation without verifying its part in a claim.
- **What is never exported:** founding year, aliases, acronyms and labels in other languages, parent, child and related organisations, identifiers in other registries (Wikidata, ISNI, Crossref Funder, GRID), domains, coordinates, city and subdivision, and the record's admin dates. Each is a step towards a profile of the organisation, which the site does not keep.
- **What is kept:** each chosen match's `organization` object as fetched, with the fetch time, in `organisation_record`, once per ROR identifier.

## NLM Medical Subject Headings (MeSH)

Read before the client was written (openspec `knowledge-cards`, task 1.1).

- **Checked:** 2026-11-14
- **Terms:** <https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html> (last reviewed 4 October 2018). "NLM freely provides MeSH data." No charge, fee or royalty. Translation files are not covered and are not used.
- **Services:** MeSH RDF, <https://id.nlm.nih.gov/mesh/>; documentation at <https://hhs.github.io/meshrdf/> and its "SPARQL and URI Requests" page. A term's record is `GET https://id.nlm.nih.gov/mesh/<year>/<identifier>.json`; terms by label are `GET https://id.nlm.nih.gov/mesh/lookup/descriptor?label=…&match=exact&limit=10&year=<year>`. Entry terms are `GET https://id.nlm.nih.gov/mesh/lookup/term?label=…&match=exact&limit=10&year=<year>`, and the record an entry term belongs to is one SELECT query at `GET https://id.nlm.nih.gov/mesh/sparql?query=…&format=JSON&year=<year>&inference=false` (both added for task 2a.1, below).
- **Authentication:** none (observed).
- **Rate limit:** none stated for the record and lookup addresses. For the SPARQL service, NLM's Acceptable Use Policy (<https://hhs.github.io/meshrdf/acceptable-use-policy>, page last updated 13 August 2026, read 2026-11-14) asks for "no more than 500 requests per minute per IP address"; a request over the limit is not served and service returns after 30 seconds. One SPARQL answer holds at most 1,000 results. The client defaults to 2 requests per second, and a term's stored record is asked for again no sooner than ninety days later.
- **Terms that bind the site:** acknowledge NLM as the source "in a clear and conspicuous manner"; do not indicate or imply that NLM endorses the site; when republishing, either keep the data the most current or make known that it may not be, "and/or identify the version of MeSH being used". NLM gives no warranty for the data.
- **Credit line:** "Medical Subject Headings (MeSH), U.S. National Library of Medicine". A card also states the MeSH year and the date its record was read, and says NLM does not endorse the site.
- **Which field gives the version (observed):** none inside the record. A record holds `dateIntroduced` and `lastUpdated`, which are the term's own dates, and no year of the vocabulary. The version is in the address: `/mesh/2026/D009765.json` answers with `"@id": "http://id.nlm.nih.gov/mesh/2026/D009765"`, and the address without a year serves the current vocabulary with no year in `@id`. The client therefore asks the address of the year in which it asks, and reads the version back from the year in the record's `@id`. A year NLM has not published answers like an unknown identifier (`/mesh/2027/…` on this date), so in the weeks around a new year's release a lookup can find nothing; it is then run again later, and no other year is tried.
- **Behavior (observed, generic client name, no key):** a record is JSON-LD served as `application/rdf+json`. A descriptor carries `label`, `identifier`, `preferredConcept` and no definition. The definition is the `scopeNote` of the preferred concept's own record (`/mesh/2026/M0015159.json`), a second request. An unknown identifier answers 200 with an empty object, not 404. `match=exact` compares without regard to case ("obesity" returns "Obesity") and answers `[]` when no label is equal. `match=contains` for "Obesity" lists "Anti-Obesity Agents" first; the client never asks it, and compares labels itself as well. A supplementary record (`C…`) read without a year can be inactive with a label starting "[OBSOLETE]"; a year's address was not seen to serve one.
- **Entry terms (observed 2026-11-14, generic client name, no key; task 2a.1):**
  - `lookup/term` with `match=exact` compares the name with each term's own wording, without regard to case, and answers the term's identifier, not the record it belongs to: `[{"resource": "http://id.nlm.nih.gov/mesh/T713007", "label": "Ketogenic Diet"}]`. It finds an entry term of a descriptor labelled otherwise ("Ketogenic Diet", where `lookup/descriptor` answers `[]`) and the term of a supplementary record ("orforglipron"). A word contained in a term answers `[]` ("Ketogenic").
  - A term's own record names no owner. The record it belongs to is found by one query at `/mesh/sparql`, which can ask for several terms at once:

    ```sparql
    PREFIX meshv: <http://id.nlm.nih.gov/mesh/vocab#>
    PREFIX mesh: <http://id.nlm.nih.gov/mesh/>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?term ?record ?label ?type WHERE {
      VALUES ?term { mesh:T713007 mesh:T001140881 }
      ?concept meshv:term|meshv:preferredTerm ?term .
      ?record meshv:concept|meshv:preferredConcept ?concept .
      ?record rdfs:label ?label .
      ?record a ?type .
    } ORDER BY ?term ?record
    ```

    It answered `D055423`, a `TopicalDescriptor` labelled "Diet, Ketogenic", for the first and `C000729680`, an `SCR_Chemical` labelled "orforglipron", for the second. A term identifier the vocabulary does not hold answers no row. Addresses in the answer carry no year, though the query names one.
  - The SPARQL page (<https://hhs.github.io/meshrdf/sparql-and-uri-requests>, page last updated 13 August 2026) states the parameters `query`, `format`, `year`, `inference`, `limit` (1,000 at most) and `offset`, and that `format=HTML` is refused by the endpoint. It states no terms beyond the Acceptable Use Policy above.
  - A supplementary record (`/mesh/2026/C000729680.json`) holds `label`, `note`, `source` (the paper NLM took the record from), `preferredMappedTo` and `preferredConcept`. Its concept's record holds no `scopeNote`. Its definition is therefore the record's own `note` field. `source` and `preferredMappedTo` are not used.
  - There is no lookup of supplementary records by label (`lookup/supplemental…` answers 404).
- **What is kept:** the descriptor's or supplementary record's and its concept's records as fetched, with the fetch time, in `term_record`.
- **What is not used:** annotations, history notes, tree numbers, qualifiers and "see also" links. They are indexing instructions, not descriptions.

## Global Substance Registration System (GSRS)

Read before the client was written (openspec `live-lookup`, task 4.3). It maps a drug's generic or brand name to the development codes a trial registry may file its trials under, such as CIN-107 for baxdrostat.

- **Checked:** 2026-11-14
- **Why this source and not the others considered:** GSRS gives every name of a substance a kind, and one kind is "Code" (`cd`), so a code is told from a brand, a common or a chemical name by the source itself. The NCI Thesaurus (CC BY 4.0) was read on the same date: its exact search for "baxdrostat" returned the concept C184908 with no code among its synonyms. ChEMBL lists research codes too, but is CC BY-SA 3.0 and is not accepted until the operator's decision on share-alike material (`knowledge-cards`, task 6.1).
- **Licence:** <https://gsrs.ncats.nih.gov/licensing> (read in a browser; the page is drawn by script). "Unless otherwise noted, the data provided by GSRS is public domain and made available with a Creative Commons CC0 1.0 Universal dedication." The software is under Apache 2.0, which does not concern the data. GSRS is run by NCATS with the FDA, which assigns the Unique Ingredient Identifier (UNII).
- **Terms that bind the site:** none for the data. No attribution is required; the list of sources credits "Global Substance Registration System, FDA and NCATS" all the same. Nothing from GSRS is published: a code is a search term, and the export does not carry it.
- **API:** `https://gsrs.ncats.nih.gov/api/v1`. The pipeline asks two things. A substance by exact name: `GET /substances/search?q=root_names_name:"^<name>$"&top=5&fdim=0`. Its names: `GET /substances(<uuid>)/names`.
- **Authentication:** none (observed). Names an organisation has marked protected are not served without signing in, and are not sought.
- **Rate limit:** none stated on the licensing page or in the API's answers. There is no `robots.txt` on the host (404 on this date). The client sends one request a second with the contact User-Agent, and keeps each answer for thirty days.
- **Behavior (observed, generic client name, no key):**
  - The search answers 200 with `total`, `count` and `content`, a list of substances in a short form: `uuid`, `_name`, `approvalID` (the UNII), `substanceClass`, `status`, a structure where there is one, and `_names` with a count and the address of the names. `fdim=0` leaves most of the search's facet counts out of the answer.
  - `^…$` asks for a whole name, whatever its case: "baxdro" and "USAN" (which is inside "BAXDROSTAT [USAN]") find nothing. It does set punctuation aside: "cin 107" finds the substance whose code is "CIN-107". The client therefore reads each substance's names and keeps the substance only when one of them equals the name asked for, ignoring case and runs of spaces and nothing else.
  - A name is found whatever its kind: "Baxfendy" (brand), "CIN-107" (code) and "baxdrostat" all lead to the one substance. "vitamin C" leads to Ascorbic Acid, "MDMA" to Midomafetamine. "insulin", "CAR-T cell therapy", "faecal microbiota transplant" and "olaparib and bevacizumab" find nothing: a class, a method and a combination are not substances.
  - Each name carries `name`, `type`, `deprecated`, `languages` and more. The kinds, from the registry's own vocabulary (`/vocabularies/search?q=root_domain:NAME_TYPE`): `of` Official Name, `sys` Systematic Name, `bn` Brand Name, `cn` Common Name, `cd` Code. Baxdrostat has twelve names, three of them codes: CIN-107, RO-6836191 and RO6836191. Aspirin has 64 names, three of them codes.
  - A "Code" is any code, not only a company's development code: aspirin's are BAY1019036 and two National Service Center numbers (NSC-27223, NSC-406186). No rule here tells them apart, so each is searched for, within the claim's indication only.
  - The names of an unknown substance answer 404 with `{"message":"not found","status":404}`.
- **The rule (no loose matching):** a code is taken only when the names an intervention is recorded under lead to exactly one substance, and only from the names GSRS marks `cd` and not `deprecated` for that substance. Names that lead to two substances (a drug and its salt, say) give no code. No part of a name is tried, no spelling is corrected, and no model is asked. An intervention GSRS does not list has no code, and `resolve` and `entity codes` say so.
- **What is kept:** in `entity_substance`, per intervention: the substance's short record and all its names as fetched, the fetch time, the substance's identifier and page, and the codes taken. A live lookup keeps nothing beyond the thirty-day cache of the two answers.
- **What is not used:** structures, chemical and systematic names, relationships, references and the code systems under `codes` (CAS numbers and the like, which are identifiers in other databases, not names a trial is filed under).
- **Not asked from the site's Worker.** The public lookup service does not ask GSRS: that would send the treatment's name from the reader's search to a further host, which the words beside the search button do not say. It is the operator's decision (see `openspec/changes/live-lookup/design.md`).

## Open Targets Platform

Read for the drug and target cards (openspec `knowledge-cards`, task 1.2). The client reads targets only: a search of targets for a word of an intervention's name, and a target's record by its identifier (group 2a). Since the operator's decision on share-alike material (task 6.1, below) it also reads a drug by its own name, with its kind of molecule and mechanisms. A target link is stored and checked, and since the operator's acceptance on 2026-11-14 (task 2a.18, below) an approved one gives a target card.

- **Checked:** 2026-11-14
- **Licence page:** <https://platform-docs.opentargets.org/licence>. "Open Targets Platform is marked with CC0 1.0." The same page lists each data source with its own licence and says every listed source has "agreed for their data to be used without restriction by all Open Targets users".
- **Terms of use:** <https://platform-docs.opentargets.org/licence/terms-of-use>. They add no constraint beyond the data owner's. Open Targets "expects attribution" for its services and data. Use at a level that prevents, or looks likely to prevent, service to others is blocked.
- **Citation asked for:** <https://platform-docs.opentargets.org/citation>: Buniello, A. et al. (2025), "Open Targets Platform: facilitating therapeutic hypotheses building in drug discovery", Nucleic Acids Research.
- **API:** GraphQL at `https://api.platform.opentargets.org/api/v4/graphql`, documented at <https://platform-docs.opentargets.org/data-access/graphql-api>. No key. No rate limit is stated. The page says the API serves queries for a single target, disease or drug, discourages "repeatedly querying the GraphQL API one entity at a time", and points systematic use to the data downloads. One search and one record per named drug is single-entity use; a run over every claim at once should read the downloads instead.
- **Licences of the parts a card would use, each listed separately:**

| Part | Drawn from | Licence | Where it is stated | Read |
| --- | --- | --- | --- | --- |
| That a drug is in the platform, its name and identifier | Open Targets Platform | CC0 1.0 | <https://platform-docs.opentargets.org/licence> | 2026-11-14 |
| Kind of molecule and mechanisms of action | ChEMBL (the platform's drug page names ChEMBL as the source of "Molecule information, Mechanisms of action": <https://platform-docs.opentargets.org/drug>) | CC BY-SA 3.0 Unported | Open Targets' licence table, and ChEMBL's own page <https://chembl.gitbook.io/chembl-interface-documentation/about>: "made available on a Creative Commons Attribution-Share Alike 3.0 Unported License" | 2026-11-14 |
| A target's protein name and function description | UniProt (the platform's target page names UniProt for protein information: <https://platform-docs.opentargets.org/target>) | CC BY 4.0 | Open Targets' licence table, and UniProt's own page <https://www.uniprot.org/help/license> (last modified 18 December 2024): CC BY 4.0 applies "to all copyrightable parts of our databases" | 2026-11-14 |

- **What follows for the site:** the data file is offered under CC BY 4.0. A CC BY 4.0 fact can enter it with credit. A CC BY-SA 3.0 fact cannot enter it without making the file share-alike, and whether such a fact may be shown on a page at all is the operator's decision (task 6.1). The operator decided on 2026-11-14 that it may (ADR 0002): the list of sources in `pipeline/src/thenwhat/sources/terms.py` marks ChEMBL accepted and not allowed in the data file. Open Targets' own data and UniProt's descriptions were accepted separately (task 2a.18, below).
- **UniProt's disclaimer (same page):** its medical information is "for research, educational and informational purposes only" and is no substitute for professional advice. A target card would sit under the site's own notice that cards are not advice.
- **Behavior (observed 2026-11-14, generic client name, no key; task 2a.2):** the API answers a GraphQL query sent by POST (JSON body with `query` and `variables`) with 200, and the same query sent by GET with 500. A target found by `search(queryString, entityNames: ["target"])`, or read by `target(ensemblId)`, carries `id` (an Ensembl gene identifier), `approvedSymbol`, `approvedName`, `biotype`, `symbolSynonyms` (each a `label` and the `source` that gives it: `uniprot`, `HGNC` or `NCBI_entrez` were seen; one label can be listed once per source), `functionDescriptions` (a list of sentences; the first for CXCR3 starts "[Isoform 1]: Receptor for the C-X-C chemokines" and cites papers inline as "(PubMed:…)") and `proteinIds`. The function description is the field `functionDescriptions`, which settles what this entry left unchecked; a description does not name its own origin, and the platform's target page names UniProt for it. A search answers ten hits at most as asked, including targets whose symbol only starts with the word ("TMS" lists TMSB4X); the client keeps only a target whose symbol or listed synonym equals the word. An identifier the platform does not hold answers `{"data": {"target": null}}`. A word with no hit answers an empty list.
- **Pipeline use:** one target search per gene-like word of an intervention's names (about 55 for the claims of this date), one drug search per name of an intervention (about 190), and one record per approved target and per drug found, each cached and a search kept for ninety days; the client defaults to 2 requests per second. A run is started by the operator and is not scheduled.
- **What is kept:** a target's or a drug's record as answered, with the fetch time, in `term_record` under the source `opentargets`.
- **Drugs (observed 2026-11-14, generic client name, no key; task 6.2):** `search(queryString, entityNames: ["drug"])` and `drug(chemblId)` give a drug's `id` (a ChEMBL identifier), `name` (in capitals: "TIRZEPATIDE"), `drugType` ("Protein", "Small molecule", "Antibody drug conjugate" were seen) and `mechanismsOfAction.rows`, each with `mechanismOfAction`, `actionType` ("AGONIST", "INHIBITOR", "BINDING AGENT" were seen), `targetName` and `targets` (the genes of the target, each with the target fields above; an empty list when the target is not a human gene product). A search for "orforglipron" also answers "ORFORGLIPRON CALCIUM", and one for "semaglutide" also answers liraglutide; the client keeps only a drug whose own `name` equals the name asked, without regard to case. A drug can have no mechanism row (orforglipron, baxdrostat). A procedure's name ("Salpingectomy") answers no hit. An identifier the platform does not hold answers `{"data": {"drug": null}}`. The client asks for no phase, approval, indication, synonym or trade name.
- **Operator's decision on drug cards (task 6.1):** accepted on 2026-11-14, recorded in `docs/adr/0002-share-alike-drug-facts-on-pages-not-in-the-data-file.md`. ChEMBL-derived facts (kind of molecule, mechanisms of action, and that a drug's record names one protein as its target) are shown on claim pages with ChEMBL's credit and licence, and never enter the open data file, which names ChEMBL as left out.
- **Operator's decision on the named-gene target card (task 2a.18):** accepted on 2026-11-14. Asked: whether Open Targets' own data (CC0 1.0) and UniProt's function descriptions (CC BY 4.0, credited) are accepted for the page and the data file. Answer: "Yes, accept both". The list of sources marks `opentargets` and `uniprot` accepted and allowed in the data file from that date. A target card credits Open Targets with the citation above and names UniProt, with its licence, as the origin of the function description. `chembl` was accepted separately, for pages only (task 6.1, above).

## News indexes for the registry-first backfill

Read on 2026-11-14 for the change `backfill-work-ledger`, to choose where the news search step asks which articles name a trial's intervention and indication. The step needs an address, outlet, title and date for each article and must never receive or keep article text. Items marked unconfirmed were not found on the pages read.

### Media Cloud (chosen)

- **Checked:** 2026-11-14. [Terms of use](https://www.mediacloud.org/legal/media-cloud-terms-of-use) (effective 16 May 2023), [FAQ](https://mediacloud.org/documentation/faqs), [story guide](https://www.mediacloud.org/documentation/story-guide), [query guide](https://www.mediacloud.org/documentation/query-guide), [API client](https://github.com/mediacloud/api-client).
- **Terms:** any lawful use; the terms say the platform is not designed as a commercial tool. Access and keys may not be sold or sublicensed. Attribution is recommended, not required. No rights are granted over the stories' own content. The FAQ says lists of story addresses may be downloaded.
- **Authentication:** a free account and an API key. **The operator's step:** the account is created and the terms accepted by the operator, and the key goes in `.env` as `MEDIACLOUD_API_KEY`. No request is sent while it is empty.
- **Rate limit:** 4,000 API requests a week by default; some endpoints allow 2 requests a minute. More is given on request by email. The pipeline's allowance is set to 4,000 a week with 30 seconds between requests. On the first live run (2026-11-14) Media Cloud answered "too many requests" once, after 136 searches sent 30 seconds apart; after the hour's pause the remaining 61 went through at the same spacing. Sixteen of 197 searches got no answer within 60 seconds.
- **What a search returns:** story id, outlet name and address, title, publication date and the story's address, for a query with AND, phrases and proximity. Full text is never released, so none can reach the pipeline. Confirmed on a live answer on 2026-11-14: the fields are `id`, `indexed_date`, `language`, `media_name`, `media_url`, `publish_date`, `title` and `url`.
- **What is searched:** a search must name at least one collection (`cs`) or one outlet (`ss`) by its directory id; with neither it is refused with status 422. Both may be given and are searched together. Set in `.env` as `MEDIACLOUD_COLLECTION_IDS` and `MEDIACLOUD_SOURCE_IDS`.
- **Coverage:** over 200 million stories; an outlet is covered only from when its feed was first collected. The archive's start date is unconfirmed. Checked in the directory on 2026-11-14: there is no collection of health or clinical trade outlets. The national collections are `34412234` (United States, 246 outlets) and `34412476` (United Kingdom, 90 outlets). Trade outlets are listed one by one, and many are no longer collected: healio.com, onclive.com, medscape.com, fiercepharma.com, fiercebiotech.com, endpts.com, targetedonc.com and pharmatimes.com show no stories a week; statnews.com, biospace.com, medpagetoday.com, news-medical.net, ajmc.com and drugs.com are collected. In the first run biospace.com alone gave about two thirds of the trade press leads.
- **Size of the job:** one request per trial. The 43,320 phase 3 trials take at least 11 weeks at the default allowance.

### GDELT bulk datasets (not used)

- **Checked:** 2026-11-14. [Terms](https://www.gdeltproject.org/about.html#termsofuse), [data](https://www.gdeltproject.org/data.html), [Web NGrams 3.0](https://blog.gdeltproject.org/announcing-the-new-web-news-ngrams-3-0-dataset/), [BigQuery pricing](https://cloud.google.com/bigquery/pricing).
- **Terms:** open for academic, commercial and governmental use, with redistribution allowed. Any use must cite GDELT and link to gdeltproject.org.
- **Authentication and cost:** none for the raw files. BigQuery needs a Google Cloud project: the first 1 TiB scanned each month is free, then $6.25 per TiB.
- **Rate limit:** not stated for file downloads.
- **What is searchable:** the Global Knowledge Graph (from April 2013) holds GDELT's extracted themes, names and organisations, not free keywords. Web NGrams 3.0 (from January 2020) holds one record per word with the article's address and a few words of context; two keywords are matched by a join, and title, outlet and date come from a second table. The context words are fragments of article text and must be discarded if this is ever used.
- **Coverage:** nothing before April 2013; keyword matching only from 2020. Whether the trade press is included is unconfirmed.
- **The live DOC 2.0 interface:** searches back to January 2017 and answers "too many requests" above one request every five seconds. It refused every request from the operator's address on 2026-11-14, including single ones 40 minutes apart. No higher allowance is published; GDELT's posts send high-volume users to the datasets above.

### Common Crawl news crawl (ruled out)

- **Checked:** 2026-11-14. [Terms of use](https://commoncrawl.org/terms-of-use) (updated 7 March 2024), [news crawl data](https://data.commoncrawl.org/crawl-data/CC-NEWS/index.html).
- **Why not:** there is no keyword search. The files hold full article pages, about 47 TiB for 2016 to 2025, so using it means downloading and holding article text, which this project never does.

## Link datasets for the social-link backfill

Read on 2026-11-14 for a proposed backfill that starts from article addresses people shared, not from registry trials. No loader exists yet. Before one is written, re-read the primary pages named here: most of what follows about Reddit's own rules comes from secondary reports, because Reddit's pages sit behind a bot check.

### Hacker News monthly parquet archive (chosen)

- **Checked:** 2026-11-14. [Dataset card](https://huggingface.co/datasets/open-index/hacker-news), read from its `README.md` and the hub's own record of the dataset. [Hacker News API repository](https://github.com/HackerNews/API), whose licence is MIT.
- **What it is:** every Hacker News item, one parquet file per calendar month from 2006-10 (`data/YYYY/YYYY-MM.parquet`), about 25.8 GB in all. It is an independent mirror, not endorsed by Y Combinator: its history comes from ClickHouse's public copy of the official API, and new items from the official API itself.
- **Terms:** released under the Open Data Commons Attribution License (ODC-By) v1.0; the card says the original content is subject to the rights of its authors. Public, not gated, no account needed. **Attribution** is owed when the data is used publicly; nothing from it reaches the export, so none is shown on the site.
- **Freshness:** the hub's record showed the last change on 2026-08-23, so months after that may be missing. Check the file list before relying on a recent month.
- **Fields read:** `id`, `type` (1 is a story), `url`, `title`, `time`, `score`, `dead`, `deleted`. The loader asks the file for these columns only, so `by` (the author's username) and `text` are never read from disk.
- **How the operator obtains it:** download the monthly files wanted from the dataset's `data/` folder. No request is sent by the pipeline.
- **Rate limit and authentication:** none for the pipeline; the hub's own limits apply to the download.

### Hacker News on BigQuery (not read)

- **Checked:** not read on 2026-11-14. It needs a Google Cloud project of the operator's, and offers nothing the parquet archive lacks. Read its terms before using it.

### Hacker News search interface (not used)

- **Checked:** 2026-11-14. `hn.algolia.com/api/v1/search` answered counts of stories by address on that date without a key. Its documentation page did not give its rate limit to a plain fetch, so the limit is unconfirmed.
- **Why not:** it returns at most a page of results for a query, so a full list means many requests by domain and date, and it can only be asked about domains already listed. The archive shows which unlisted domains are shared most, which is how the outlet list grows.

### Reddit submission dumps (operator's decision: use, links only)

- **Checked:** 2026-11-14. [Arctic Shift download links](https://github.com/ArthurHeitmann/arctic_shift/blob/master/download_links.md), read directly. Reddit's Data API Terms and Public Content Policy were not re-read on this date; the reading of 2026-11-12 is in the table under "Platforms whose posts are not read".
- **What exists (observed):** monthly dumps of all submissions and comments are listed on Academic Torrents from 2024-04 to 2026-10, and the 2026-07 listing answered on this date. The single archive for 2005-06 to 2025-12 is struck through on Academic Torrents and offered by magnet link only, at about 3.8 TB. A per-subreddit release for the top 40,000 subreddits covers 2005-06 to 2023-12, so chosen subreddits can be taken without the whole archive.
- **Reported, not confirmed:** that the 2005 to 2025 archive was removed from Academic Torrents at Reddit's request from 30 July 2026; that Reddit stopped taking new public API requests on 31 October 2026 and ends public access in March 2027. Both come from third-party posts. The struck-through listing is consistent with the first.
- **Terms:** the dumps are published by third parties, not by Reddit, and carry no licence from Reddit. Reddit's Public Content Policy (May 2024) says use of its public content needs an agreement with Reddit and must respect deletions. A dump cannot respect a deletion made after it was taken. The supply may end without notice.
- **Operator's decision (2026-11-14):** asked whether to skip Reddit, use the dumps for links only, or wait. Answer: "the information is public domain and fair use, especially for educational and academic content like this app". Reddit dumps are used.
- **Limits applied to that decision (proposed by the assistant, not yet confirmed line by line):** what is kept from a submission is the address of the article it links to, the subreddit, the time, the score and the title it was shared under. The title is kept with the link lead, privately: the operator labels a sample of leads from their titles, and a reworded triage has to score the same title again (change `social-link-backfill`, design decision 4). It never reaches the export or the site. An earlier wording of this entry said the title would be dropped after triage; that could not be done. The author, the post's id and address, its text and its comments are never read out of the file or kept. Nothing in the export says an article was found through Reddit. Only link submissions are read; comment files are not downloaded.
- **Not a legal reading:** the decision rests on the operator's own view. Two points for whoever revisits it: the question Reddit raises is its terms of access, not copyright, and "fair use" is a United States doctrine while the operator is in the United Kingdom. Addresses and dates are facts, which is why only they are kept.
- **Rate limit and authentication:** none; the files are downloaded once by torrent and read locally.
- **Crossref Event Data's Reddit events:** allowed under the same decision and the same limits, if that archive is used.

## Live lookup source reuse (14 November 2026)

Successful public ClinicalTrials.gov responses and Europe PMC trial-number mappings may be reused for up to 24 hours under versioned hashed query keys. A paper with no indexed record is kept for one hour. Cache reads and writes are bounded and fall back to the source on failure; source failures and timeouts are never cached as successful empty answers. Paper abstracts, news text, images, credentials and reader identifiers are not retained. Concurrent identical requests within a source client share work without one caller’s cancellation cancelling another caller.
