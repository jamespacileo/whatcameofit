# Tasks

Each section is useful when it is done, without the sections after it. Sections 2 to 5 need nothing from `cloudflare-source-of-truth`; section 2 builds on `daily-trial-refresh`. Section 6 waits for it.

## 1. Decisions before any build

- [ ] 1.1 Put the open decisions of `design.md` to the operator; verify each answer replaces its question in `design.md`, and that a spec is revised where an answer differs from the recommendation it was written to
- [ ] 1.2 Write `docs/adr/0010`: a registry trial has a page of registry facts without a claim, which facts it may state, and that no word for how a trial turned out is used; verify it names the glossary line and the `CLAUDE.md` lines it supersedes
- [ ] 1.3 Add trial page, trial listing, telling name, strong link and set to `GLOSSARY.md`, and revise "Registry trial" ("never exported"); verify the terms match the specs word for word
- [x] 1.4 Reconcile section 2 and `specs/registry-corpus` with the change `daily-trial-refresh` (pull request 268, open on 2026-11-16); verify the outcome is recorded here before any task of section 2 starts. Done 2026-11-16, on paper: the daily step, the clean stop and "the daily run starts no step over loaded trials" are that change's and were removed from this one; a load here starts nothing; the refresh of a citing claim is the daily run's existing `refresh` step taking those claims first, not a new step, and it is not model-free; the export hold is on `thenwhat export`, since the daily run never exports. Table in `design.md`, decision 10. To check again if pull request 268 changes before it merges
- [ ] 1.6 Apply this change only after `daily-trial-refresh` is merged; verify `openspec/changes/daily-trial-refresh` or its synced `daily-run` spec is on `main` before any task of section 2 starts
- [ ] 1.5 Note the wider field list of the bulk load in `docs/sources.md` with the date and the bytes a trial measured in `design.md`; verify the entry is written before the client is changed

## 2. The corpus: wider records, kept current

- [ ] 2.1 Add the fields of `specs/registry-corpus` to the list request and to the stored trial, with a new migration; verify a recorded fixture of one page with the wider fields loads, and a trial stored with ten fields gains the rest in place
- [ ] 2.2 Keep no name for a sponsor classed as an individual; verify a test with such a record
- [ ] 2.3 Load every interventional study again with the wider fields, as a full load and not `--changes-only`, so trials unchanged since 16 November gain them; verify the count stored equals the registry's count that day, and record here the requests sent, the time taken and the table's size
- [ ] 2.4 Add to a load's report how many cited trials changed and how many claims that made due; verify tests of a day with four cited trials changed and a day with none. The daily step and its clean stop are `daily-trial-refresh`'s and are not built again
- [ ] 2.5 Make a cited trial's change of state, phases, dates or results posting make its claims due for the registry refresh, and make new or renamed trials due for the offline linking; verify tests for a cited trial, an uncited trial, and a field no step uses
- [ ] 2.6 Have the daily run's `refresh` step take first the claims a load made due, within `DAILY_RUN_REFRESH_LIMIT` and its spend guard, and put both counts in the summary; verify with the stand-in in `scripts/tests/daily-run.test.sh`: the order, more due than the limit, and the spend guard stopping the run
- [ ] 2.7 Refuse `thenwhat export` while a cited trial's refresh is due, saying how many and naming the command; verify one test that it refuses, one that it writes when none is due, and one that an uncited trial's change holds nothing
- [ ] 2.8 Verify with a test that a load starts no step: after a load with a new telling-named trial, no lead is read, no page-reader request or news search is sent, no claim or match is created; and verify `docs/daily-run.md` says the refresh order and that the run still never exports

## 3. Strong links

