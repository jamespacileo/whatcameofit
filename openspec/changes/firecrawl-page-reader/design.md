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
- Read from Firecrawl's documentation on 2026-11-15, not tried against a running service: `POST /v2/scrape` returns `markdown`, `html` (page furniture removed) or `rawHtml`; results are cached for two days unless `maxAge: 0` and `storeInCache: false`; `headers` can set the User-Agent; robots.txt is read "before it crawls a site", with no statement that this covers a single-page scrape. Stock Firecrawl has no answer of the kinds this design needs ("not allowed, because", "not now, until"), so the operator's service is assumed to add them. Its interface has not been seen.
- Guardrails that bind here, wherever they are enforced: robots.txt and published rate limits; a contact User-Agent; article text kept nowhere; no model IDs in code; no fallback paths; no live requests in tests.

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
| `not_allowed` | a reason code and words for the operator (robots.txt, platform terms, the service's own list) | extraction: `PasteNeeded` with the reason. Lead: cannot be read, with the reason, not tried again. Outlets report: refused |
| `not_now` | when the site may be asked again, and why (rate limit, rules could not be read) | lead stays due, no attempt counted, the run goes on with other sites. Extraction: tells the operator when |
| `not_served` | the site's status | as today for a page that could not be retrieved; the outlets report shows the status |

Anything else, or no answer, is the reader failing (decision 4).

`not_now` replaces three things the pipeline did itself: the per-outlet interval, the crawl delay, and the retry of an outlet whose rules could not be read.

### 3. Text is plain; metadata comes from the page as drawn

The page as drawn goes to `read_page` for what the page says about itself (meta tags, structured data, links). The main content, as HTML, goes through the same text collector and becomes the text the model and the statement check see.

Markdown is not used for the text. The statement check compares a proposed statement with the text word for word, and link and emphasis marks inside a sentence would make true statements fail. If the service offers only markdown, that is settled with the operator in task 1.1 before any code, not worked around.

### 4. The reader failing is not a site failing

Not configured: the command refuses, as it does with no contact address. Unreachable, a server error, or the service saying it is itself overloaded: `ReaderUnavailable`, a `SourceStop`. The run ends, records stay due, no attempt is counted. Nothing is recorded against an outlet, so `docs/outlets.md` and the failed-address register keep describing sites.

### 5. One allowance, for the reader

The read step's source becomes `reader`, with one configured allowance, so `source-allowances` still holds: the plan shows it, and a missing allowance refuses the run. The `outlet:` sources and `outlet_source` are removed. The allowance is a ceiling on how hard the pipeline drives the home machine; spacing per site is the reader's.

### 6. The guardrails become a conformance check

The pipeline can no longer show by its own code that robots.txt was respected or the client identified. So the reader is checked, by hand, against the running service, and the dated result is written into its entry in `docs/sources.md`:

- an address a site's robots.txt disallows is answered `not_allowed`;
- every platform in "Platforms whose posts are not read" (X, Reddit, Facebook, Instagram, Threads, LinkedIn, Telegram, and YouTube by address) is answered `not_allowed`, with no request sent to it;
- a request-echo page shows the contact User-Agent, and no stealth proxy is in use;
- a second read of one page is not served from a kept copy, and the service's queue and logs hold no page text after the answer;
- a page drawn by scripts comes back as drawn.

The check is repeated when the service's rules or version change. `docs/sources.md` stays the record of *why* each platform is or is not read; the service is where it is enforced. A capable reader does not reopen those decisions.

### 7. Configuration

`FIRECRAWL_API_URL` (the Tailscale address; required to read any page) and `FIRECRAWL_API_KEY`. No default address. The pipeline does not use the tunnel.

### 8. The tunnel route is closed to everyone but the project's backend

A reader that answers anyone is an open proxy: a stranger could fetch any page through it, in the project's name and from the operator's network. The tunnel's hostname refuses every request without a credential only the project's Worker holds, checked at Cloudflare (an Access service token), with the service's key as a second check. A reader's browser and the extension never hold that credential and never call the reader. Recorded in `docs/adr/0005`; verified in task 1.2 by an unauthenticated request being refused.

## Next prunes

Not in this change's tasks. Each waits for the reader's answer to cover it, and each is its own change.

| What goes | Where | What the reader's answer needs |
| --- | --- | --- |
| Reading posts on Bluesky, Hacker News, Mastodon; `json()` | `extract/post.py` (172 lines), `cli/lookup.py` | a post's text and the links in it, never its author |
| Publisher and PubMed address patterns, DOI link patterns | `extract/page.py` | the DOIs, PubMed numbers and registry numbers a page links to |
| The Worker's page, post, short-link and screenshot readers | `site/worker/page.mjs`, `post.mjs`, `short.mjs`, `article.mjs`, `visual.mjs` | the same answers, asked by the Worker through the tunnel; a down reader shown as service overloaded |
| The extension's host lists and its `t.co` reading | `extension/src/open-page.js`, `short-links.js` | to be weighed: the extension reads what the reader's own browser already shows, which the service cannot see |

Kept, because they are not rules about fetching: `backfill/address.py` and `site/src/lib/article-key.mjs` (when two addresses are one article), `backfill/outlet_kinds.py` (which outlets are listed, and their names, which no model and no domain may supply), `backfill/link_readers.py` (reading bulk files), and `sources/` (registry and literature APIs, whose raw payloads are stored with every evidence event).

## Risks / Trade-offs

- [The project's guardrails now rest on a service this repository does not contain] → Decision 6: a dated check in `docs/sources.md`, repeated on change. The pipeline's tests cover its handling of each answer, not the service's rules.
- [The reader is a single point of failure] → Accepted by the operator. The run stops with a clear reason and records stay due.
- [A `not_now` for a busy site could leave leads due for a long time] → They cost nothing while due; the funnel report counts them.
- [The service's interface is unseen, so the wire format may not carry all four outcomes] → Task 1.1 settles it before any code. If an outcome cannot be told apart, the change stops there.
- [The tunnel exposes the reader] → Decision 8.
- [Content hashes change for articles read again] → Nothing compares a new hash with an old one to decide whether to read; task 3.5 verifies that.
- [Main content cut too eagerly drops part of an article] → The before and after outlets report shows Read falling for any outlet where this happens.

## Migration Plan

1. Agree the answer format with the service and run the conformance check (tasks 1.1, 1.2).
2. Run `thenwhat outlets` on main and keep the report as the baseline.
3. Land the change. Remove the `outlet:` rows' use; the allowance-use table needs no migration, old rows are simply no longer read.
4. Run `thenwhat outlets` again and compare.
5. Rollback is reverting the commit. No data migration either way.

## Open Questions

- **Stealth proxies.** medicalxpress.com answers the identified client with 403. This change's conformance check forbids hiding the client, so it stays unread. Whether that is the standing answer is the operator's; it changes nothing in this change.
