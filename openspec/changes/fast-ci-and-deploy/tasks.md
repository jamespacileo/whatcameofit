# Tasks

Read `design.md` first. Strategy numbers (S1 to S9) refer to its table. Every figure in a task is checked with `node scripts/ci-timing.mjs`; "the ledger" is `openspec/changes/fast-ci-and-deploy/experiments.md`.

## 0. Pull request preview fast path (done on pull request 267, 2026-11-16)

- [x] 0.1 Keep drawn card images under the hash of the renderer's input (`site/src/lib/card-image.ts`, `site/tests/card-store.test.mjs`); verified: two builds, cold then warm, give byte-identical files, and the card routes fall from 76 s to 4.3 s in CI
- [x] 0.2 Give a preview the key of what it was made from at `/build-key.txt` and skip a push with the same key (`site/scripts/build-key.mjs`, `make pr-preview-state`, `site/tests/build-key.test.mjs`); verified: a notes-only push ran in 11 s and left the Worker as it was, a push changing `site/scripts` rebuilt
- [x] 0.3 Restore the installed dependencies and the card store in the preview job, and keep both from `CI and deploy` so `main` seeds every pull request; verified: restores take 2 s each, the CI rehearsal fell from 107 s to 19 s
- [x] 0.4 Record the behaviour in the `deployment` delta, `docs/deploy.md` and the ledger; verified: `openspec validate fast-ci-and-deploy --strict` passes
- [ ] 0.5 After this is on `main`, open a pull request that changes nothing under `site/` and one that changes one page; verify from the ledger that each one's first preview restored the stores kept by `main` and record both times
- [ ] 0.6 Decide with the operator which option in the ledger's verdict to take for a push that changes the site (50 s against a 20 s limit); verify the choice is recorded in `design.md` before work on it starts

## 1. Timing report and baseline

- [ ] 1.1 Write `scripts/ci-budgets.json` with the four scenarios' limits and targets from `specs/delivery-time/spec.md`; verify each number matches the spec's four scenarios
- [ ] 1.2 Write `scripts/ci-timing.mjs`: classify runs into scenarios, compute p50 and p90 over the last 20 successful runs, list the deciding path's steps and waiting largest first, exit non-zero on a missed limit; verify by running it against the live repository and comparing three runs' totals with `gh run view <id> --json jobs` by hand, each within 5 s
- [ ] 1.3 Add `scripts/tests/ci-timing.test.mjs` with synthetic recorded API answers covering: a deploying run, a superseded push, parallel jobs, a gap between jobs, fewer than 20 runs, a missed p90, a missed target only; add it to `make scripts-test`; verify `make scripts-test` passes and makes no network call
- [ ] 1.4 Split `make check` and the rehearsal into named workflow steps (one per `make` target) with no other change, so the jobs API shows each; verify the report's step list for a new run adds up to the run's wall-clock time within 5 s
- [ ] 1.5 Start the ledger with the baseline: the report's output for all four scenarios, and the proposal's table; verify the ledger's baseline p50 for pull request checks is within 30 s of the 268 s measured on 2026-11-16, or explain the difference in the ledger
- [ ] 1.6 Measure the floor: a `workflow_dispatch` workflow with one job that only checks out, dispatched ten times at two different hours; verify the ledger holds its p50 and p90 and the time of each batch
- [ ] 1.7 Document the report command, the budgets file and the ledger in `docs/deploy.md`; verify the command runs as written there

## 2. The guard

- [ ] 2.1 Write one deliberately broken patch per check in `scripts/tests/ci-canaries/` (lint, types, pipeline tests, script tests, site tests, site build, extension tests, deployment rehearsal) plus one that changes a file unlikely to be on any input list; verify each applies cleanly to `main` with `git apply --check`
- [ ] 2.2 Write the runner behind `make ci-canaries`: apply each patch on a scratch branch, push to one draft pull request per patch, wait for the checks, assert failure, close the pull request and delete the branch; verify that on the unchanged workflows all nine fail and the runner exits successfully, and that an empty patch makes the runner exit with a failure
- [ ] 2.3 Document `make ci-canaries` in `docs/deploy.md`, with the rule that it runs after every change to scheduling, skipping or reuse; verify the documented command runs as written

## 3. Parallel checks and one build (S1, S2, S8)

- [ ] 3.1 S1: split the `check` job into parallel jobs, keeping one required status that passes only when all do; verify with five paired dispatches that pull request checks' median is at or under 120 s, and record prediction and result in the ledger
- [ ] 3.2 S2: make building and publishing separable in `site/scripts/deploy.mjs`, with the deploy checks unchanged and still run before publishing; extend `site/tests/deploy.test.mjs` for publishing a given build and for refusing one whose digest differs; verify `make site-test` passes
- [ ] 3.3 S2: the rehearsal job uploads the built site with its digest and the deploy job downloads, verifies and publishes it through `make deploy-ci`, building afresh when it is absent or does not match; verify on one real push to `main` that the deploy job's log shows no site build and the live check passes, and record the deploy job's seconds in the ledger
- [ ] 3.4 S8: remove the deploy job's repeated install and separate `whoami` where the build's artifact or a cache can supply Wrangler; verify the deploy job's steps before publishing total under 8 s over five runs, or record the refutation
- [ ] 3.5 Run `make ci-canaries`; verify all nine fail and write the result in the ledger
- [ ] 3.6 Update `docs/deploy.md` for the new job layout and the once-built site; verify every command it gives still runs as written