- [ ] 3.1 Screen every lead in scope again against the whole corpus with the present rule, so the link table describes one corpus; verify the counts of `design.md` are replaced here by real ones for each set
- [ ] 3.2 Measure, over stored titles, the share that hold each substance name, and choose with the operator the share above which a name is not telling; verify the figure and the twenty most common names it excludes are recorded here, and the setting is in `.env.example` with no default
- [ ] 3.3 Collect development codes from every intervention name and other name by rule; verify tests for a code, a code written without its hyphen, and a name that only contains digits
- [ ] 3.4 Ask the substance registry for the drug and biological names of the set being worked, within its allowance, storing "not listed" as an answer; verify with recorded fixtures, and that a name not yet asked is not telling
- [ ] 3.5 Make strong links as `specs/trial-report-links` says, recorded with the name and condition word, to a name and a condition and not to one trial; verify tests for each scenario and that a run sends no request and records no usage
- [ ] 3.6 Sample forty strong links and judge them as `design.md` judged the present link; verify the table is recorded here, and stop to tell the operator if fewer than half name the right treatment for the right condition
- [ ] 3.7 Report, by set: leads strongly linked, their triage bands, how many are read, how many would be read; verify one test of its figures and one of its message when nothing is linked

## 4. Reading a set

- [ ] 4.1 Add the named sets and the command that names the one being worked; verify tests that an unknown name is refused with the list, and that `completed-recently` is refused while no completion date is stored
- [ ] 4.2 Run the offline linking for trials a load left due, then print the plan of `specs/trial-report-links` before a set is worked, and read nothing when the expected cost passes the route's share; verify tests of both
- [ ] 4.3 Read held leads with a strong link to the set being worked, never a rejected lead, in the order of `specs/trial-report-links`; verify tests for a held lead, a rejected lead and the order of two due leads
- [ ] 4.4 Hand the strongly linked trials to preparation as candidates with their reason; verify a test that a linked trial is scored for the claim's indication and is not approved for having been linked
- [ ] 4.5 Verify with a test that a claim drafted on this route is held awaiting audit and that no export publishes it before it is cleared
- [ ] 4.6 Work `under-way-phase-3`: plan, read, `thenwhat prepare --pending`, audit, clear; record here the reads, the failures on the page, the claims drafted and joined, the trials newly cited, the cost and the hours, and show the operator before the next set
- [ ] 4.7 Work `under-way-phase-2`, then `completed-recently`, each recorded as 4.6 is

## 5. On the static site

- [ ] 5.1 Hold the state phrases, the no-report line and the results lines in the site's wording module, and fail the build on verdict wording in any of them; verify a build that fails on a planted word
- [ ] 5.2 Word the state on the trial page that exists by the `trial-facts` mapping; verify a test that a recruiting trial's page does not hold the word "recruiting"
- [ ] 5.3 Write the trial listing for a named set from the pipeline, with its schema, and build it into the site as a file fetched only on search; verify the schema test, the file's size raw and compressed recorded here, and that a claim page fetches nothing of it
- [ ] 5.4 Answer a search for a listed trial's identifier or title words with its page, after any claim; verify tests for an uncited identifier, a cited one and a title
- [ ] 5.5 Add the setting that opens the trial page to listed identifiers, off by default; verify tests that a listed, uncited trial is not found while it is off and is shown, not indexed and with the no-report line, while it is on
- [ ] 5.6 Verify with tests that an uncited trial's page holds no status, no gloss, no score, no lead, no location or contact, and none of the words `specs/trial-pages` forbids
- [ ] 5.7 Keep uncited trial pages out of the sitemap; verify a test
- [ ] 5.8 Add to the method page how a trial comes to have a page, what the page states, and that most trials are never in the news; verify the site build passes its wording checks
- [ ] 5.9 Deploy to a pull request preview and read twenty uncited trial pages across states and phases with the operator; record here anything reworded

## 6. From the store (after `cloudflare-source-of-truth` holds the corpus)

- [ ] 6.1 Measure the store's size with 467,064 wider registry trials and report it to `cloudflare-source-of-truth` against its criterion; verify the figure is recorded in both changes
- [ ] 6.2 Answer every stored trial's page from the store with no request to the registry, by the same rules and phrases, with the read date and the date the registry was last checked; verify tests for a cited trial, an uncited one, and a change load older than the configured age
- [ ] 6.3 State a trial's facts on its page and on every claim page from the one most recent stored record; verify a test with two copies fetched on different days
- [ ] 6.4 Search every stored trial by identifier and by word from the store; verify tests, and that the static listing is no longer built
- [ ] 6.5 Add the full-record step for trials of a named set whose record says results are posted, one registry request a trial and no model, and show primary outcomes from it by the `trial-facts` rules; verify with recorded fixtures and a test that a page without a full record names no outcome

