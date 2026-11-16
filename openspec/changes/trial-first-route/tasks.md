# Tasks

Each section is useful when it is done, without the sections after it. Sections 2 to 5 need nothing from `cloudflare-source-of-truth`; section 2 builds on `daily-trial-refresh`. Section 6 waits for it.

## 1. Decisions before any build

- [ ] 1.1 Put the ten open decisions of `design.md` to the operator; verify each answer replaces its question in `design.md`, and that a spec is revised where an answer differs from the recommendation it was written to
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

## 7. Records

- [ ] 7.1 Revise `CLAUDE.md`'s guardrails and layout: a trial page, the daily load and what it never starts; verify no line still says a registry trial is never shown
- [ ] 7.2 When `social-link-backfill` is synced, fold the held-on-a-strong-link case and the reading order into `lead-reading`; verify `openspec validate` passes for both