## 4. Faster tests (S3, S6)

- [ ] 4.1 S3: find what the site's tests share that needed `--test-concurrency=1` (run them concurrently, read the failures), and write the finding in the ledger; verify the finding names the files or directories involved
- [ ] 4.2 S3: give each test file its own output and data paths and remove the flag; verify 20 consecutive green runs of `npm --prefix site test` locally or in CI and a median under 30 s in CI, or revert and record the refutation
- [ ] 4.3 S6: run the pipeline's tests across workers with one `_test` database per worker; verify 20 consecutive green runs and the same count of tests passed as before (1,795 on 2026-11-16, or the count on `main` at the time)
- [ ] 4.4 S6: shorten the database's start in CI (health check interval, no durability, no pull where the image is present); verify the database is healthy in under 6 s at the median over five runs
- [ ] 4.5 Run `make ci-canaries`; verify all nine fail and write the result in the ledger
- [ ] 4.6 Update the README's and `CLAUDE.md`'s test notes if a local `make check` now behaves differently; verify `make check` passes from a clean clone following the README

## 5. Reuse by input key (S4, S5, S7, S9)

- [ ] 5.1 Write the input list file: path patterns per check and the "read by nothing" list, failing closed for unlisted paths; add a test that every tracked path matches a check or the nothing list or triggers all checks; verify the test passes and that removing one pattern makes it report the unlisted paths
- [ ] 5.2 S4: compute each check's key from its inputs' blob ids, lock files, tool versions and settings; upload a pass record per key; add the `CI_REUSE` variable with `off`, `shadow` and `on`; verify in `shadow` that a run's summary lists, per check, the key and the earlier run that would have answered it
- [ ] 5.3 Run in `shadow` for 40 pushes to `main` or two weeks, whichever is first; verify the ledger records how many checks would have been answered, and that none of those then failed when run
- [ ] 5.4 S5: store the rehearsed build under its key and have a deploying run fetch it only from a run of this repository, verifying the digest; verify with a fork-style test (a recorded API answer whose `head_repository` differs) that it is refused
- [ ] 5.5 S7 (the store itself is done in 0.1 and 0.3; this is its measurement for production): verify a rebuild with an unchanged snapshot is under 30 s at the median over five runs and its output digest equals a build without the store, or record the refutation
- [ ] 5.6 S9: establish whether the registry search switch changes built files; if it can move to the Worker's settings, publish previews from the stored build through `make pr-preview`; verify a preview's pages still send the no-index header and its search still answers that it is not set up, and that preview publishing is under 90 s at p50
- [ ] 5.7 Run `make ci-canaries` with `CI_REUSE=on` on the scratch branches; verify all nine fail, including the forgotten-file patch, then set `CI_REUSE=on` for the repository
- [ ] 5.8 Update `docs/deploy.md` with the input list file, the `CI_REUSE` variable and how to turn reuse off; verify the rollback as written returns a run to executing every check

## 6. Discovery loop

- [ ] 6.1 After 20 runs per scenario with everything above in place, run the report; verify the ledger holds its full output and a met or missed mark for each limit and target
- [ ] 6.2 For every missed limit, run design decision 5 until the limit is met; verify each pass through the loop is a ledger row with step, hypothesis, predicted seconds, refuting observation, five-run medians before and after, and kept or reverted
- [ ] 6.3 For every missed target, run design decision 5 until the target is met, the floor rule fires, or three hypotheses in a row are refuted for each of the three largest steps; verify the ledger shows which of the three ended it for each scenario
- [ ] 6.4 Answer the merge queue question from design's Open Questions with the share of the last 40 `main` pushes it would have covered; verify the ledger holds the count and a recommendation
- [ ] 6.5 Run `make ci-canaries` after the last kept change; verify all nine fail

## 7. Verdict

- [ ] 7.1 Write a verdict per scenario into `specs/delivery-time/spec.md` as scenarios of "Each scenario ends with a verdict on its target", with the report's figures and, for any not met, the measured floor and the options with rough costs; verify `openspec validate fast-ci-and-deploy --strict` passes
- [ ] 7.2 If any limit is still missed, stop and tell the operator with the ledger's evidence before changing a limit; verify no limit in `scripts/ci-budgets.json` differs from the spec
- [ ] 7.3 Final integration check: `make check` locally, one real pull request through checks and preview, one real deployment with the live check, and the report exiting successfully; verify all four and record the run ids in the ledger

## Workflow follow-up

- Archive the change once the operator has read the verdicts.
- If the floor rule fired, the operator decides on the runner options listed with it; that is a new change.
