# Tasks

Each section is useful when it is done, without the sections after it. Sections 2 to 5 need nothing from `cloudflare-source-of-truth`; section 2 builds on `daily-trial-refresh`. Section 6 waits for it.

## 1. Decisions before any build

- [x] 1.1 Done 2026-11-17: every open decision was put to the operator in a question dialog and is recorded, dated, under "Open Questions" in `design.md`; `specs/trial-coverage` was revised for the sets as built and for route 2's batched requests. Was: Put the open decisions of `design.md` to the operator; verify each answer replaces its question in `design.md`, and that a spec is revised where an answer differs from the recommendation it was written to
- [ ] 1.2 Write `docs/adr/0010`: a registry trial has a page of registry facts without a claim, which facts it may state, and that no word for how a trial turned out is used; verify it names the glossary line and the `CLAUDE.md` lines it supersedes
- [ ] 1.3 Add trial page, trial listing, telling name, strong link and set to `GLOSSARY.md`, and revise "Registry trial" ("never exported"); verify the terms match the specs word for word
- [x] 1.4 Reconcile section 2 and `specs/registry-corpus` with the change `daily-trial-refresh` (pull request 268, open on 2026-11-16); verify the outcome is recorded here before any task of section 2 starts. Done 2026-11-16, on paper: the daily step, the clean stop and "the daily run starts no step over loaded trials" are that change's and were removed from this one; a load here starts nothing; the refresh of a citing claim is the daily run's existing `refresh` step taking those claims first, not a new step, and it is not model-free; the export hold is on `thenwhat export`, since the daily run never exports. Table in `design.md`, decision 10. To check again if pull request 268 changes before it merges
- [ ] 1.6 Apply this change only after `daily-trial-refresh` is merged; verify `openspec/changes/daily-trial-refresh` or its synced `daily-run` spec is on `main` before any task of section 2 starts
- [ ] 1.5 Note the wider field list of the bulk load in `docs/sources.md` with the date and the bytes a trial measured in `design.md`; verify the entry is written before the client is changed

## 2. The corpus: wider records, kept current

- [x] 2.1 Done on `main` (migration `0031`, `backfill/registry_load.py`). Was: Add the fields of `specs/registry-corpus` to the list request and to the stored trial, with a new migration; verify a recorded fixture of one page with the wider fields loads, and a trial stored with ten fields gains the rest in place
- [x] 2.2 Done on `main` (`without_people`). Was: Keep no name for a sponsor classed as an individual; verify a test with such a record
- [x] 2.3 Done 2026-11-17: 467,064 stored with the wider record. Was: Load every interventional study again with the wider fields, as a full load and not `--changes-only`, so trials unchanged since 16 November gain them; verify the count stored equals the registry's count that day, and record here the requests sent, the time taken and the table's size
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

