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
- Guardrails that bind here, wherever they are enforced: robots.txt and published rate limits; a contact User-Agent; article text kept nowhere; no model IDs in code; no fallback paths; no live requests in tests.

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
| `not_allowed`, with a reason | No such answer. Nothing in the guide says robots.txt is read on a single scrape | The pipeline's robots.txt reading cannot be pruned until the service refuses what robots.txt disallows and says so |
| A decision on the platforms `docs/sources.md` lists as not read | The router reads X, Reddit, Facebook, Instagram, Threads and YouTube captions | Decided by the operator on 2026-11-15: allowed, and how each is read is the service's responsibility (decision 9) |
| `not_now`, with when | No such answer; a throttled site shows as a 500 | A site's limit cannot be told from the machine failing, so a throttled site would stop a whole run |
| The site's status for a page not served | `metadata.statusCode` on a normal scrape (Firecrawl's field; to confirm) | Likely met |
| The client identified to the site | Not stated | To check; `headers` can carry the contact User-Agent if the service passes it on |
| Nothing kept | Not stated; Firecrawl caches for two days by default | The pipeline sends `maxAge: 0` and `storeInCache: false`; the service's queue and logs are checked |
| A post's author never returned | Post routes return the author | Matters for the posts prune, not for this change |
| No silent second route | The router falls back to a normal scrape when a route fails | A fallback of the kind the operator's rule asks to be flagged. It decides nothing in this change, which sends no post to the router |

The service is shared with the operator's other projects, which may not want what this project needs (robots.txt respected on news sites, nothing cached). So what this project needs is best held in the service as a named set of rules that a caller asks for by name. The pipeline then names its rule set and still holds no rule about any site.

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

On the wire, as far as the guide settles it: the request is `POST /v2/scrape` with `formats: ["rawHtml", "html"]`, `maxAge: 0`, `storeInCache: false`, and the name of this project's rule set once the service has one. `read` is `success` with `metadata.statusCode` 200. `not_served` is `success` with another status. `not_allowed` and `not_now` have no form yet; task 1.1 is the service gaining them. The pipeline never asks for `json`, `summary` or `describeImages`, and never uses batch or crawl.

Success is not trusted as good content. The pipeline keeps its own checks on what came back: a body under the existing length is thin, and a page with no headline or date is not read. Those are checks on a page, not rules about a site.

`not_now` replaces three things the pipeline did itself: the per-outlet interval, the crawl delay, and the retry of an outlet whose rules could not be read.

### 3. Text is plain; metadata comes from the page as drawn

The page as drawn goes to `read_page` for what the page says about itself (meta tags, structured data, links). The main content, as HTML, goes through the same text collector and becomes the text the model and the statement check see.

Markdown is not used for the text. The statement check compares a proposed statement with the text word for word, and link and emphasis marks inside a sentence would make true statements fail. If the service offers only markdown, that is settled with the operator in task 1.1 before any code, not worked around.

### 4. The reader failing is not a site failing

Not configured: the command refuses, as it does with no contact address. Unreachable, a server error, or the service saying it is itself overloaded: `ReaderUnavailable`, a `SourceStop`. The run ends, records stay due, no attempt is counted. Nothing is recorded against an outlet, so `docs/outlets.md` and the failed-address register keep describing sites.

### 5. One allowance, for the reader

The read step's source becomes `reader`, with one configured allowance, so `source-allowances` still holds: the plan shows it, and a missing allowance refuses the run. The `outlet:` sources and `outlet_source` are removed. The allowance is a ceiling on how hard the pipeline drives the home machine; spacing per site is the reader's. The machine takes at most 4 requests in flight and is shared with other projects, so the pipeline's reads side by side are capped at 2 by a setting, and the request timeout is 120 seconds.

### 6. The guardrails become a conformance check

The pipeline can no longer show by its own code that robots.txt was respected or the client identified. So the reader is checked, by hand, against the running service, and the dated result is written into its entry in `docs/sources.md`:

- an address a site's robots.txt disallows is answered `not_allowed`;
- a request-echo page shows the contact User-Agent, and no stealth proxy is in use;
- a second read of one page is not served from a kept copy, and the service's queue and logs hold no page text after the answer;
- a page drawn by scripts comes back as drawn.

The check is repeated when the service's rules or version change. `docs/sources.md` stays the record of what was decided about each source and when; the service is where it is carried out.

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
| The Worker's page, post, short-link and screenshot readers | `site/worker/page.mjs`, `post.mjs`, `short.mjs`, `article.mjs`, `visual.mjs` | the same answers, asked by the Worker through the tunnel; a down reader shown as service overloaded |
| The extension's host lists and its `t.co` reading | `extension/src/open-page.js`, `short-links.js` | to be weighed: the extension reads what the reader's own browser already shows, which the service cannot see |

Kept, because they are not rules about fetching: `backfill/address.py` and `site/src/lib/article-key.mjs` (when two addresses are one article), `backfill/outlet_kinds.py` (which outlets are listed, and their names, which no model and no domain may supply), `backfill/link_readers.py` (reading bulk files), and `sources/` (registry and literature APIs, whose raw payloads are stored with every evidence event).

## Risks / Trade-offs

- [The project's guardrails now rest on a service this repository does not contain] → Decision 6: a dated check in `docs/sources.md`, repeated on change. The pipeline's tests cover its handling of each answer, not the service's rules.
- [The reader is a single point of failure] → Accepted by the operator. The run stops with a clear reason and records stay due.
- [A `not_now` for a busy site could leave leads due for a long time] → They cost nothing while due; the funnel report counts them.
- [The service cannot yet answer `not_allowed` or `not_now`] → Task 1.1: the service gains them first. Until then nothing is pruned and the pipeline keeps reading robots.txt itself.
- [A challenge or login page comes back as success and is read as an article] → The pipeline's own thin, headline and date checks stay. The outlets report before and after shows any outlet whose Read count rises on pages that are not articles; task 5.2 samples them.
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

- **Robots.txt on news sites.** Decision 9 hands social and video platforms to the service. This design assumes robots.txt is still to be respected for ordinary news sites (the-sun.com is refused today and stays refused). The operator has not said otherwise; if the service is to decide that too, decision 6 and one requirement change.

- **Stealth proxies.** medicalxpress.com answers the identified client with 403. This change's conformance check forbids hiding the client, so it stays unread. Whether that is the standing answer is the operator's; it changes nothing in this change.
