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
- [ ] 4.4 Write registry cache entries with an upsert so two lookups at once cannot collide
- [ ] 4.5 Build a reviewed test set of article and trial pairs across many outlets

## 4b. Signals beyond the text (asked for 2026-11-12)

- [x] 4b.1 Read a page for its headline, summary, date, structured article, linked papers and registry numbers; verify the page tests pass
- [x] 4b.2 Look up the trial of a linked paper through Europe PMC, and a trial the text names through the registry's title search; verify the client tests pass on recorded responses
- [x] 4b.3 Ask the model for the trial's name, size and sponsor, compare them with each record by rule, and rank by agreement; verify the lookup tests pass
- [ ] 4b.4 Do the same in the Worker; verify its tests pass
- [ ] 4b.5 Show a reader why a record is listed first, in the site's words and without a verdict
- [ ] 4b.6 Add `thenwhat outlets` to record which outlets can be read and which signals their pages carry; verify one success and one refusal
- [ ] 4b.7 Run it on the tracked articles and keep the result in `docs/outlets.md`
- [ ] 4b.8 Measure the lookup again and record the change in `docs/lookup.md`

## 5. For readers (decided 2026-11-12: unreviewed answers may be shown, clearly marked)

- [x] 5.1 Build the lookup service for the site's Worker in plain JavaScript, with the pipeline's search and scoring rules; verify its 21 tests pass
- [x] 5.2 Word a live answer in one tested module: the marking first, records with phase, state and number, no verdict; verify the six wording tests pass
- [x] 5.3 Offer the search on the home page for an untracked article, only where a lookup address is configured; nothing is sent until the reader asks
- [x] 5.4 Add the Worker script, the two limits and the lookup settings to the deploy configuration; verify a dry run lists them
- [x] 5.5 Try it end to end on this machine with `make lookup-dev`: an untracked article gave a marked answer with the treatment's trials (2026-11-12)
- [ ] 5.6 Have the browser extension read the open page and ask the same service, for sites that refuse automated reading
- [ ] 5.7 Measure the Worker against the same test as the pipeline's lookup

## 6. For the operator

- [ ] 6.1 Confirm or overturn the working choices in design.md
- [ ] 6.2 Store the model's key with `wrangler secret put OPENAI_API_KEY`, set a monthly limit with the provider, and say on the method page what a registry search sends
