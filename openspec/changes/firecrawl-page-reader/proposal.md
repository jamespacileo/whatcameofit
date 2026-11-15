# Proposal

## Why

The pipeline reads an article with one plain request and a hand-written HTML reader, and it carries its own rules for each site it asks: robots.txt, crawl delays, spacing per outlet, an archive lookup. A page whose article is drawn by scripts comes back too thin to read. The operator is setting up a self-hosted Firecrawl service that can read almost any address and that will hold the rules about individual sites itself. That is the opportunity to read more pages and to remove the per-site handling from this project.

## What Changes

- An article page is fetched through one **page reader**, the operator's service. There is one way to fetch a page: the pipeline's direct request is removed, not kept behind the reader as a second try.
- **BREAKING** (for the pipeline's internals and two requirements): the rules about an individual site move to the reader. The reader decides whether an address may be fetched, how often a site may be asked, and where a copy comes from. The pipeline no longer reads robots.txt, keeps a crawl delay, spaces requests per outlet, or asks the Internet Archive itself.
- The reader **answers with what happened**, and the pipeline acts on the answer: the page was read; the address is not allowed, with the reason; the site cannot be asked now, with when to try again; the site did not serve the page, with its status.
- **Pruned from the pipeline:** the robots.txt reading, crawl delay and unknown-rules handling in `extract/retrieve.py`; the archive lookup there; the per-outlet allowance and its branches in `backfill/link_read.py`.
- The guardrails do not move with the code. Robots.txt is respected on news sites, the client is identified to them, and no article text is kept. They become conditions the reader must meet, checked against the running service and recorded in `docs/sources.md`, and re-checked whenever its rules change.
- The pipeline asks the reader for the page only: no summary, no structured extraction. Every model call stays in the pipeline, where it is logged and counted against the monthly ceiling.
- When the reader itself cannot be reached or is overloaded, the run stops and says so; the article is left to be read later. Nothing is fetched another way.
- `thenwhat outlets` is run before and after. The change is accepted on its Read, Thin, Refused and Failed counts per outlet.

Not in this change, and listed in `design.md` as the next prunes once the reader's answers cover them:

- **Posts.** `extract/post.py` reads Bluesky, Hacker News and Mastodon through each platform's own interface. It goes when posts are read through the reader. By the operator's decision of 2026-11-15 the reader may read X, Reddit, Meta's platforms, YouTube and others, and how it reads each is the service's responsibility; at worst the answer is built from a post's Open Graph card. The pipeline still keeps no author and no post text.
- **Research papers and registry records a page links to.** `extract/page.py` holds address patterns for publishers and PubMed. They go when the reader returns the identifiers a page links to.
- **The lookup service and the browser extension.** `site/worker` has its own page, post, short-link and screenshot readers, and the extension has its own host lists. The public lookup will depend on the reader too (`docs/adr/0005`): the project's Worker asks it, and a reader's browser or the extension never does. When the reader's machine is down, the lookup shows a service-overloaded error. That is its own change.

Not pruned, because they are not rules about fetching: the address comparison shared with the site (`backfill/address.py`), the list of outlets and their names (`backfill/outlet_kinds.py`), and the clients of registries and literature indexes (`sources/`), which store the raw payload of every evidence event.

## Capabilities

### New Capabilities

- `page-reading`: how the pipeline fetches a news page: through one reader that holds the rules about each site, what the reader's answers are and what the pipeline does with each, what the reader must never do, and what happens when the reader cannot be asked.

### Modified Capabilities

- `claim-extraction`: **Robots exclusion** becomes the reader's refusal, for any reason it gives. **Archived copies** no longer has the pipeline look for a snapshot; an archive address is recorded when the reader says the copy came from one.

`lead-reading` ("Outlets are asked politely") changes in the same way, but that requirement is still in the unarchived change `social-link-backfill`. It is amended there as a task of this change, not as a delta here.

## Impact

- **Code removed:** robots, crawl delay, snapshot and direct page fetch in `pipeline/src/thenwhat/extract/retrieve.py`; outlet allowance claims in `backfill/link_read.py`; `outlet_source` in `backfill/allowance.py` if nothing else uses it.
- **Code changed:** `extract/retrieve.py` (asks the reader, maps its answers), `outlets/readability.py`, `cli/extract.py`, `cli/lookup.py`, `cli/statements.py`, `config.py`, `.env.example`.
- **Dependencies:** none added. The reader is asked over HTTP with the client the pipeline already uses.
- **Configuration:** the reader's address and key, from the environment. The read step's allowance names the reader, not each outlet.
- **Docs:** `docs/sources.md` (the reader's entry and its conformance check; "Platforms whose posts are not read" rewritten to record the operator's decision), `docs/outlets.md` (regenerated), `GLOSSARY.md`, `CLAUDE.md` (where the robots and identification rules are enforced), `docs/adr/0005` (written).
- **Tests:** retrieval, outlet and reading tests move to synthetic reader answers; tests of robots parsing and crawl delay are removed with the code. No live request in tests or CI.
- **Data:** no migration. A content hash from a new read of an article will differ from one recorded before.
- **Operations:** the pipeline needs the reader running to read any article, and trusts it for the rules it used to check itself.
