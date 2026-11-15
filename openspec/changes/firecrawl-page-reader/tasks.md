# Tasks

## 1. The reader as a source

- [ ] 1.1 Get the service's interface from the operator and write down, in `design.md` decision 2, the wire format of the four outcomes (`read`, `not_allowed`, `not_now`, `not_served`), of the service being overloaded, and whether the text is offered as HTML or only as markdown; verify each outcome can be told from the others in a real answer, and stop the change if one cannot or if only markdown is offered
- [ ] 1.2 Run the conformance check of `design.md` decision 6 against the running service, by hand and outside tests, and write its entry in `docs/sources.md` with the date: where it runs, its two routes and how each is authenticated, its version, and the result of each of the five checks; verify an unauthenticated request to the tunnel's hostname is refused, and stop the change if any check fails
- [ ] 1.3 Add page reader to `GLOSSARY.md`, saying it fetches a page and holds the rules about each site; verify the term matches the words in `specs/page-reading/spec.md`
- [ ] 1.4 Run `thenwhat outlets` on main before any code changes and keep the report outside the repository as the baseline; verify it lists Read, Thin, Refused and Failed for every outlet in `docs/outlets.md`

## 2. Configuration

- [ ] 2.1 Add `FIRECRAWL_API_URL` and `FIRECRAWL_API_KEY` to `Settings` and `.env.example`, with no default address, and a default allowance named `reader`; verify `make check` passes and `thenwhat backfill plan` shows the reading step's source as the reader
- [ ] 2.2 Make every command that builds a retriever refuse when no reader address is configured, naming the setting; verify one CLI test per command family (`extract`, `lookup`, `statements`, `outlets`, `backfill run` of the reading step) shows the refusal and that no request is sent

## 3. The page fetch

- [ ] 3.1 Replace the insides of `ArticleRetriever.retrieve()` with one request to the reader, mapping its answers as in `design.md` decisions 2 and 4, and add `ReaderUnavailable` to `backfill/errors.py`; verify tests on synthetic answers cover each of the four outcomes, an unknown answer, no answer, and the service overloaded, and that none of the last three is recorded against an outlet
- [ ] 3.2 Read page metadata from the page as drawn and the text from its main content (`design.md` decision 3); verify tests cover a page whose text exists only in the drawn copy, and one whose headline, date, DOI and registry number are in the head and links
- [ ] 3.3 Record the archive address when a `read` answer carries one; verify a test shows the source article keeps it and that the pipeline sends the Internet Archive nothing
- [ ] 3.4 Verify with a test that the request asks for no summary, structured extraction or prompt, and that a reader answer's text appears in no log record and in no fixture
- [ ] 3.5 Verify with a test that no code path decides whether to read an article by comparing content hashes

## 4. Pruning the pipeline's site rules

- [ ] 4.1 Delete the robots.txt reading, `allowed()`, `rules_unknown()`, `crawl_delay()`, the snapshot lookup and the direct page fetch from `extract/retrieve.py`, with the tests of robots parsing and crawl delay; verify `grep -rn "robots\|crawl_delay\|wayback" pipeline/src/thenwhat/extract pipeline/src/thenwhat/backfill` finds nothing but words in messages, and `make check` passes
- [ ] 4.2 Remove the allowed, rules-unknown, crawl-delay and `outlet:` allowance steps from `backfill/link_read.py`, and `outlet_source` if nothing else uses it; act on the retriever's outcome only; verify the reading tests cover a lead that is not allowed (cannot be read, with the reason, not retried), one that is not now (due, attempts unchanged, run continues with another outlet's lead) and the reader unavailable (run ends)
- [ ] 4.3 Amend the unarchived change `social-link-backfill`: reword "Outlets are asked politely" in its `specs/lead-reading/spec.md` to the reader's answers, and its design where it describes outlet pacing; verify `openspec validate social-link-backfill --strict` passes and its scenarios match `specs/page-reading/spec.md`
- [ ] 4.4 Update `CLAUDE.md`: the robots, rate-limit and User-Agent guardrail says they are enforced by the page reader and checked as `docs/sources.md` records; verify the sentence names the check and that no line still says the pipeline reads robots.txt

## 5. Outlets and acceptance

- [ ] 5.1 Make `probe()` ask the reader and count a `not_allowed` answer as refused; verify `test_outlet_readability.py` passes on synthetic answers, including an outlet counted as read whose pages are drawn by scripts and one counted as refused
- [ ] 5.2 Run `thenwhat outlets` with the change and regenerate `docs/outlets.md` and `docs/outlets-articles.csv`; verify against the baseline of 1.4 that Thin falls, that Read falls for no outlet, that every outlet refused before is still refused, and record the mean time per read. Report any outlet that got worse, or that is newly read after being refused, to the operator before merging
- [ ] 5.3 Run `make check`; verify ruff, ty, pytest and the site build pass with no live request made
