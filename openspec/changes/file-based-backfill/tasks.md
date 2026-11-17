# Tasks

## 1. Decisions before code

- [x] 1.1 Ask the operator whether preparing and auditing a batch stay store-side (`design.md` decision 9); verify the answer replaces the open question Answered 2026-11-16: store-side, and the audit hold stays for backfill batches
- [x] 1.2 Ask the operator for each device's share of the monthly ceiling; verify the figures are in `design.md` decision 6 and `.env.example` names the setting with no default Answered 2026-11-16: 100 US dollars in all; store-side 40, Mac mini 30, MacBook Pro 30
- [x] 1.3 Ask the operator whether leads that were screened and never scored are pushed; verify the answer is in `design.md` decision 8 and `specs/backfill-run-files` agrees Answered 2026-11-16: no. Every scored lead is pushed, rejected ones included; a lead never scored is not
- [ ] 1.4 Add run, stage, reference file, tally and work slice to `GLOSSARY.md`; verify the terms match the specs
- [ ] 1.5 Add the dataframe library of `design.md` decision 2 to the pipeline's dependencies; verify `make check` passes with it installed and nothing yet imports it outside `backfill/run/`

## 2. Run folder and load

- [ ] 2.0 Add `BACKFILL_DATA_DIR` and `BACKFILL_RUNS_DIR` to the configuration, `.env.example` and `scripts/fetch_link_files.py`, with no default inside the repository, and refuse to start when the folder's volume is not mounted; verify one refusal test, and that the files already in `data/link-files/` are moved to the external volume on the Mac mini with the operator's yes and their sizes checked after the move
- [ ] 2.1 Write the run folder: `run start`, the run record, temporary-name-then-rename writes; verify tests that a run records its inputs' sizes and that an interrupted write leaves no file under its final name
- [ ] 2.2 Write the load stage over the existing readers, address key and outlet kinds, writing shares on listed outlets only; verify a test with synthetic posts on a listed and an unlisted outlet writes one share
- [ ] 2.3 Write the tally with the topic-word count; verify a test that it holds domains and counts only, and that no other file of the run holds an unlisted link
- [ ] 2.4 Add the reconciliation, the quarantine, `LOAD_ERROR_BUDGET` and the field check; verify tests for counts that disagree, one malformed Reddit line (quarantine holds file, line and error kind only), a file over budget, and a parquet file with no `url` column
- [ ] 2.5 Add `--dry-run`; verify one CLI test that it prints the report and writes only the tally
- [ ] 2.6 Verify with a test that a Reddit line carrying an author, an id, a permalink and text leaves none of them in any file of the run
- [ ] 2.7 Dry-run the 23 Hacker News files and the Reddit files in `data/link-files/`; record the counts here beside the figures in `design.md` and show the operator the tally's top domains and topic domains
- [ ] 2.8 Draw up the domains for the four groups the operator chose on 2026-11-16 (`design.md` decision 3) from the tally and show the operator the lists; add the outlet kinds journal or paper index, regulator, video and social, and the screening outcome awaiting a route; verify each domain is in `backfill/outlet_kinds.py` with its kind, the list's version is raised, and a test shows a journal's link kept, not scored and not read

## 3. Reference file

- [ ] 3.1 Agree the reference file's contents with `cloudflare-source-of-truth` and write its reader; verify a test against a synthetic file that it holds no payload, title or decision
- [ ] 3.2 Write `backfill reference pull` and have `run start` pull by default; verify one CLI test of a pull against a fake ingest address and one of the refusal when none was ever pulled
- [ ] 3.3 Warn when a run's reference file is older than seven days; verify a test
- [ ] 3.4 Until the truth store exists, write a one-off script that makes a reference file from the present database; verify it is in `scripts/`, says it is temporary, and is named in section 8 for removal

## 4. Screen and triage

