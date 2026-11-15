# Design

## Context

See `proposal.md` for why. What shapes the approach:

- `extract/retrieve.py` holds the only page fetch in the pipeline. `ArticleRetriever` reads robots.txt, fetches the page with `httpx`, looks for an archived snapshot, and raises `PasteNeeded`. `backfill/link_read.py` asks it whether an address is allowed, whether the rules are unknown and what crawl delay applies, then claims a per-outlet allowance before the fetch. `probe()` does a single fetch for `thenwhat outlets`.
- `extract/page.py` turns HTML into a `Page`: plain text, headline, date, DOIs and registry numbers. Reported statements are checked word for word against that plain text.
- The retriever takes an `httpx` transport, which is the seam every retrieval test uses.
- The operator's decisions of 2026-11-15, in the order given:
  - The reader is a self-hosted Firecrawl service on the home network, reachable over Tailscale (the pipeline's route) and through a Cloudflare Tunnel (for a Worker).
  - The project is not commercial and no money is spent on hosting. The public lookup may depend on the home reader (`docs/adr/0005`).
  - Rules about individual sites are delegated to the service, research papers included. Where an address is not allowed, a site is rate limited, or another limit applies, the service says so in its answer and the project handles the answer. Code and decisions in this project that handle particular addresses directly are to be pruned: "an opportunity to simplify things".
  - The service is never called from a reader's browser or the extension; the project's backend makes the calls.
  - When the home machine is down, readers are shown a service-overloaded error.
- Read from Firecrawl's documentation on 2026-11-15, not tried against a running service: `POST /v2/scrape` returns `markdown`, `html` (page furniture removed) or `rawHtml`; results are cached for two days unless `maxAge: 0` and `storeInCache: false`; `headers` can set the User-Agent; robots.txt is read "before it crawls a site", with no statement that this covers a single-page scrape.
- The operator's guide to the service, given on 2026-11-15, is summarised under "The service as it is today". It is the standard Firecrawl v2 interface with a router in front of single scrapes. It has no answer of the kinds this design needs ("not allowed, because", "not now, until"), and its router reads platforms this project has decided not to read. So the service has work to do before this change can be applied.
- Guardrails that bind here: article text kept nowhere; no model IDs in code; no fallback paths; no live requests in tests. The guardrail on robots.txt, rate limits and the contact User-Agent is changed by the operator's decision (decision 6).

## The service as it is today

From the operator's guide (2026-11-15). Addresses and the key are not written here or anywhere in the repository; they are settings.

- **Interface:** Firecrawl v2 (`/v2/scrape`, `/v2/batch/scrape`, `/v2/crawl`, `/v2/map`). A bearer key is required on both routes; without it the answer is 401.
- **Answers:** `success` and `data` with `markdown`, other formats, and `metadata`; or an error status. 5xx, timeouts and connection errors mean the machine is down or busy. A 500 on a Reddit address means Reddit is throttling the machine.
- **Router on single scrapes:** X, Bluesky, YouTube (with captions), Facebook, Instagram, Threads, TikTok and Reddit are read by special routes, named in `metadata.socialRouter`, which return markdown and metadata only. Post routes return the author. `skipSocialRouter` bypasses the router. When a special route fails the router silently falls back to a normal scrape.
- **Model features:** structured extraction and image descriptions, run on the server with the operator's model credits, only when asked for.
- **Limits:** one small machine; at most 4 requests in flight; allow 120 seconds.
- **Warned in the guide:** success does not mean good content. A login wall, a challenge page or empty markdown can come back as success.

What this change needs and the service does not yet give:

| Needed | Today | Consequence |
| --- | --- | --- |
| `not_allowed`, with a reason | No such answer | Nothing is blocked by this: whether to refuse anything is the service's to decide (decision 6). The pipeline understands the answer when the service gives it |
| A decision on the platforms `docs/sources.md` lists as not read | The router reads X, Reddit, Facebook, Instagram, Threads and YouTube captions | Decided by the operator on 2026-11-15: allowed, and how each is read is the service's responsibility (decision 9) |
| `not_now`, with when | No such answer; a throttled site shows as a 500 | A site's limit cannot be told from the machine failing, so a throttled site would stop a whole run |
| The site's status for a page not served | `metadata.statusCode` on a normal scrape (Firecrawl's field; to confirm) | Likely met |
| The client identified to the site | Not stated | The service's to decide (decision 6) |
| Nothing kept | Not stated; Firecrawl caches for two days by default | The pipeline sends `maxAge: 0` and `storeInCache: false`; the service's queue and logs are checked |
| A post's author never returned | Post routes return the author | Matters for the posts prune, not for this change |
| No silent second route | The router falls back to a normal scrape when a route fails | A fallback of the kind the operator's rule asks to be flagged. It decides nothing in this change, which sends no post to the router |

