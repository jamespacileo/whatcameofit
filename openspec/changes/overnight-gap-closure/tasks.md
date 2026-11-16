# Tasks

Each task names its lane and model. "Here" is the one session that writes to the working database.

## 1. Reddit backfill to the site (data lane, here)

- [ ] 1.1 Let the read run finish; confirm nothing readable is left and the 115 held leads were not asked
- [ ] 1.2 Prepare every pending claim
- [ ] 1.3 Audit round 2 with auditors on Opus 5.5 under the existing brief; decide their flagged cases here; apply
- [ ] 1.4 Attach each archived duplicate's articles to the published claim it duplicates, skipping pairs an auditor doubted
- [ ] 1.5 Export, stage the snapshot, run the deployment check, open the data pull request, merge on green, confirm a new claim's page answers
- [ ] 1.6 Record the batch on the improvement sheet: reads, drafted, cleared, archived by ground, spend

## 2. Pull requests in flight (code and specification lanes)

- [ ] 2.1 268 daily trial changes: re-read its fixes (rate-limit stop recorded as a pause; property list written owner-only); merge
- [ ] 2.2 271 read-step fixes: re-read its fixes (live overlaps listed; archived owner not joined; antigen not a name for matching; older records re-fetched; the vaccine signal's reach answered); merge
- [ ] 2.3 Claim merge and rename: review when opened; merge; do not run its commands tonight
- [ ] 2.4 270 trial-first: read the batching experiment's numbers; correct the news index's allowance count by its request total; merge as a document when coherent
- [ ] 2.5 273 D1 draft: read for internal consistency only; leave as a draft for the operator
- [ ] 2.6 Keep every approved branch current with main until merged; archive each session when its pull request merges

## 3. The wider trial record (code lane, Opus 5.5)

- [ ] 3.1 Ask the trial-first session which registry fields its routes need, and settle the field list
- [ ] 3.2 Delegate: load and store the activity and results fields, the acronym, other intervention names and the registry's references; one additive migration; fixtures re-recorded; a reload marks nothing due unless a listing field changed
- [ ] 3.3 Delegate in the same task: the two sets `active-since-2025` and `completed-with-results-since-2025` as selections over stored trials, with a command that counts them
- [ ] 3.4 Review and merge

## 4. Migrations and the rekey survey (data lane, here)

- [ ] 4.1 Confirm no read, prepare or load is running; pause the daily job
- [ ] 4.2 Dump the working database to the external drive; record its size and checksum; restore one table from it into a scratch database to prove it reads
- [ ] 4.3 Read migration 0028 and confirm it only adds; apply 0027 and 0028
- [ ] 4.4 Run the rekey survey; write for the operator how many leads would merge, how many shares move, how many claims' lead pointers are touched, and ten examples of each kind (addresses only)
- [ ] 4.5 Do not apply the rekey

## 5. Reload and count (data lane, here)

- [ ] 5.1 After 3.4 and 4.3: apply the wider record's migration; load every interventional trial again; confirm the count and that no step gained due records
- [ ] 5.2 Count the two sets, by phase; write the numbers for the operator
- [ ] 5.3 Resume the daily job on its existing checkout, by 04:15 UTC at the latest whatever else is unfinished

## 6. Hand-over

- [ ] 6.1 Write the morning list: rekey counts, set sizes, each open decision with its options, what was not done and why
- [ ] 6.2 Total the night: model spend, reader and registry requests used, pull requests merged, claims published