- [ ] 4.1 Split screening into a pure function over rows and a stage that reads and writes files; verify the function's tests cover a listed outlet, an address that is a source article with a tracking parameter, a lead read elsewhere, a title naming a claim's intervention, and a name inside a longer word
- [ ] 4.2 Verify with a test that screening sends no request, calls no model and writes no usage
- [ ] 4.3 Write `backfill run report` from the run's files and tally; verify tests of its counts and of its message when nothing is screened
- [ ] 4.4 Split triage into the decision call and a stage that writes one part a batch and one usage line a call; verify with the fake backend a scored batch, a refusal for one lead that leaves the others scored, and a stop after two batches that resumes with the third
- [ ] 4.5 Leave out leads the reference file scores at the current version and copy their scores; verify tests for the same version and for a lower one
- [ ] 4.6 Take topic leads first; verify a test of the order
- [ ] 4.7 Write `backfill run plan` and the ceiling check against the run's usage plus the reference file's; verify tests for the ceiling reached part way, a restart that scores nothing, and the refusal with no price configured
- [ ] 4.8 Run load, screen and triage on one month of Hacker News with the reference file of 3.4, and compare outcomes and scores with the session-based steps on the same leads; record agreement and every difference here

## 5. Read

- [ ] 5.1 Split reading into the existing extraction and a stage that writes one line a read; verify tests for a read that drafts a claim, one that joins a tracked claim, a business-news outcome, and an article that cannot be read on three attempts
- [ ] 5.2 Leave out leads the reference file gives a read outcome for, read held topic leads, never read a rejected lead; verify a test of each
- [ ] 5.3 Verify with a test that no file of a run holds article text after a batch of reads, including after a failure part way through one
- [ ] 5.4 Write the prepare stage that turns reads into results in the merge's natural-key form (`store/README.md` lists each kind's keys), with drafted claims pending; it searches no registry and approves nothing, which the store's side does; verify a test round-trips each kind against the form `cloudflare-source-of-truth` defines
- [ ] 5.5 Read one batch of 200 and compare with the session-based read on the same leads; show the operator the funnel and the claims drafted before any further reading

## 6. Push

- [ ] 6.1 Add `INGEST_URL`, `INGEST_TOKEN` and `WORK_DEVICE_NAME` to the configuration and `.env.example`; verify push refuses and names the setting while one is empty
- [ ] 6.2 Write `backfill push`: put payloads over 16 KB, split into store runs of the set size with parents first, and for each register, hand over in parts with counts and checksums, merge and print the report; mark the folder pushed after the last; verify against a fake ingest address a first push, a second push answered as already merged, a part that fails its checksum, and a push stopped between two store runs and finished by pushing again
- [ ] 6.3 Add `--report-only`; verify the fake store holds nothing new after it
- [ ] 6.4 Verify with a test that nothing on an unlisted outlet and no tally row is handed over
- [ ] 6.5 When `cloudflare-source-of-truth` has its merge in preview, push the batch of 5.5 with `--report-only`, then for real; record the report here

## 7. Work slices

- [ ] 7.1 Write `backfill slices take|release|list` against the ingest address; verify one success and one refusal each against a fake
- [ ] 7.2 Have `run start` take the slices its files cover and warn for each held elsewhere; verify a test
- [ ] 7.3 State in a run's record which slices' files were processed whole, for the merge to mark done; verify a test of a run over part of a month that states none

## 8. Close

- [ ] 8.1 Describe the route in the README's pipeline section: fetch, start, dry run, load, screen, triage, plan, read, push, audit; verify the commands run as written on a device with no database
- [ ] 8.2 Record in `docs/sources.md` that unlisted links are no longer stored anywhere and where a run's tally and quarantine are kept
- [ ] 8.3 After two batches have gone through this route, remove the session-based link steps, `load-links` into a database and the script of 3.4; verify `make check` passes and the registry-first route's tests are untouched
- [ ] 8.4 Open a change for ordering the registry-first news search by trial status and completion date; verify it is named here
- [ ] 8.5 Open one change each for the routes the kept leads wait on: shared papers, regulators' notices, and video and posts; verify each is named here and says what a lead of its kind becomes