The one thing this project needs of every request is that nothing is kept, and it asks for that itself with `maxAge: 0` and `storeInCache: false`. So no rule set by name is needed in the service.

## Goals / Non-Goals

**Goals:**

- One place asks for a page, and it asks the reader.
- No rule about an individual site for fetching is left in the pipeline.
- The pipeline acts on four answers and one failure, and nothing else.
- The text the model and the statement check see is plain text, as now.

**Non-Goals:**

- Deciding how the service implements its rules. This design states what the pipeline needs from its answers.
- Moving `site/worker` or the extension. Listed under "Next prunes".
- A Firecrawl SDK dependency.

## Decisions

### 1. The reader replaces the retriever's insides; its rule questions are removed

`ArticleRetriever.retrieve()` and `probe()` ask the reader. `allowed()`, `rules_unknown()`, `crawl_delay()`, the robots cache and the snapshot lookup are deleted. `link_read.py` stops asking those three questions and stops claiming an `outlet:` allowance; it calls `retrieve()` and acts on the outcome.

`json()` stays for now: `cli/lookup.py` passes it to `extract/post.py`. It goes with the posts prune.

*Alternative considered and dropped:* keeping the pipeline's own robots.txt reading in front of the reader, as the first draft of this change did. Two readings of one site's rules can disagree, and the operator's decision is that the rules live in one place.

### 2. The reader's answer: four outcomes

What the pipeline needs, whatever the wire format:

| Outcome | Carries | The pipeline |
| --- | --- | --- |
| `read` | the page's HTML as drawn, its main content, the final address, an archive address if the copy came from one | reads it |
| `not_allowed` | a reason in words for the operator, whatever the service's reason is | extraction: `PasteNeeded` with the reason. Lead: cannot be read, with the reason, not tried again. Outlets report: refused |
| `not_now` | when the site may be asked again, and why (rate limit, rules could not be read) | lead stays due, no attempt counted, the run goes on with other sites. Extraction: tells the operator when |
| `not_served` | the site's status | as today for a page that could not be retrieved; the outlets report shows the status |

Anything else, or no answer, is the reader failing (decision 4).

On the wire, as far as the guide settles it: the request is `POST /v2/scrape` with `formats: ["rawHtml", "html"]`, `maxAge: 0`, `storeInCache: false`. `read` is `success` with `metadata.statusCode` 200. `not_served` is `success` with another status. `not_allowed` and `not_now` have no form in the service yet. The pipeline will understand this one, proposed to the service: `success: false` with `code: "NOT_ALLOWED"` or `code: "NOT_NOW"`, a `reason` in words, and for `NOT_NOW` a `retryAfter` in seconds. A refusal is known by its code, whatever HTTP status it comes with. When the copy it returns came from an archive, the service says so as `metadata.archiveUrl` (added when the change was applied, 2026-11-15; offered with the rest in task 1.1). Until the service sends them, a site it will not or cannot read shows as `not_served` or as the reader failing. The pipeline never asks for `json`, `summary` or `describeImages`, and never uses batch or crawl.

Success is not trusted as good content. The pipeline keeps its own checks on what came back: a body under the existing length is thin, and a page with no headline or date is not read. Those are checks on a page, not rules about a site.

`not_now` replaces three things the pipeline did itself: the per-outlet interval, the crawl delay, and the retry of an outlet whose rules could not be read.

### 3. Text is plain; metadata comes from the page as drawn

The page as drawn goes to `read_page` for what the page says about itself (meta tags, structured data, links). The main content, as HTML, goes through the same text collector and becomes the text the model and the statement check see.

Markdown is not used for the text. The statement check compares a proposed statement with the text word for word, and link and emphasis marks inside a sentence would make true statements fail. If the service offers only markdown, that is settled with the operator in task 1.1 before any code, not worked around.

### 4. The reader failing is not a site failing

Not configured: the command refuses, as it does with no contact address. Unreachable, a server error, or the service saying it is itself overloaded: `ReaderUnavailable`, a `SourceStop`. The run ends, records stay due, no attempt is counted. Nothing is recorded against an outlet, so `docs/outlets.md` and the failed-address register keep describing sites.

