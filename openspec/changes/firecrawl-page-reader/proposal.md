# Proposal

## Why

The pipeline reads an article with one plain request and a hand-written HTML reader. A page whose article is drawn by scripts comes back too thin to read, and the operator is asked to paste the text; in a backfill run the lead ends as "cannot be read". The operator is setting up a Firecrawl service that renders a page before returning it, so the pipeline can read those pages without a second fetch path of its own.

## What Changes

- An article page is fetched through one **page reader**, the operator's Firecrawl service, in place of the pipeline's direct request. There is one way to fetch a page: the direct request is removed, not kept behind the reader as a second try.
- The pipeline keeps deciding **whether** a page may be fetched. It reads the outlet's robots.txt itself, as now, before the reader is asked. The reader is never asked for a page the outlet's rules refuse, or whose rules could not be read.
- The reader is asked to send the pipeline's contact User-Agent and to use no proxy that hides who is asking. An outlet that refuses the identified client stays refused.
- The reader is asked for a fresh copy every time and told to keep none. It is asked for the page only: no summary, no structured extraction, no screenshot. Every model call stays in the pipeline, where it is logged and counted against the monthly ceiling.
- When the reader is not configured, does not answer, or says it is asked too often, the run stops and says so. The article is left to be read later. Nothing is fetched another way.
- What a page says about itself (headline, date, linked papers, registry numbers) is read from the rendered page with the existing rules.
- `docs/sources.md` gains an entry for the reader: where it runs, what it keeps, its limits, and the date checked.
- `thenwhat outlets` is run before and after. The change is accepted on its Read, Thin and Failed counts per outlet.

Not in this change:

- **Platforms whose posts are not read.** X, Reddit, LinkedIn, Facebook, Instagram, Threads and Telegram stay unread (`docs/sources.md`, "Platforms whose posts are not read"). Their terms decide that, not what a reader can fetch.
- **Posts on Bluesky, Hacker News and Mastodon.** They are read through each platform's own interface for software, which stays as it is.
- **The live lookup service and the browser extension.** `site/worker` keeps its own page reader. Until a later change moves it, the pipeline can read some pages the lookup service cannot.
- **The archived-snapshot step.** An article that cannot be retrieved is still looked for as an archived snapshot. This is a second source used when the first fails, which the operator's rule against fallbacks asks to be flagged: it is flagged in `design.md` and left for the operator to decide.
- **Getting past an outlet's bot check** with the reader's stealth proxies. That would stop identifying the client and needs the operator's decision first (`design.md`, open decisions).
- **PDF addresses** and **batch reads**. Each can follow once the single-page path is measured.

## Capabilities

### New Capabilities

- `page-reading`: how the pipeline fetches a news page: through one reader, only where the outlet's rules allow, identified, with nothing kept by the reader and no model run by it, and what happens when the reader cannot be asked.

### Modified Capabilities

None. `claim-extraction` (robots exclusion, archived copies, transient article text, pasted text) and the outlet pacing in `lead-reading` hold as written; this change is how a page is fetched under them.

## Impact

- **Code:** `pipeline/src/thenwhat/extract/retrieve.py` (page fetch and the outlet probe), `pipeline/src/thenwhat/config.py`, `.env.example`. Its callers keep their interface: `cli/extract.py`, `cli/lookup.py`, `cli/statements.py`, `backfill/link_read.py`, `outlets/readability.py`.
- **Dependencies:** none added. The reader is asked over HTTP with the client the pipeline already uses.
- **Configuration:** the reader's address and, where it needs one, its key. Both from the environment.
- **Docs:** `docs/sources.md`, `docs/outlets.md` (regenerated), `GLOSSARY.md` (page reader).
- **Tests:** `test_article_retrieval.py`, `test_outlet_readability.py` and the reading tests move to synthetic reader answers. No live request in tests or CI.
- **Data:** no migration. A content hash recorded from a new read of an article will differ from one recorded before this change, because the text comes from the rendered page.
- **Operations:** the pipeline now needs the reader to be running to read any article.
