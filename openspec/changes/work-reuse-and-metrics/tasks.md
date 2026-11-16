# Tasks

## 1. Decisions before code

- [x] 1.1 Ask the operator for the required recall of the prefilter, the tolerance for a reshaped triage call, and how many days single-step measurements are kept; verify each is in `design.md` in place of its open question and in `.env.example` with no default Answered 2026-11-16: recall 99%; tolerance 98% in the same band and no passing lead rejected; 30 days, and 7 for readers' lookups. In `design.md`; `.env.example` follows with the settings in section 2 and 5
- [x] 1.2 Ask the operator whether they will label a sample of leads or an assistant's labels, marked as such, are used; verify the answer is in `design.md` Answered 2026-11-16: an assistant labels about 1,000, marked assistant-made, and the operator checks 50
- [ ] 1.3 Read the terms, limits and price of Workers Analytics Engine and write its entry in `docs/sources.md`, or record that logs are used in its place; verify the entry or the decision exists
- [ ] 1.4 Add span, trace, unit of work, stored result, prefilter and settled to `GLOSSARY.md`; verify the terms match the specs

## 2. Measurements

- [x] 2.1 Write the measurement module: a span with the fields of `specs/processing-metrics`, a trace identifier from the address key and the run or request, and a recorder a step wraps its work in; verify tests cover a success, a failure, time waiting kept apart from time running, and an answer from a stored result Done 2026-11-16: `thenwhat/measure/spans.py`. A step wraps its work in `measured`; a model call's cost, a request to a source and a wait for a turn are added to the open span where they happen (`llm/ledger.py`, `sources/base.py`, `extract/retrieve.py`), so no step counts its own. A span opened inside another is measured apart and its time and cost are not counted twice. Tests in `tests/test_measure.py`
- [ ] 2.2 Record spans from triage, reading, registry and paper search, match decisions and prepare in the present pipeline; verify one end-to-end test of a synthetic lead yields a span for each step, linked by one trace Recording is in place as of 2026-11-16 for every ledger step through the runner (triage, reading, screening, news search), every decision, the registry search, the paper search, a claim's own reads and prepare. Tested through the real triage step (one measurement for a call, naming each lead) and the real read step (the read and every decision inside it under the lead's address key, the page reader's request counted), and by wiring tests for the claim-level functions. Not yet written, which is why this stays open: the one end-to-end test that follows a single synthetic lead through every step. Triage and reading have their fakes in different test files; that test needs them brought together
- [ ] 2.3 Record spans from the lookup Worker's steps; verify with a test that no span holds a network address, a user agent, or anything the reader's browser sent Not started, for two reasons to settle first. Where the Worker's measurements go is task 1.3, which is open. And the lookup service's rule that it logs no address stands (`cloudflare-source-of-truth`, `specs/live-lookup`), so a lookup's measurements cannot be written to the Worker's logs with the article's address in them: either they go to a store, or they are kept without the address and a lookup cannot be followed by address
- [x] 2.4 Keep single-step measurements for the set number of days and remove them after; verify a test of both Done 2026-11-16: one file a day and a kind in `MEASURE_DIR`; `remove_old` removes work files after `MEASURE_KEEP_DAYS` and lookup files after `MEASURE_LOOKUP_KEEP_DAYS`, and `thenwhat measure` adds a day into the totals before removing anything. Neither setting has a default: with the folder set and either empty, nothing is measured and each command says so
- [x] 2.5 Add the daily totals by day, step, version, writer and outcome, and the sum for each published claim; verify a test that a thousand spans become the expected totals and no row for each span Done 2026-11-16: migration `0025` adds `measure_daily`, `measure_claim` and `measure_rolled_day`. A finished day is added once; a claim's sum takes the spans of its source articles' address keys and of its own slug, and a call that covered twenty leads gives each a twentieth
- [x] 2.6 Add `thenwhat measure` with the reports of `specs/processing-metrics`; verify one test of its figures on seeded spans and one of its message when the range is empty Done 2026-11-16: `thenwhat measure [--days N | --since D --until D]`
- [x] 2.7 Use measured cost in the plan a step prints where a week of measurements exists; verify a test with and without them Done 2026-11-16: `backfill plan` says whether a cost is measured or estimated. Measured means seven or more days of totals for the step in the last thirty, and counts the cost of what was measured inside the step, which is where a decision's model call is recorded
- [ ] 2.8 Run the present pipeline with measurements for a week, or over one batch of 200 reads, and record here: time running and waiting by step, cost by step, the slowest sources, and the cost and time of a published claim; show the operator before section 3