### 5. One allowance, for the reader

The read step's source becomes `reader`, with one configured allowance, so `source-allowances` still holds: the plan shows it, and a missing allowance refuses the run. The `outlet:` sources and `outlet_source` are removed. The allowance is a ceiling on how hard the pipeline drives the home machine; spacing per site is the reader's. The machine takes at most 4 requests in flight and is shared with other projects, so the pipeline's reads side by side are capped at 2 by a setting, and the request timeout is 120 seconds.

### 6. Whether and how a site is asked is the service's decision

The operator decided on 2026-11-15, asked whether robots.txt on ordinary news sites should also be left to the service: "Service decides". With decision 9 this means the project no longer holds, checks or promises anything about robots.txt, crawl delays, per-site rate limits or how the client presents itself to a site. The service does what its operator has set it to do, and answers `not_allowed` or `not_now` where it chooses to. Recorded in `docs/adr/0006`.

The assistant's reading, not the operator's words: "service decides" covers the contact User-Agent and proxies too, since they are part of how a site is asked. The pipeline still sends its contact User-Agent to the registries and literature indexes it asks directly; nothing about `sources/` changes.

What stays the project's own, because it is about what the project keeps and not about fetching: no article or post text is kept. That is checked against the running service, by hand, with the dated result in the reader's entry in `docs/sources.md`:

- a second read of one page is not served from a kept copy;
- the service's queue and logs hold no page text after the answer;
- a page drawn by scripts comes back as drawn.

The check is repeated when the service's version or configuration changes.

What changes outside the code, in task 4.4: the guardrail in `CLAUDE.md` and in `openspec/config.yaml`, the README's lines on robots.txt, and the outlet entry in `docs/sources.md` that says "robots.txt decides". The site's wording that mentions robots.txt (`site/src/lib/live-lookup.mjs`) belongs to the Worker's change.

### 7. Configuration

`FIRECRAWL_API_URL` (the Tailscale address; required to read any page) and `FIRECRAWL_API_KEY`. No default address. The pipeline does not use the tunnel.

### 8. The tunnel route is closed to everyone but the project's backend

A reader that answers anyone is an open proxy: a stranger could fetch any page through it, in the project's name and from the operator's network. As built, both routes require the service's bearer key and answer 401 without it, and the service's admin paths answer 404. That closes the route. A reader's browser and the extension never hold the key and never call the reader. Recorded in `docs/adr/0005`; verified in task 1.2 by an unauthenticated request being refused.

Not in place, and the operator's to weigh: a check at Cloudflare before a request reaches the home machine (an Access service token). With the key alone, every guess at the key and every flood of requests arrives at the machine itself.

### 9. Social and video platforms are the reader's to handle

The operator decided on 2026-11-15: "allow X, Reddit, Meta, Youtube and others, it'll be the responsibility of the service to decide how to handle these, in worst case we may get markdown based off open graph cards".

This replaces the "Not read" entries of 2026-11-12 in `docs/sources.md` ("Platforms whose posts are not read"). That table is rewritten in task 1.4 to say what was found about each platform's terms and robots.txt, that the operator decided to read them through the reader, and the date. As with the Reddit dumps entry there, it is the operator's decision and not a legal reading; what the 2026-11-12 reading found stays on the page for whoever revisits it.

What the decision does not change, because these are the project's rules about what it keeps and shows, not about fetching:

- A post's author is never kept, logged or exported. The reader's post routes return the author; the pipeline drops it on arrival.
- A post's text is treated as article text: held while it is read, kept nowhere, never displayed.
- A post is a way to an article and to the claim it reports. It is never itself evidence, and a registered trial found through a post is never presented as a treatment option.

No post is sent to the reader by this change. The decision takes effect with the posts prune.

## Next prunes

Not in this change's tasks. Each waits for the reader's answer to cover it, and each is its own change.

