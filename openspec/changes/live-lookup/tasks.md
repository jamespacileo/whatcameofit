# Tasks

## 1. Engine

- [x] 1.1 Name the trial question and record text in `decide/steps.py` so match scoring and lookup share them; verify the resolution and decision tests still pass
- [x] 1.2 Build `look_up`: read the text, look up stated registry numbers, search names and phrases within the condition, score and rank, name a tracked claim, store nothing; verify the seven lookup tests pass

## 2. Command

- [x] 2.1 Add `thenwhat lookup` for an address or pasted text, with `--json`; verify one success and one refusal

## 3. Measurement

- [x] 3.1 Run the lookup on the articles of claims that have reviewer-approved trials and report how often an approved trial is among the likely candidates and at the top (2026-11-12, twice: 23 of 32 claims, 72%; top candidate approved for 17 then 19)
- [x] 3.2 Record the result and its limits in `docs/lookup.md`

## 4. After the first measurement

- [x] 4.1 Search also under names the model knows the treatment by, reported apart; verify the test passes (measured: no gain with the present model)
- [x] 4.2 Search each part of a combination; verify the test passes
- [ ] 4.3 Map generic names to development codes from an open drug-name source, after checking its terms
- [x] 4.4 Write registry cache entries with an upsert so two lookups at once cannot collide; verify the test passes
- [ ] 4.5 Build a reviewed test set of article and trial pairs across many outlets

## 4b. Signals beyond the text (asked for 2026-11-12)

- [x] 4b.1 Read a page for its headline, summary, date, structured article, linked papers and registry numbers; verify the page tests pass
- [x] 4b.2 Look up the trial of a linked paper through Europe PMC, and a trial the text names through the registry's title search; verify the client tests pass on recorded responses
- [x] 4b.3 Ask the model for the trial's name, size and sponsor, compare them with each record by rule, and rank by agreement; verify the lookup tests pass
- [x] 4b.4 Do the same in the Worker; verify its tests pass
- [x] 4b.5 Show a reader why a record is listed first, in the site's words and without a verdict
- [x] 4b.6 Add `thenwhat outlets` to record which outlets can be read and which signals their pages carry; verify one success and one refusal
- [x] 4b.7 Run it on the tracked articles and keep the result in `docs/outlets.md`, with one row per address in `docs/outlets-articles.csv` (2026-11-12: 104 addresses at 57 outlets, 96 read, 4 refused by robots.txt, 4 failed)
- [x] 4b.8 Measure the lookup again and record the change in `docs/lookup.md` (2026-11-12: 43 lookups, an approved trial among the likely records for 32, listed first for 29)

## 4c. Posts on social media (asked for 2026-11-12: a post's address must work, and so must the article it links to)

- [x] 4c.1 Check each platform's terms and what it serves to software without signing in, and note them in `docs/sources.md` (2026-11-12: Bluesky, Hacker News and Mastodon can be read; X, Reddit, Meta's three, LinkedIn, Telegram, TikTok and YouTube are not)
- [x] 4c.2 Where the terms allow, read a post by its address: its text and the links in it; verify the post tests pass in both engines
- [x] 4c.3 Follow the article a post links to, read it as any article, and look up the post's text and the article together; answer with the claim's page when the article is tracked
- [x] 4c.4 Where a platform cannot be read, say so by name and ask for the post's text or the article's address
- [x] 4c.5 Try a real post on each platform that is read, and show per platform what works (2026-11-12: one post each on Bluesky, Hacker News and a Mastodon server, through the site's engine)

- [x] 4c.7 Follow a shortened link in a post to its article where the shortener's robots.txt allows; verify the tests for an allowed chain, a refusing shortener, a dead link and a circular one
- [ ] 4c.6 For the operator: decide whether to register for the platforms that need it. Reddit needs an approved app, X charges per post read, YouTube needs a free key. None is built.

## 4d. Speed (asked for 2026-11-12: a decision model, and work done in parallel)

- [x] 4d.1 Check OpenAI's Decisions API terms, price and limits, try it once with made-up records, and note them in `docs/sources.md`
- [x] 4d.2 Add the `openai-decisions` backend behind `DECISION_BACKEND`, counted in the usage ledger and stopped by the monthly ceiling; verify its tests pass on a recorded answer
- [x] 4d.3 Score with the Decisions API in the Worker when it is configured, and run its independent requests at the same time; verify its tests pass
- [x] 4d.4 Measure a lookup's time and answers with each backend on the same articles, and record both (2026-11-12: 43 lookups each; found 32 then 35, first 29 then 30; the whole run 21 minutes then 10)
- [x] 4d.5 Save an outlet run article by article and check several outlets at once, with one shared limit per registry; verify the tests pass

## 5. For readers (decided 2026-11-12: unreviewed answers may be shown, clearly marked)

- [x] 5.1 Build the lookup service for the site's Worker in plain JavaScript, with the pipeline's search and scoring rules; verify its 21 tests pass
- [x] 5.2 Word a live answer in one tested module: the marking first, records with phase, state and number, no verdict; verify the six wording tests pass
- [x] 5.3 Offer the search on the home page for an untracked article, only where a lookup address is configured; nothing is sent until the reader asks
- [x] 5.4 Add the Worker script, the two limits and the lookup settings to the deploy configuration; verify a dry run lists them
- [x] 5.5 Try it end to end on this machine with `make lookup-dev`: an untracked article gave a marked answer with the treatment's trials (2026-11-12)
- [x] 5.6 Have the browser extension read the open page and ask the same service, for sites that refuse automated reading (2026-11-12; tasks 5.1 to 5.5 of the browser-extension change; not yet pressed in a real Chrome or Safari)
- [ ] 5.7 Measure the Worker against the same test as the pipeline's lookup
- [x] 5.8 Keep marked main content ahead of large navigation menus in both page readers and verify the first-time UCLH article lookup (2026-11-12: baxdrostat identified, BaxHTN NCT06034743 first, 6.4 seconds locally)

## 6. For the operator

- [ ] 6.1 Confirm or overturn the working choices in design.md
- [x] 6.2 Store the model's key with `wrangler secret put OPENAI_API_KEY`, set a monthly limit with the provider, and say on the method page what a registry search sends (2026-11-12)


## 7. Public search budget (authorized 2026-11-12)

- [x] 7.1 Add bounded model output, request deadlines, no retries and sanitized budget refusals; verify with network-free tests
- [x] 7.2 Set the dedicated provider project's $13 hard limit, 80% alert and model restriction
- [x] 7.3 Update site and extension provider disclosures and CI settings
- [x] 7.4 Store the dedicated production key, confirm data sharing is off, deploy and verify a public lookup (2026-11-12: production CI passed; a synthetic non-medical input returned no treatment, and a synthetic semaglutide lookup ranked the stated STEP 1 record NCT03548935 first)

## 8. Extension result confidence (requested 2026-11-12)

- [x] 8.1 Give each displayed trial record its own match-confidence percentage and unavailable state, with wording distinguishing it from effectiveness and trial quality; verify score boundaries and missing values through the shared answer seam
- [x] 8.2 Update the public privacy and method copy for automatic lookup when the extension opens, with no background browsing collection; extension implementation and browser checks are tracked in the browser-extension change