## 8. From the trial's end

Free and deterministic first. Each task is useful when done; 8.1 to 8.6 send no request to a news source. Section 2's wider load comes first.

- [x] 8.1 Run the batching experiment before specifying the news search; verify its request count, limits, attribution and a hand sample of 40 are in `design.md`. Done 2026-11-17: 19 requests logged, counted as 20; results under "The batching experiment"
- [ ] 8.2 Correct the news index's allowance count by 20 requests for the week of 2026-11-16, and add to its entry in `docs/sources.md` the limits read from its source and the limits observed; verify the entry is dated
- [ ] 8.3 Build a trial's fingerprint by rule from the stored record, with each term marked fit or not; verify tests for an acronym that is an ordinary word, one that is a condition's abbreviation, one with a digit, a code, and a trial with no fit term but its number
- [ ] 8.4 Add the sets `active-recent` and `completed-with-results` with their dates as settings with no default; verify tests that each is refused before the wider load, that a cited trial is left out, and that an unknown name is refused with the list
- [ ] 8.5 Attach the papers a stored record lists as result or derived, with the registry's kind, never background, and store a link the record gives on a listed outlet as a link lead; verify tests for each kind and for a link on an unlisted domain
- [ ] 8.6 Treat a fit acronym and a registry number as strong links in the offline linking; verify tests for an acronym in a headline and a number in an address, and record here how many stored leads link to each set
- [ ] 8.7 Write PubMed's entry in `docs/sources.md` from its current pages, including the usage-policy chapter that could not be read on 2026-11-16, then its client with recorded fixtures: one request a trial for the number in the publisher's field, "nothing found" stored; verify no paper with more than three numbers is attached and none that only mentions the number
- [ ] 8.8 List attached papers on the trial page under the two fixed headings with paper facts; verify a test that a paper leaves the no-report line in place and that the page states nothing of what a paper found
- [ ] 8.9 Build the batched news search as a step: fit terms only, the number of trials a request as a setting starting at ten, a request cut short asked again in halves, a timed-out request leaving its trials due, a hit tied only on headline or address, untied hits counted and dropped; verify with recorded fixtures on synthetic headlines
- [ ] 8.10 Try title-only search on three requests of ten trials when the index is not slow, and record here whether it answers faster and how many hits tie; keep it only if it does
- [ ] 8.11 Run the batched search for `completed-with-results`, then judge 40 tied hits by hand; record here the requests, time-outs, stories, ties and the judgement, and stop to tell the operator if fewer than half name the trial's own treatment
- [ ] 8.12 Print the plan of `specs/trial-coverage` before any route runs; verify tests of a plan, of a route that is off, and of a route turned on with no dated entry for its source
- [ ] 8.13 Verify with one test for each route that a found article is a lead and nothing more: no claim, source article, match or event exists until it is read, a rejected lead is not read, and a drafted claim is held awaiting audit
- [ ] 8.14 Only on the operator's answers to open decisions 11, 13 and 14: write the entry in `docs/sources.md`, then the client, for a wire's feeds, a full-text search or a mentions index; verify each is off by default

## 7. Records

- [ ] 7.1 Revise `CLAUDE.md`'s guardrails and layout: a trial page, the daily load and what it never starts; verify no line still says a registry trial is never shown
- [ ] 7.2 When `social-link-backfill` is synced, fold the held-on-a-strong-link case and the reading order into `lead-reading`; verify `openspec validate` passes for both
- [ ] 7.3 Add fingerprint, fit term and the two sets to `GLOSSARY.md`, and revise "Results paper" if papers that carry the number are shown; verify the terms match `specs/trial-coverage`