| What goes | Where | What the reader's answer needs |
| --- | --- | --- |
| Reading posts on Bluesky, Hacker News, Mastodon; `json()` | `extract/post.py` (172 lines), `cli/lookup.py` | a post's text and the links in it; the pipeline drops the author (decision 9) |
| Publisher and PubMed address patterns, DOI link patterns | `extract/page.py` | the DOIs, PubMed numbers and registry numbers a page links to |
| Whatever the pipeline does of its own to get a paper's abstract from a publisher's page | to be listed when that change is proposed | a paper's abstract as markdown, by its DOI or address (operator, 2026-11-15) |
| The Worker's page, post, short-link and screenshot readers | `site/worker/page.mjs`, `post.mjs`, `short.mjs`, `article.mjs`, `visual.mjs` | the same answers, asked by the Worker through the tunnel; a down reader shown as service overloaded |
| The extension's host lists and its `t.co` reading | `extension/src/open-page.js`, `short-links.js` | to be weighed: the extension reads what the reader's own browser already shows, which the service cannot see |

On abstracts, three things for that change to settle, none decided here:

- A paper is an evidence event, and every evidence event stores the raw payload and fetch time of the index that reported it (Europe PMC, OpenAlex, Crossref). An abstract read from a page is not that payload. It can add to a paper's record; it cannot stand in for the index's record.
- The guide to the service says some research publishers answer with cookie or bot walls. An abstract that did not come back is an empty state, shown as such, not filled from somewhere else.
- What is kept of an abstract. Today recorded fixtures have abstracts replaced, and a model reads a paper's record into fixed codes (ADR 0003). Whether an abstract's markdown is stored, or held only while it is read like article text, is the operator's to decide.

Kept, because they are not rules about fetching: `backfill/address.py` and `site/src/lib/article-key.mjs` (when two addresses are one article), `backfill/outlet_kinds.py` (which outlets are listed, and their names, which no model and no domain may supply), `backfill/link_readers.py` (reading bulk files), and `sources/` (registry and literature APIs, whose raw payloads are stored with every evidence event).

## Risks / Trade-offs

- [The project no longer promises that robots.txt is followed] → The operator's decision (ADR 0006). No public page may go on saying it is; task 4.4 finds and corrects every such line.
- [The reader is a single point of failure] → Accepted by the operator. The run stops with a clear reason and records stay due.
- [A `not_now` for a busy site could leave leads due for a long time] → They cost nothing while due; the funnel report counts them.
- [A site the pipeline refused before is now read, because the service does not refuse it] → Intended by the operator's decision. Task 5.2 lists every outlet that moves from Refused to Read, for the operator to see before merging.
- [A throttled site shows as the reader failing and stops a run, until the service answers `not_now`] → Safe: records stay due. Proposed to the service in decision 2.
- [A challenge or login page comes back as success and is read as an article] → The pipeline's own thin, headline and date checks stay. The outlets report before and after shows any outlet whose Read count rises on pages that are not articles; task 5.2 samples them.
- [The tunnel exposes the reader] → Decision 8.
- [Content hashes change for articles read again] → Nothing compares a new hash with an old one to decide whether to read; task 3.5 verifies that.
- [Main content cut too eagerly drops part of an article] → The before and after outlets report shows Read falling for any outlet where this happens.

## Migration Plan

1. Offer the answer format to the service and run the keep-nothing check (tasks 1.1, 1.2).
2. Run `thenwhat outlets` on main and keep the report as the baseline.
3. Land the change. Remove the `outlet:` rows' use; the allowance-use table needs no migration, old rows are simply no longer read.
4. Run `thenwhat outlets` again and compare.
5. Rollback is reverting the commit. No data migration either way.

## Open Questions

- None that changes this change. Whether the service uses stealth proxies, for medicalxpress.com or any site, is now the service's (decision 6).

## Live integration checked on 2026-11-15

The service adopted `NOT_NOW` with `reason` and `retryAfter` for its host-cooldown gate and target engine exhaustion. A site challenge is represented as a not-served status. `NOT_ALLOWED` and `metadata.archiveUrl` remain supported client fields for future service policies and full archived pages. Single article reads request full HTML and receive no preview-card substitution. Both routes accepted the bearer key and refused unauthenticated requests. The pipeline continues to use Tailscale.

The retention probe passed for the pipeline request shape. Changed source values proved a fresh fetch on repeated reads. The unique request left no queue record or matching page content in inspected Redis values and service logs. Immediate JavaScript rendering passed. A delayed-render fixture returned a shell, which the main-body check rejects before a model call. The dated details are in `docs/sources.md`.

Review corrections make the supplied main HTML authoritative through `Page.as_text()`, reject thin bodies before extraction, require headline and date for outlet Read counts, reject malformed retry times, and share deferred exclusions across workers in a run.

