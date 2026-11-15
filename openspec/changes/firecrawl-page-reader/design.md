# Design

## Context

See `proposal.md` for why. What shapes the approach:

- `extract/retrieve.py` holds the only page fetch in the pipeline. `ArticleRetriever` reads robots.txt, fetches the page with `httpx`, falls back to an archived snapshot, and raises `PasteNeeded`. `probe()` does the same single fetch for `thenwhat outlets`. Five callers use it and none of them builds a request itself.
- `extract/page.py` turns HTML into a `Page`: plain text, headline, date, DOIs and registry numbers. Reported statements are checked word for word against that plain text.
- The retriever takes an `httpx` transport, which is the seam every retrieval test uses.
- Read from Firecrawl's documentation on 2026-11-15 (`docs.firecrawl.dev`, scrape and advanced scraping guides), not tried against a running service:
  - `POST /v2/scrape` takes `formats`; `rawHtml` is the HTML as served, `html` is the HTML with page furniture removed, `markdown` is the default.
  - Results are served from a cache up to two days old by default. `maxAge: 0` asks for a fresh copy and `storeInCache: false` asks for none to be kept.
  - `headers` sets request headers, a User-Agent included. `proxy` is `basic`, `enhanced` or `auto`.
  - Firecrawl reads robots.txt "before it crawls a site" under the token `FirecrawlAgent`. The documentation does not say this covers a single-page scrape, and says the token is not necessarily the User-Agent header sent.
  - A self-hosted service is addressed by its own URL and may need no key.
- The operator's service is self-hosted (answered 2026-11-15). The pipeline reaches it on the private network; it is not served publicly. What a self-hosted service lacks compared with the cloud one (the assistant's unchecked recollection of Firecrawl's self-hosting guide is that the stealth proxy engine is cloud-only) is confirmed in task 1.1, not assumed here.
- Guardrails that bind here: robots.txt and a contact User-Agent; article text kept nowhere, logs and caches included; no model IDs in code; no fallback paths; no live requests in tests.

## Goals / Non-Goals

**Goals:**

- One place asks for a page, and it asks the reader.
- Callers of `ArticleRetriever` do not change.
- The text the model and the statement check see is plain text, as now.

**Non-Goals:**

- Using Firecrawl's crawl, search, batch or extraction endpoints.
- A Firecrawl SDK dependency.
- Changing the outlet pacing in `backfill/link_read.py`: the outlet's allowance is claimed before the retriever is called, and still is.

## Decisions

### 1. The reader replaces the page fetch inside `ArticleRetriever`

`_page()` and the fetch in `probe()` ask the reader. `retrieve()`, `probe()`, `allowed()`, `rules_unknown()`, `crawl_delay()` and `json()` keep their signatures, so no caller changes.

*Alternative:* a new reader class that callers choose. Rejected: five callers would each decide, and a choice between two fetch paths is the fallback the operator's rule forbids.

### 2. robots.txt, the snapshot lookup and platform JSON stay direct

Three kinds of request are not page fetches and keep using `httpx` with the contact User-Agent: an outlet's robots.txt, the Internet Archive's availability API, and a platform's own interface for software (`json()`, used for posts). The first must be the pipeline's own reading, since the pipeline answers for it. The other two are APIs that return JSON, which a page renderer adds nothing to.

The snapshot page itself, once found, is fetched through the reader like any page.

### 3. Ask over HTTP with the existing client, not the SDK

One `POST` to `{FIRECRAWL_API_URL}/v2/scrape`, sent with the `httpx` client the retriever already holds. The existing transport seam then covers the reader in tests, and no dependency is added.

*Alternative:* the `firecrawl` Python package. Rejected: it adds a dependency and a second seam for one endpoint.

### 4. Request `rawHtml` and `html`; never `markdown` or a model format

- `rawHtml` goes to `read_page` for what the page says about itself: meta tags, structured data, linked papers and registry numbers. Those live in the head and in links that a cleaned copy drops.
- `html` (main content only) goes through the same text collector and becomes `Retrieved.text` and `Page.text`.

Markdown is not requested. The statement check compares a proposed statement with the text word for word, and link and emphasis marks inside a sentence would make true statements fail the check.