- [x] 5.1 Hold the state phrases, the no-report line and the results lines in the site's wording module, and fail the build on verdict wording in any of them; verify a build that fails on a planted word Done 2026-11-17: `site/src/lib/trial-page.mjs`; the template `trial-reader.astro` reads it, so a build fails; the planted word is tested on the same check in `site/tests/trial-pages.test.mjs`, not by a second build
- [x] 5.2 Word the state on the trial page that exists by the `trial-facts` mapping; verify a test that a recruiting trial's page does not hold the word "recruiting" Done 2026-11-17, on the cited page and the plain page alike
- [x] 5.3 Write the trial listing for a named set from the pipeline, with its schema, and build it into the site as a file fetched only on search; verify the schema test, the file's size raw and compressed recorded here, and that a claim page fetches nothing of it Done 2026-11-17: `thenwhat trials-listing`, `site/trials-listing.schema.json`, built as `/trials-listing.json`. Set `active-since-2025`, 23,328 trials on the working database: 7,009,433 bytes raw, 1,933,766 with gzip -9, 1,182,924 with Brotli. Under 8 MiB, so one file
- [x] 5.4 Answer a search for a listed trial's identifier or title words with its page, after any claim; verify tests for an uncited identifier, a cited one and a title Done 2026-11-17, and for words of the acronym, an intervention's name and a condition too
- [x] 5.5 Add the setting that opens the trial page to listed identifiers, off by default; verify tests that a listed, uncited trial is not found while it is off and is shown, not indexed and with the no-report line, while it is on Done 2026-11-17, differently: the operator decided that day that the page opens for the listed set, so the setting is on unless a build is given `LISTED_TRIAL_PAGES=0`, and a build with no listing beside its export opens nothing. Both are tested
- [x] 5.6 Verify with tests that an uncited trial's page holds no status, no gloss, no score, no lead, no location or contact, and none of the words `specs/trial-pages` forbids
- [x] 5.7 Keep uncited trial pages out of the sitemap; verify a test
- [x] 5.8 Add to the method page how a trial comes to have a page, what the page states, and that most trials are never in the news; verify the site build passes its wording checks Done 2026-11-17: the section is drawn only in a build that has a listing
- [ ] 5.9 Deploy to a pull request preview and read twenty uncited trial pages across states and phases with the operator; record here anything reworded
- [x] 5.10 Remove every person from a registry record before the Worker saves, shows, compares or sends it: one rule (`site/worker/people.mjs`), the trial page asking only for the fields it shows, saved copies of the older version refused and replaced, and a test that plants a person in every field (`specs/trial-records`, "No person of a registry record is saved or shown")

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
- [x] 8.4 Done on `main` before phase 1 as `active-since-2025` and `completed-with-results-since-2025` (`backfill/trial_sets.py`, `thenwhat backfill trial-sets`), the date in the name (`design.md`, question 16); leaving a cited trial out is the news routes' and is task 8.9's. Was: Add the sets `active-recent` and `completed-with-results` with their dates as settings with no default; verify tests that each is refused before the wider load, that a cited trial is left out, and that an unknown name is refused with the list
- [ ] 8.5 Attach the papers a stored record lists as result or derived, with the registry's kind, never background, and store a link the record gives on a listed outlet as a link lead; verify tests for each kind and for a link on an unlisted domain
- [ ] 8.6 Treat a fit acronym and a registry number as strong links in the offline linking; verify tests for an acronym in a headline and a number in an address, and record here how many stored leads link to each set
- [x] 8.7 Done in phase 1 as 9.4 to 9.7, with one difference: the numbers of many trials go in one request (fifty by default), not one request a trial, and each paper's own record is read back to say which trial it belongs to. Was: write PubMed's entry in `docs/sources.md` from its current pages, including the usage-policy chapter that could not be read on 2026-11-16, then its client with recorded fixtures, "nothing found" stored; verify no paper with more than three numbers is attached and none that only mentions the number. Still open: asking a trial again after a configured age
- [ ] 8.8 List attached papers on the trial page under the two fixed headings with paper facts; verify a test that a paper leaves the no-report line in place and that the page states nothing of what a paper found
- [ ] 8.9 Build the batched news search as a step: fit terms only, the number of trials a request as a setting starting at ten, a request cut short asked again in halves, a timed-out request leaving its trials due, a hit tied only on headline or address, untied hits counted and dropped; verify with recorded fixtures on synthetic headlines
- [ ] 8.10 Try title-only search on three requests of ten trials when the index is not slow, and record here whether it answers faster and how many hits tie; keep it only if it does
- [ ] 8.11 Run the batched search for `completed-with-results-since-2025`, then judge 40 tied hits by hand; record here the requests, time-outs, stories, ties and the judgement, and stop to tell the operator if fewer than half name the trial's own treatment
- [ ] 8.12 Print the plan of `specs/trial-coverage` before any route runs; verify tests of a plan, of a route that is off, and of a route turned on with no dated entry for its source
- [ ] 8.13 Verify with one test for each route that a found article is a lead and nothing more: no claim, source article, match or event exists until it is read, a rejected lead is not read, and a drafted claim is held awaiting audit
- [ ] 8.14 Not in phase 1. Questions 11, 13 and 14 were decided on 2026-11-17 as "not now"; only after the operator's two emails are answered and a route is turned on: write the entry in `docs/sources.md`, then the client, for a wire's feeds, a full-text search or a mentions index; verify each is off by default

## 9. Phase 1: the free routes (decided 2026-11-17)

The first phase built: routes 1 to 3 of `design.md`, decision 13. No spend, no new paid source, and no request but to PubMed. One pull request a group, each with its tests, its requirement deltas and the commands to run after it merges. A task here says which earlier task it does, in whole or in part; what it leaves of that task stays open there.

Route 1, the registry's own references (pull request 2; part of 8.5):

