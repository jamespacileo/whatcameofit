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
- **Search within a condition (observed 2026-11-11):** `countTotal=true` adds `totalCount` to the first page. `query.cond` narrows a search by condition and accepts `OR` between words. A condition worded the registry's way narrows well ("CAR-T cell therapy" has 2,071 trials, 2 with `query.cond=Stiff person syndrome`). A lay or long wording can return nothing ("Vitamin C" with "Pre-leukaemia blood disorders (CCUS and low-risk MDS)": 0; with "myelodysplastic syndrome": 16). The client therefore narrows only names with more than 100 trials, tries the condition as worded and then its telling words joined with `OR`, and falls back to the first page of the broad search.

## Europe PMC RESTful web service

- **Checked:** 2026-11-11
- **Terms:** <https://europepmc.org/Copyright>
- **API:** <https://europepmc.org/RestfulWebService>
- **Authentication:** none (observed).
- **Rate limit:** not found on the pages read. The client defaults to 2 requests per second.
- **Terms that bind the site:** almost all material is copyright of publishers or authors, including abstracts. Crawling the website to download batches of articles is prohibited. The pipeline uses the web service only, stores abstracts in raw payloads for matching, and never publishes them. The site shows a paper's title and a link.
- **Behavior (observed):** a DOI is looked up with `query=DOI:"…"`; an unknown DOI returns `hitCount` 0, not an error. Citing papers come from `query=CITES:<id>_<source>` with `resultType=core` and are paged with `cursorMark`.

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

## Not yet checked

ISRCTN, EU CTIS, WHO ICTRP, PubMed E-utilities, OpenAlex, NIH RePORTER, UKRI Gateway to Research, Companies House, SEC EDGAR, openFDA, EMA and MHRA have no client. Add an entry here before writing one.