The proxy previously fell back directly to the upstream API when the router restarted. That skipped the router response contract. Single scrapes now require the router. An unavailable router is reported as unavailable, allowing the pipeline to leave work due. Target engine exhaustion is a temporary `NOT_NOW` answer with a 60-second retry interval.

## Outlet acceptance result on 2026-11-15

The final run finished 400 tracked articles in 303.49 seconds, with at most two HTTP requests in flight. One article was added by another session after the 399-article baseline. Over the matching 399 URLs, Read was 329 versus 337, Thin 27 versus 0, Refused 0 versus 4, and failed 43 versus 58. The new article was Read, making the current report 330 Read. Elapsed wall time per checked article was 0.759 seconds. This is throughput with concurrency, not the latency of one HTTP request. No per-request mean latency was recorded.

The requested no-regression and lower-Thin conditions were not met. The stricter checks require enough main text and a usable publication date, and a detected challenge is no longer counted as an article. The operator was told of these results before merge. The regenerated report records the observed results.

Both previously refused outlets became readable, QUB (1) and The Sun (3). Other outlets with higher Read counts were AP (0 to 2), Bloomberg (0 to 2), Fierce Biotech (0 to 2), Fierce Pharma (0 to 1), Financial Times (0 to 4), The Atlantic (0 to 5), US News (0 to 1), and Washington Post (0 to 3). Dana-Farber's one newly added article also read successfully.

Outlets whose Read counts fell were au.news.yahoo.com (1 to 0), bbc.co.uk (20 to 19), dailymail.co.uk (3 to 0), dailymail.com (7 to 0), eurekalert.org (5 to 0), idw-online.de (1 to 0), kyoto-u.ac.jp (1 to 0), medscape.com (1 to 0), news.yahoo.com (2 to 0), nottingham.ac.uk (1 to 0), nz.news.yahoo.com (1 to 0), okayama-u.ac.jp (1 to 0), plymouth.ac.uk (1 to 0), qmul.ac.uk (1 to 0), riken.jp (1 to 0), sg.news.yahoo.com (2 to 0), tohoku.ac.jp (1 to 0), and usatoday.com (1 to 0).

Repeat inspection used up to three newly readable articles per outlet, or all when fewer were available, and recorded headline, publication date, body length and paragraph count without retaining article text. AP, Fierce Biotech, Fierce Pharma, Financial Times, QUB, The Atlantic, The Sun, US News, Dana-Farber and Washington Post passed those mechanical checks. Washington Post bodies were only 528–744 characters, so completeness is uncertain despite meeting the existing 500-character threshold. Bloomberg's two pages failed on repeat with no body or metadata. Its initial two Read results are therefore not a reliable gain.

## The outlets report splits Thin from No date (2026-11-15, after merge)

The acceptance run above counted a page as Thin when its main text was short *or* it had no headline or readable date. Over the 399 baseline URLs, 13 of the 21 pages that moved from Read to Thin had 1,500 to 10,000 characters of main text and had no readable date in the baseline either (EurekAlert 5, idw-online, Kyoto, Nottingham, Okayama, Plymouth, QMUL, RIKEN, Tohoku, one BBC video page). That was a change in what Thin counts, not a loss of reading. The reading step refused undated pages before and after the change.

The report now has two columns: **Thin**, main text under 500 characters, as the requirement "Outlets are measured through the reader" uses the word; and **No date**, enough text but no headline or readable date, which a lead's read refuses. A rerun on 2026-11-15 over the matching 399 URLs gave Read 333 (baseline 337), Thin 5 (0), No date 18, Refused 0 (4) and failed 43 (58). The five Thin pages are Washington Post paywall stubs, which the baseline could not fetch at all.

The reads still lost against the baseline, and where each belongs:

| Pages | What happens | Whose to fix |
| --- | --- | --- |
| Daily Mail (10) | the site answers 403 to the reader | the service (ADR 0006): how the site is asked |
| Yahoo (2 on this run, up to 6 on others) | an intermittent redirect to `consent.yahoo.com` ("Your privacy choices"); the page has no date, so a lead hitting it ends as cannot be read although a later read would succeed | the service: how a consent wall is answered |
| USA Today (1) | the site answers 402 | the service |
| Medscape (1) | its date is given as `9/6/2026`, which `published_day` does not read; day and month order is not guessed | open |
| QMUL (1) | the reader's main content is 768 characters against 4,309 for the page; it also has no date | the service: its main-content cut |