- [x] 9.1 Read from each stored record the papers it lists, result and derived kept apart from background, and the links it gives; verify tests for a record with each kind, a paper listed twice, a number that is not a number, and a record with no references
- [x] 9.2 Count, for each of the two sets, the trials with a result paper, with a derived paper, with either, the papers, and the links by domain and by whether the domain is a listed outlet, from stored records and with no request (`thenwhat backfill trial-references`); verify one test of the figures and one that an unknown set is refused with the list
- [x] 9.3 Record how a listed paper becomes a paper record: by the one rule and the one store a claim's results papers already use, and by no other path; verify a test that the papers read for a stored trial are those the claim path reads for the same record. Storing a link on a listed outlet as a link lead (the rest of 8.5) waits for the counts of 9.2

Counted on the working database on 2026-11-17, read-only, from stored records:

| | `active-since-2025` | `completed-with-results-since-2025` |
| --- | --- | --- |
| Trials | 23,328 | 3,141 |
| List a paper as reporting results (sponsor) | 597 (2.6%) | 190 (6.0%) |
| Have a paper the registry linked from PubMed | 2,845 (12.2%) | 1,083 (34.5%) |
| Either | 3,350 (14.4%) | 1,206 (38.4%) |
| Background papers only | 1,652 | 259 |
| Distinct papers: sponsor's, registry's (a paper both ways counted in each) | 3,424, 4,447 | 532, 2,070 |
| Give a link | 3,402 trials, 4,522 links | 639 trials, 861 links |

The fifteen most linked domains across both sets are sponsors' trial sites, hospitals and file hosts (mdanderson.org 502, mskcc.org 323, a sponsors' file host 288, merckclinicaltrials.com 262, clinicalstudies.info.nih.gov 240, pubmed.ncbi.nlm.nih.gov 213). None is a listed outlet. So no link becomes a link lead in phase 1: the rest of 8.5 stays open until `thenwhat backfill trial-references` shows a listed outlet among them.

Route 2, papers by trial number (pull request 3; does 8.7):

- [x] 9.4 Write PubMed's entry in `docs/sources.md` from NCBI's current pages, with the date, the pages read, the key, the tool and email parameters, the limits and the off-peak rule, before the client; add the settings to `.env.example`
- [x] 9.5 Write the client: the numbers of many trials in one request, exact, in the field the publisher supplied; each paper's own record read back, and a paper given to a trial only when that record carries the trial's number; refuse to run without what the terms require; verify with recorded fixtures (generic client name, no abstract, no author) a paper for one trial, a paper naming more than three numbers, a trial with no paper, and the refusal
- [x] 9.6 Store each paper found for a trial with its source, identifier, reduced raw payload and fetch time, in a migration numbered after `main`'s head; make it a step of the work ledger over the two sets, so a run resumes and a trial already asked is not asked again, "nothing found" included; verify tests of a run, a second run that sends nothing, and a run stopped by the allowance
- [x] 9.7 Ask for a sample of at most 50 trials across the two sets, with the generic client name, and record here how many of each set's sample have a paper

The sample of 9.7, asked on 2026-11-17 with a generic client name, no key, in 4 requests (2 searches, 2 fetches): 25 trials drawn by a seeded order from each set.

| Set | Trials asked | With a paper that carries the number | Papers |
| --- | --- | --- | --- |
| `active-since-2025` | 25 | 4 (16%) | 6 |
| `completed-with-results-since-2025` | 25 | 10 (40%) | 12 |

One paper carried three numbers and none more, so the rule against papers of many trials removed nothing. Twenty-five trials is a small sample: the figures say the route is worth running, not what it will give. Still open of 8.7 and "Nothing found is an answer": asking a trial again after a configured age; today a trial asked is not asked again until the step's version is raised.

Route 3, stored leads on more than the intervention's name (pull request 4; does 3.1 and 3.3, part of 3.5, 3.6, 3.7, 4.1 to 4.3 and 8.6):

- [x] 9.8 Link a stored lead to a trial on the trial's registry number, its acronym, a development code among its intervention names and other names, and its other intervention names, each as its own reason with its own strength, with the term and the condition word recorded; an acronym that is an ordinary word never links; the present link is kept as a candidate; verify tests for each reason, for a code written without its hyphen, for a common-word acronym, and that a run sends no request and records no usage
- [x] 9.9 Measure on the working database, read-only, how many leads link to how many trials of each set under each reason, and judge 40 links by hand from headline and outlet alone; record the tables here and in `design.md`, and nothing of any article
- [x] 9.10 Say which strength is enough for a held lead to be read, and make the reading order selectable for a named set: leads strongly linked to trials of the set first, phase 3 before phase 2, a rejected lead never; verify tests for a held lead, a rejected lead and the order of three due leads
- [x] 9.11 Hold the route's share of the ceiling as a setting (15 US dollars a month), print the plan of `specs/trial-report-links` before a set is read, and read nothing when the expected cost passes what is left of the share; verify tests of a plan and of a refusal