## 3. The triage call

- [ ] 3.1 Draw a fixed sample of 2,000 stored leads across the score range and record its present scores; verify the sample's identifiers and the draw's seed are stored, with no title in the repository
- [ ] 3.2 Try the three shapes of `design.md` decision 6 on the sample; record here, for each, input tokens for a headline, cost, time, and agreement with present scores
- [ ] 3.3 Adopt a shape only if at least 98% of the sample falls in the same band and no passing lead is rejected, under a new triage version; verify the recorded fixture for the decision backend is re-recorded on synthetic titles and the tests pass with no live call

## 4. Stored results

- [ ] 4.1 Add the table of results by kind and key to the store's schema (`cloudflare-source-of-truth` task 3.2), with the run that made each and, for a negative result, its time to be asked again; verify the schema applies and a test stores and finds one result of each kind
- [ ] 4.2 Write the key for each kind of work as a pure function; verify tests that two writers get the same key, that a tracking parameter does not change it, and that a version change does
- [ ] 4.3 Look for a stored result before each unit of work and store the result after, negative results included; verify tests for a read reused by a lookup, a match decision not asked twice, and a registry search not sent again before its time
- [ ] 4.4 Make a result stale by version, by a changed payload checksum, or by time, and by nothing else; verify a test of each and of a result that stays current
- [ ] 4.5 Verify with a test that no stored result of a read or a page fetch holds any text of the article
- [ ] 4.6 Carry the keys a run can use in the reference file and push the results a run made (`file-based-backfill` tasks 3.1 and 6.2); verify a test of a second run that repeats none of the first run's work
- [ ] 4.7 Keep each outlet's rate of readable pages and its waiting time; verify a test of ten failures setting a wait, other outlets being read meanwhile, and a success ending it
- [ ] 4.8 Report reuse in `thenwhat measure`; verify the share of lookup match decisions answered from stored results is recorded here after a day of lookups in preview, beside the 59% repeated today

## 5. Rules and the classifier

- [ ] 5.1 Record the free signals for each lead in the load and screening, and keep each outlet's pass rate from stored scores; verify tests for a known outlet, a new outlet, a section in the address and a topic word
- [ ] 5.2 Order triage and reading by the signals; verify a test of the order, and that no lead is dropped by a signal
- [ ] 5.3 Train a linear classifier on stored triage scores with a held-out set, and record its recall and the share it settles at each threshold beside the probe's figures in `design.md` decision 5; verify the record names the sizes of both sets, uses more than one split, and holds no title
- [ ] 5.4 Score the 560 assistant-labelled leads with it and record the figures as the independent check; draw about 1,000 headlines without scores shown (300 the prefilter would settle, 300 held, 200 passed, 200 rejected), label them with `--as-assistant`, give the operator 50 to check, and record the figures again with how often the operator's 50 agreed
- [ ] 5.5 Add the prefilter stage before triage: settle below the threshold that meets the required recall, with the classifier's version and probability on the lead; verify tests for a settled lead, an unsure one, no recall configured, and a classifier that cannot meet it
- [ ] 5.6 Send the set share of settled leads to the decision step, stop settling when the sample disagrees, and leave the leads settled since the last good sample due; verify a test of a steady sample and of a drifting one
- [ ] 5.7 Send a settled lead to the decision step when a new classifier version would not settle it or the operator names it; verify a test
- [ ] 5.8 Run the prefilter over one month of leads beside full triage and record here: leads settled, model calls saved, and passed or held leads it would have dropped, by name of outlet only; show the operator before it is turned on

## 6. Reading

- [ ] 6.1 Order reads by topic, score, the outlet's rates and shares; verify a test of the order
- [ ] 6.2 Group leads with the same tidied title on different outlets within the set number of days, read one, and put the others to the same-claim decision; verify tests for a group whose first read drafts a claim, and for a grouped article the decision turns away being read in its own turn
- [ ] 6.3 Count near-matching titles in the stored leads and record the figure here before deciding whether grouping goes beyond exact matches

## 7. Close

- [ ] 7.1 Record in this change, from `thenwhat measure`, the cost and time of a published claim and the cost of a thousand leads before section 3 and after section 6; verify both sets of figures come from measurements and name their date ranges
- [ ] 7.2 Describe measurements, stored results and the prefilter in the README's pipeline section and add the settings to `.env.example`; verify `make check` passes
- [ ] 7.3 Write the delta to `lead-triage` once `social-link-backfill` is synced: not every in-scope lead reaches the decision step; verify it is named here
