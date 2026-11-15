# Tasks

## 1. The reader as a source

- [ ] 1.1 Offer the service the `NOT_ALLOWED` and `NOT_NOW` answer format of `design.md` decision 2, and record in `design.md` whether it is adopted, changed or declined; verify the pipeline's handling in group 3 matches what was agreed. This does not block the other groups: until the service sends those answers, tests cover them on synthetic answers only
- [ ] 1.2 Run the keep-nothing check of `design.md` decision 6 against the running service, by hand and outside tests, and write the reader's entry in `docs/sources.md` with the date: where it runs, its two routes and that each needs the key, its version, its limits, that whether and how a site is asked is the service's decision (ADR 0006), and the result of each check, without writing any address or the key into the repository; verify an unauthenticated request on each route is refused, that `rawHtml` and `html` come back for an ordinary article, and stop the change if page text outlives a read and cannot be configured away
- [ ] 1.3 Add page reader to `GLOSSARY.md`, saying it fetches a page and holds the rules about each site; verify the term matches the words in `specs/page-reading/spec.md`
- [ ] 1.4 Rewrite "Platforms whose posts are not read" in `docs/sources.md` as `design.md` decision 9 says: keep what the 2026-11-12 reading found about each platform, add the operator's decision of 2026-11-15 in their words, that it is not a legal reading, and what the project still never keeps (author, post text); verify no line in `docs/sources.md` or `CLAUDE.md` still says those platforms are not read
- [ ] 1.5 Run `thenwhat outlets` on main before any code changes and keep the report outside the repository as the baseline; verify it lists Read, Thin, Refused and Failed for every outlet in `docs/outlets.md`

## 2. Configuration

- [ ] 2.1 Add `FIRECRAWL_API_URL` and `FIRECRAWL_API_KEY` to `Settings` and `.env.example`, with no default address, a default allowance named `reader`, a setting for reads side by side that defaults to 2, and a 120 second request timeout; verify `make check` passes, `thenwhat backfill plan` shows the reading step's source as the reader, and a test shows no more than the configured number of requests in flight
- [ ] 2.2 Make every command that builds a retriever refuse when no reader address is configured, naming the setting; verify one CLI test per command family (`extract`, `lookup`, `statements`, `outlets`, `backfill run` of the reading step) shows the refusal and that no request is sent

## 3. The page fetch

- [ ] 3.1 Replace the insides of `ArticleRetriever.retrieve()` with one request to the reader, mapping its answers as in `design.md` decisions 2 and 4, and add `ReaderUnavailable` to `backfill/errors.py`; verify tests on synthetic answers cover each of the four outcomes, an unknown answer, no answer, and the service overloaded, and that none of the last three is recorded against an outlet
- [ ] 3.2 Read page metadata from the page as drawn and the text from its main content (`design.md` decision 3); verify tests cover a page whose text exists only in the drawn copy, and one whose headline, date, DOI and registry number are in the head and links
- [ ] 3.3 Record the archive address when a `read` answer carries one; verify a test shows the source article keeps it and that the pipeline sends the Internet Archive nothing
- [ ] 3.4 Verify with a test that the request is a single scrape with exactly `rawHtml` and `html`, `maxAge` 0 and `storeInCache` false, asks for no `json`, `summary` or `describeImages`, never uses batch or crawl, and that a reader answer's text appears in no log record and in no fixture
- [ ] 3.5 Verify with a test that no code path decides whether to read an article by comparing content hashes

## 4. Pruning the pipeline's site rules

- [ ] 4.1 Delete the robots.txt reading, `allowed()`, `rules_unknown()`, `crawl_delay()`, the snapshot lookup and the direct page fetch from `extract/retrieve.py`, with the tests of robots parsing and crawl delay; verify `grep -rn "robots\|crawl_delay\|wayback" pipeline/src/thenwhat/extract pipeline/src/thenwhat/backfill` finds nothing but words in messages, and `make check` passes
- [ ] 4.2 Remove the allowed, rules-unknown, crawl-delay and `outlet:` allowance steps from `backfill/link_read.py`, and `outlet_source` if nothing else uses it; act on the retriever's outcome only; verify the reading tests cover a lead that is not allowed (cannot be read, with the reason, not retried), one that is not now (due, attempts unchanged, run continues with another outlet's lead) and the reader unavailable (run ends)
- [ ] 4.3 Amend the unarchived change `social-link-backfill`: reword "Outlets are asked politely" in its `specs/lead-reading/spec.md` to the reader's answers, and its design where it describes outlet pacing; verify `openspec validate social-link-backfill --strict` passes and its scenarios match `specs/page-reading/spec.md`
- [ ] 4.4 Reword the robots.txt, rate-limit and User-Agent guardrail in `CLAUDE.md` and `openspec/config.yaml` to say that whether and how a site is asked is the page reader's decision (ADR 0006) and that the contact User-Agent is still sent to registries and literature indexes; correct the README's lines on robots.txt and the outlet entry in `docs/sources.md`; verify `grep -rni "robots" CLAUDE.md README.md openspec/config.yaml docs/sources.md` shows no line that says the project reads or follows robots.txt for articles

## 5. Outlets and acceptance

- [ ] 5.1 Make `probe()` ask the reader and count a `not_allowed` answer as refused; verify `test_outlet_readability.py` passes on synthetic answers, including an outlet counted as read whose pages are drawn by scripts and one counted as refused
- [ ] 5.2 Run `thenwhat outlets` with the change and regenerate `docs/outlets.md` and `docs/outlets-articles.csv`; verify against the baseline of 1.5 that Thin falls, that Read falls for no outlet, list every outlet that moved from Refused to Read, and record the mean time per read. For each outlet whose Read count rose, open three of its newly read articles' reports and confirm a headline and date were found, so that a challenge or login page is not being counted as an article. Report any outlet that got worse, and the list of newly read outlets, to the operator before merging
- [ ] 5.3 Run `make check`; verify ruff, ty, pytest and the site build pass with no live request made
