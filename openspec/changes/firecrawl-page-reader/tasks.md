# Tasks

## 1. The reader as a source

- [ ] 1.1 The service is self-hosted (operator, 2026-11-15). Read its deployment configuration and Firecrawl's self-hosting guide, then write its entry in `docs/sources.md` with the date checked: that it is reachable only on the private network, authentication, version, any limit it applies, which cloud-only features it lacks, and what its result cache, job queue and container logs keep and for how long; verify the entry states plainly whether any article text outlives a read, and stop the change if it does and cannot be configured away
- [ ] 1.2 Against the running service, by hand and outside tests, read one request-echo page and one page drawn by scripts with the request of `design.md` decision 5; verify and record in `docs/sources.md` that the outlet receives the contact User-Agent, that `rawHtml` is the page as drawn, and that a second read is not served from a kept copy. If any of the three fails, stop and tell the operator
- [ ] 1.3 Add page reader to `GLOSSARY.md`, saying it fetches a page and decides nothing; verify the term matches the words in `specs/page-reading/spec.md`
- [ ] 1.4 Run `thenwhat outlets` on main before any code changes and keep the report outside the repository as the baseline; verify it lists Read, Thin, Refused and Failed for every outlet in `docs/outlets.md`

## 2. Configuration

- [ ] 2.1 Add `FIRECRAWL_API_URL` and `FIRECRAWL_API_KEY` to `Settings` and `.env.example`, with no default address; verify `make check` passes and `.env.example` explains that the key is optional for a self-hosted service
- [ ] 2.2 Make every command that builds a retriever refuse when no reader address is configured, naming the setting; verify one CLI test per command family (`extract`, `lookup`, `statements`, `outlets`, `backfill run` of the reading step) shows the refusal and that no request is sent

## 3. The page fetch

- [ ] 3.1 Replace the page fetch in `ArticleRetriever` with one request to the reader as in `design.md` decisions 3 to 5, keeping robots.txt, the snapshot lookup and `json()` direct; verify a test asserts the request body is exactly the two formats, `maxAge` 0, `storeInCache` false, `proxy` basic and the contact User-Agent, using a synthetic reader answer
- [ ] 3.2 Read page metadata from `rawHtml` and the text from `html`; verify tests with synthetic answers cover a page whose text exists only in the rendered copy, and a page whose headline, date, DOI and registry number are in the head and links
- [ ] 3.3 Map the reader's answers as in `design.md` decision 6, adding `ReaderUnavailable` to `backfill/errors.py`; verify tests cover an outlet status that is not 200 (snapshot looked for), a too-many-requests answer (paused, record due), no answer and a refused key (run ends, attempts unchanged), and that none is recorded as the outlet's failure
- [ ] 3.4 Verify with tests that a disallowed address and an outlet with unreadable rules send the reader nothing, that no direct request is made to the outlet for a page under any answer, and that no code path decides whether to read an article by comparing content hashes
- [ ] 3.5 Verify with a test that a reader answer's text appears in no log record and that the retrieval fixtures hold synthetic pages only

## 4. Outlets and acceptance

- [ ] 4.1 Make `probe()` ask the reader, so `thenwhat outlets` measures what the pipeline reads; verify `test_outlet_readability.py` passes on synthetic reader answers, including an outlet counted as read whose pages are drawn by scripts
- [ ] 4.2 Run `thenwhat outlets` with the change and regenerate `docs/outlets.md` and `docs/outlets-articles.csv`; verify against the baseline of 1.4 that Thin falls, that Read falls for no outlet, and record the mean time per read. Report any outlet that got worse to the operator before merging
- [ ] 4.3 Run `make check`; verify ruff, ty, pytest and the site build pass with no live request made
