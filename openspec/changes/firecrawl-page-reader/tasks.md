# Tasks

## 1. The reader as a source

- [ ] 1.1 (waits on the service, which is outside this repository) Have the service gain what `design.md` "The service as it is today" lists as missing: a rule set this project asks for by name; a `not_allowed` answer with a reason, given at least for a news site's address that robots.txt disallows; a `not_now` answer with a time, told apart from the machine failing; the contact User-Agent passed on to the site. Then write the wire format of all four outcomes and of the machine being overloaded into `design.md` decision 2; verify each outcome can be told from the others in a real answer. Groups 3 to 5 do not start before this is done
- [ ] 1.2 Run the conformance check of `design.md` decision 6 against the running service, by hand and outside tests, and write its entry in `docs/sources.md` with the date: where it runs, its two routes and that each needs the key, its version, and the result of each of its checks, without writing any address or the key into the repository; verify an unauthenticated request on each route is refused, that `rawHtml` and `html` come back for an ordinary article, and stop the change if any check fails
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
- [ ] 3.4 Verify with a test that the request is a single scrape with exactly `rawHtml` and `html`, `maxAge` 0, `storeInCache` false and the project's rule set, asks for no `json`, `summary` or `describeImages`, never uses batch or crawl, and that a reader answer's text appears in no log record and in no fixture
- [ ] 3.5 Verify with a test that no code path decides whether to read an article by comparing content hashes

## 4. Pruning the pipeline's site rules

- [ ] 4.1 Delete the robots.txt reading, `allowed()`, `rules_unknown()`, `crawl_delay()`, the snapshot lookup and the direct page fetch from `extract/retrieve.py`, with the tests of robots parsing and crawl delay; verify `grep -rn "robots\|crawl_delay\|wayback" pipeline/src/thenwhat/extract pipeline/src/thenwhat/backfill` finds nothing but words in messages, and `make check` passes
- [ ] 4.2 Remove the allowed, rules-unknown, crawl-delay and `outlet:` allowance steps from `backfill/link_read.py`, and `outlet_source` if nothing else uses it; act on the retriever's outcome only; verify the reading tests cover a lead that is not allowed (cannot be read, with the reason, not retried), one that is not now (due, attempts unchanged, run continues with another outlet's lead) and the reader unavailable (run ends)
- [ ] 4.3 Amend the unarchived change `social-link-backfill`: reword "Outlets are asked politely" in its `specs/lead-reading/spec.md` to the reader's answers, and its design where it describes outlet pacing; verify `openspec validate social-link-backfill --strict` passes and its scenarios match `specs/page-reading/spec.md`
- [ ] 4.4 Update `CLAUDE.md`: the robots, rate-limit and User-Agent guardrail says they are enforced by the page reader for news sites and checked as `docs/sources.md` records, and that social and video platforms are the reader's to handle; verify the sentence names the check and that no line still says the pipeline reads robots.txt

## 5. Outlets and acceptance

- [ ] 5.1 Make `probe()` ask the reader and count a `not_allowed` answer as refused; verify `test_outlet_readability.py` passes on synthetic answers, including an outlet counted as read whose pages are drawn by scripts and one counted as refused
- [ ] 5.2 Run `thenwhat outlets` with the change and regenerate `docs/outlets.md` and `docs/outlets-articles.csv`; verify against the baseline of 1.5 that Thin falls, that Read falls for no outlet, that every outlet refused before is still refused, and record the mean time per read. For each outlet whose Read count rose, open three of its newly read articles' reports and confirm a headline and date were found, so that a challenge or login page is not being counted as an article. Report any outlet that got worse, or that is newly read after being refused, to the operator before merging
- [ ] 5.3 Run `make check`; verify ruff, ty, pytest and the site build pass with no live request made