What 9.9 measured, on the working database on 2026-11-17, read-only, with no request: 558,864 leads in scope against 467,064 stored trials. 18,913 development codes were gathered over 58,014 trials, and 3,658 acronyms that carry a number. "Leads" and "trials" are those linked under the reason; the two sets are counted inside the totals.

| Reason | Strength | Leads | Trials | `active-since-2025`: leads / trials | `completed-with-results-since-2025`: leads / trials |
| --- | --- | --- | --- | --- | --- |
| The registry number in the title or address | exact | 0 | 0 | 0 / 0 | 0 / 0 |
| A development code and a condition word | strong | 13 | 32 | 9 / 16 | 1 / 1 |
| A development code alone | named | 13 | 42 | 6 / 8 | 1 / 1 |
| An acronym that carries a number, and a condition word | named | 0 | 0 | 0 / 0 | 0 / 0 |
| Another name of a drug or biological, and a condition word (at most 10 trials a name) | candidate | 611 | 742 | 237 / 216 | 34 / 23 |

Where triage left the leads linked to `active-since-2025`: of the 9 strongly linked, 6 passed and 3 were held, 4 are to phase 3 trials, and 3 are neither read nor rejected; 10 of the 13 strongly linked leads overall were already read. Of the 237 linked on another name, 170 passed, 45 were held, 13 were rejected and 9 are not scored; 136 are to phase 3 trials and 45 are passed and not yet read. For `completed-with-results-since-2025`: 20 passed, 8 held, 5 passed and not yet read.

The forty links judged by hand, drawn by a seeded order, each from the lead's headline and outlet against the trial's registry title; nothing of any article was read or written anywhere:

| Reason as first tried | Judged | Right treatment and right condition | Plainly that trial or its programme |
| --- | --- | --- | --- |
| A development code and a condition word | 8 | 8 | about 4 |
| A development code alone | 4 | 3 (one was a map's number) | 0 |
| An acronym of five letters or more with no number, and a condition word | 8 | 1 (a product's name; seven were ordinary words) | 0 |
| An acronym with no number, alone | 4 | 0 | 0 |
| Any other intervention name and a condition word | 16 | 1 (eleven were ordinary words or classes, "cancer" among them) | 0 |

What the judgement changed before the rule was fixed: an acronym with no number never links (under the loose rule 3,495 leads were linked on an acronym alone, 2,483 of them rejected by triage); another name links only for a drug, biological, genetic or combination intervention and never when it holds a general word. Sixteen more links on other names were judged after that change: 10 of the 12 not on "cancer" named the right treatment and condition and none was plainly that trial; the four on "cancer" are now left out.

What 9.10 says: only an exact or a strong link is enough for a held lead to be read. A named or candidate link orders reads and can be asked for by `--strength`, which widens which passed leads `thenwhat backfill read-set` reads and never which held leads. So "the leads strongly linked to the active set, phase 3 first" is, today, about 3 leads to read; with `--strength candidate` it is about 45. The route's yield from stored leads is small, and is recorded here as a finding, not a fault of the rule: the leads were gathered by what readers shared, and few headlines hold a code.

Still open of the tasks this pull request touches: 3.1's run over the working database (the screening step is at version 3, so every lead is due; the coordinating session runs it), 3.2 and 3.4 (a substance's name as telling), 4.4 (linked trials handed to preparation), 4.6 and 4.7 (working a set).

Not in phase 1, and still open where they stand: telling names from the substance registry (3.2, 3.4), handing linked trials to preparation as candidates (4.4), papers on the trial page (8.8), fingerprints as a stored record (8.3), the batched news search (8.9 to 8.13), everything of sections 2.4 to 2.8 and 6.

## 7. Records

- [ ] 7.1 Revise `CLAUDE.md`'s guardrails and layout: a trial page, the daily load and what it never starts; verify no line still says a registry trial is never shown
- [ ] 7.2 When `social-link-backfill` is synced, fold the held-on-a-strong-link case and the reading order into `lead-reading`; verify `openspec validate` passes for both
- [ ] 7.3 Add fingerprint, fit term and the two sets to `GLOSSARY.md`, and revise "Results paper" if papers that carry the number are shown; verify the terms match `specs/trial-coverage`
