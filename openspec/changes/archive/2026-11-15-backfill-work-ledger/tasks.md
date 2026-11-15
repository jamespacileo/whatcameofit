# Tasks

## 1. Choose the news index

- [x] 1.1 Read the current terms, authentication, rate limits and coverage of GDELT's bulk datasets, Media Cloud and Common Crawl's news crawl, and write an entry for each in `docs/sources.md` with the date checked; verify each entry states whether bulk search by keyword is permitted and at what rate
- [x] 1.2 Pick one index, or record that none qualifies, in `design.md` decision 8 and tell the operator; verify the decision names the source, its allowance and what the operator must set up (account, key), or states plainly that the step will not be run live
- [x] 1.3 Add the bulk use of ClinicalTrials.gov's list endpoint to its entry in `docs/sources.md`; verify the entry gives the page size, the request count for a full load and the rate used

## 2. Ledger and steps

- [x] 2.1 Add migration `0014` for the `work_entry` table with its unique key on record kind, record id, step and step version, together with the other tables this change adds (design decision 10); verify `alembic upgrade head` then `alembic downgrade -1` both succeed on the test database
- [x] 2.2 Add the `thenwhat/backfill` package with the step shape, the list of registered steps and the duplicate-name check; verify a test registers two steps with one name and the check refuses
- [x] 2.3 Implement the due-work query (in scope, no finished entry at the current version, or a different fingerprint); verify tests against the test database cover finished records skipped, a changed fingerprint, a record out of scope, a new step and a raised version
- [x] 2.4 Implement the runner: lock a due record with skip-locked, run the step, save the result and the entry together, commit per record; verify tests cover a failure on one record of ten, the attempt limit, and a step that raises part way leaving none of its partial result and an entry that records the failure
- [x] 2.5 Verify with a test that two sessions running the same step over 100 due records process each record once
- [x] 2.6 Add step, work ledger and due to `GLOSSARY.md`; verify the terms match the words used in the CLI output and the specs

## 3. Source allowances

- [x] 3.1 Add settings for each source's allowance (requests per period, least interval, pause when refused) to the configuration and `.env.example`; verify a step whose source has no allowance refuses to run and names the missing setting
- [x] 3.2 Add the allowance use table to migration `0014`; verify upgrade and downgrade on the test database
- [x] 3.3 Implement claiming a request against an allowance in one transaction, with spacing between requests; verify tests using two sessions and a fake clock show the shared count holds and no two requests are closer than the least interval
- [x] 3.4 Implement the used-up and refused cases: stop asking, leave records due, do not count an attempt, record the pause; verify tests cover running out mid-run, a too-many-requests answer, and a restart within the same period

## 4. Registry corpus

- [x] 4.1 Add the `registry_trial` table and the load state table to migration `0014`; verify upgrade and downgrade on the test database
- [x] 4.2 Record fixtures of two list-endpoint pages with a generic client name; verify the fixtures contain no contact address
- [x] 4.3 Implement the paged load with a condition, storing each trial once with its raw payload and fetch time; verify tests against the fixtures cover a first load, a repeat load that updates in place, and a load resumed after stopping on the second page
- [x] 4.4 Implement loading changes since the previous completed load; verify a test shows the request carries the previous load's date and that an updated trial's fingerprint changes only when a field a step reads changed
- [x] 4.5 Add `thenwhat backfill load-trials`; verify one test of a successful load and one of the refusal when no contact address is configured
- [x] 4.6 Verify with a test that the export is byte-for-byte the same before and after a load
- [x] 4.7 Add registry trial to `GLOSSARY.md` and describe the load in the README's pipeline section; verify the documented command runs as written against the Compose stack

## 5. Plan and run commands

- [x] 5.1 Add `thenwhat backfill steps` and `thenwhat backfill plan`, reporting per step the records in scope, done, nothing found, failed, due, requests needed, allowance left and hours; verify a test checks the figures for a seeded database and that no request is sent
- [x] 5.2 Add `thenwhat backfill run <step>` with a record limit and a worker count; verify one test of a limited run reporting what remains due and one of the refusal for an unknown step
- [x] 5.3 Verify with a test that a run stopped after some records and started again repeats none of them

## 6. News search step and article leads

- [x] 6.1 Add the `article_lead` table, unique on trial and address, to migration `0014`; verify upgrade and downgrade on the test database
- [x] 6.2 Implement choosing the intervention name for a search (no placebo, comparator, dose, form, route or description) and the indication words; verify tests use the 200 sampled trials' registry fields as cases, including the ones the sample could not name
- [x] 6.3 Write the client for the index chosen in 1.2, with removal of any excerpt, summary or text field before a result is stored or logged; verify tests use synthetic fixtures only and one asserts that a result carrying an excerpt is stored without it
- [x] 6.4 Implement the news search step: scope, inputs, search, leads stored once per trial and address, outcome done or nothing found; verify tests cover coverage found, none found, the same article found twice, and one article found for two trials
- [x] 6.5 Check whether the outlet list behind `docs/outlets.md` can carry an outlet kind, add the kind there or in one new checked-in list, and set each lead's kind by rule from its domain; verify tests cover a general outlet, a trade outlet, a press release wire and an unlisted domain
- [x] 6.6 Add `thenwhat backfill leads`, the hit rate report by outlet kind; verify one test of the report's counts and percentages on seeded leads and one of its message when no trial has been processed
- [x] 6.7 Verify with a test that the export is the same before and after leads are stored
- [x] 6.8 Add article lead to `GLOSSARY.md`, stating that a lead is not a source article; verify the entry and the spec use the same words