`summary`, `json`, `screenshot` and `changeTracking` are never requested. A test asserts the formats sent are exactly these two.

To confirm in task 1.2: that `rawHtml` for a page drawn by scripts is the page after rendering. If it is the HTML as first served, metadata is read from `html` and this decision is revised before any code is written.

### 5. Every request: fresh, unstored, identified, basic proxy

Each request carries `maxAge: 0`, `storeInCache: false`, `proxy: "basic"` and `headers: {"User-Agent": <contact User-Agent>}`. These are constants in code, not settings: a setting would let a run quietly turn caching or stealth on.

To confirm in task 1.2: that the outlet receives the contact User-Agent when a page is rendered in a browser, by reading a request-echo page through the reader. If the header is not honoured, the change stops there and the operator decides.

### 6. What the reader's answers mean

| The reader's answer | What the pipeline does |
| --- | --- |
| Page returned, outlet's status 200 | The page is read |
| Page returned, outlet's status not 200 | As today for that status: not retrieved, snapshot looked for; `probe()` reports the status |
| Too-many-requests from the reader | `SourcePaused` for the time stated: the run ends, the record stays due |
| Not configured | The command refuses, as it does with no contact address |
| No answer, a server error, or a refused key | A new `ReaderUnavailable`, a `SourceStop`: the run ends, the record stays due, no attempt counted |

The outlet's own status is taken from `metadata.statusCode` in the answer. A failure of the reader is never recorded as the outlet's failure, so `docs/outlets.md` and the failed-address register keep describing outlets.

### 7. Configuration

`FIRECRAWL_API_URL` (required to read any page) and `FIRECRAWL_API_KEY` (optional: a self-hosted service may need none). Both in `Settings` and `.env.example`. No default address: the service is the operator's own, and pointing the pipeline at the cloud service instead must be a deliberate choice because of decision 8.

### 8. Retention on the reader's side is checked, not assumed

`storeInCache: false` covers Firecrawl's result cache. On the operator's self-hosted service it does not cover the job queue, which holds a finished job's result for a time, or the containers' logs. Task 1.1 reads the service's own configuration and records in `docs/sources.md` what each keeps, and for how long, and sets them so that a page does not outlive its read. A reader that keeps article text longer than a read takes fails the guardrail and blocks the change.

## Risks / Trade-offs

- [The reader is a single point of failure: no reader, no reads] → Accepted, and deliberate. The run stops with a clear reason and records stay due (decision 6).
- [A rendered read is slower than a plain request] → The outlet interval already spaces reads; the request timeout is raised to cover rendering. Measured in task 4.2.
- [The contact User-Agent may not reach the outlet from a rendered fetch] → Checked before any code (decision 5).
- [Firecrawl applies its own robots.txt reading and may refuse a page the pipeline's rules allow] → Counted as the outlet failing with the reader's reason; visible per outlet in the report.
- [Content hashes change for articles read again] → Stated in the proposal. Nothing compares a new hash with an old one to decide whether to read; task 3.4 verifies that.
- [Page furniture removed too eagerly drops part of an article] → The before and after outlet report shows Read falling for any outlet where this happens.
- [The pipeline and `site/worker` now read differently] → Stated in the proposal; a later change.

## Migration Plan

1. Record the reader's deployment and retention in `docs/sources.md` (task 1.1) and run the two checks against the running service (task 1.2).
2. Run `thenwhat outlets` on main and keep the report as the baseline.
3. Land the change; run `thenwhat outlets` again; compare.
4. Rollback is reverting the commit. No data migration either way.

## Open Questions

For the operator. None changes this change's specs or tasks; each would be its own change.

- **The archived-snapshot step.** It is a second source used when the first fails, already in `claim-extraction` and `lead-reading`. Keep it, or remove it so that an unretrievable article is simply recorded as such?
- **Stealth proxies.** medicalxpress.com answers the identified client with 403. Firecrawl's `enhanced` proxy would probably read it, by not identifying the client. This change forbids it. Is that the standing answer?
- **Platform terms.** Nothing here reads X, Reddit, LinkedIn, Meta or Telegram. Confirm that a capable reader does not reopen the decisions in `docs/sources.md`.