## 7. First run

- [x] 7.1 Run `make check`; verify ruff, ty, pytest and the site build pass
- [x] 7.2 Load the phase 3 drug and biological trials on the operator's machine and run `backfill plan`; verify the trial count is close to 43,320 and record the plan's figures in this change
- [x] 7.3 Run the news search with a limit of 200 and `backfill leads`; verify the hit rate is recorded here beside the sample's 52% overall and 20% trial-specific (31% and 16% after one search per trial), with the split by outlet kind
- [x] 7.4 Stop a second limited run part way and start it again; verify the report shows no record processed twice
- [x] 7.5 Give the operator the 200-trial figures and the plan for the full run, and wait for a decision before running without a limit

## First run: what was done on 2026-11-14

- **Where:** a separate database, `thenwhat_backfill`, on the Compose Postgres server. The operator's `thenwhat` database was not migrated: other worktrees share it, and they do not have migration `0014` until this branch is merged.
- **Load (7.2):** `thenwhat backfill load-trials` stored 43,320 trials in 44 requests, in 1 minute 44 seconds. The sampling frame was 43,320.
- **Plan (7.2):** 40,006 of the 43,320 trials (92%) have a usable name and indication and are in the news search's scope. They need 40,006 requests: about 333 hours at 30 seconds apart, and 11 weekly allowances of 4,000.
- **A fault the live run found:** `load-trials --changes-only` read the previous load's date after its transaction had closed. Fixed, with a test that runs the load on separate committed transactions.
- **Before the key existed:** `thenwhat backfill run news_search` refused with "MEDIACLOUD_API_KEY is not set" and touched no record, as specified.

## Limited run: what was done on 2026-11-14 (7.3, 7.4, 7.5)

- **Which trials:** the 200 trials of the web-search sample (`docs/research/phase3-article-hit-rate`), loaded by their identifiers into their own database, `thenwhat_backfill_sample`, so that the two results are for the same trials. 186 of the 200 have a usable name and indication and were in scope. The operator's `thenwhat` database was not written to.
- **What was searched:** the United States and United Kingdom national collections (`34412234`, `34412476`) and twenty clinical trade outlets by id, in one search per trial.
- **A fault the live run found:** Media Cloud refuses a search that names neither a collection nor an outlet (status 422). The client now takes outlet ids beside collection ids and refuses before any record is touched when both are empty.
- **Result (7.3):** 180 trials were searched; 6 got no answer within 60 seconds on two attempts each and are still due.

| Measure | Media Cloud, one search | Web-search sample, same 180 trials |
| --- | --- | --- |
| At least one article lead | 148 (82%) | a news article on the intervention for the indication: 97 (54%) |
| A lead from a general news outlet | 100 (56%) | |
| A lead from health or clinical trade press | 104 (58%) | |
| A lead from a press release outlet | 11 (6%) | |
| A lead from an outlet on no list | 128 (71%) | |
| A lead whose title holds the intervention's name | 55 (31%) | a news article about that trial: 40 (22%) |
| The same, from a general news or trade outlet | 44 (24%) | |
| The same, from a general news outlet | 19 (11%) | |

  The sample's figures for all 200 trials are 52% and 20% (31% and 16% after one search per trial).
- **How to read it:** the two columns do not measure the same thing. A lead is any story that holds the intervention's name and one word of the indication anywhere in it; nobody judged whether the story reports the intervention for the indication. The sample's figure is a judgement of the best result's title. So 82% is an upper bound, and the title rows are a strict lower bound. The two methods also find different trials: of the 180, both found something for 83, only Media Cloud for 65, only the web search for 14.
- **Outlets:** 2,161 leads. biospace.com gave about two thirds of the trade press leads; healio.com, onclive.com and fiercepharma.com gave none, because Media Cloud no longer collects them. Market wires (benzinga.com, thestreet.com) and prnewswire.co.uk rank high among outlets on no list; prnewswire.co.uk has since been added to the press release list.
- **Stop and restart (7.4):** Media Cloud answered "too many requests" after 136 searches, and the run stopped itself with 61 records due and a pause until 19:27 UTC. Started again after the pause, it processed those 61 and nothing else. The ledger holds 186 entries for 186 records; the 175 finished before or after the stop with one attempt were asked once, and the only records asked twice are the 11 that failed the first time (ten timeouts and the one refused search). No trial has the same address twice.
- **Requests:** 197 by the pipeline, and about 30 more by hand to read the directory and one refusal, which the pipeline's count does not include.
- **For the operator (7.5):** the full run is 40,006 trials, one search each: 11 weekly allowances at the default, longer if Media Cloud refuses again at 30 seconds apart. It has not been started and waits for the operator's decision. Open points for that decision: about 8% of searches time out at 60 seconds and are retried; the trade press that reported most trials in the sample is largely not collected by Media Cloud; and a lead is not checked for relevance by this change.

## Full run: started on 2026-11-14

- **Decision:** the operator chose to run the news search over every trial in scope.
- **Set going:** the real database was backed up, 43,320 trials were loaded (40,006 in scope), and the launchd agent `com.thenwhat.backfill` (`scripts/backfill-job.sh`) was installed to start the run every half hour. The allowance is 3,750 searches a week, 30 seconds apart: eleven weeks.
- **Where to follow it:** `docs/lookup.md`, "The registry-first backfill: the full news search", which also takes the first allowance's figures when it has been used.

## Workflow follow-up

- Archive the change after the operator has decided on the full run.
- Propose the next steps (social posts, paper matching, turning leads into claims) as their own changes.
