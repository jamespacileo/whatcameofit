# Proposal

## Why

A change takes about six minutes to go from a push on `main` to the live site, and about four and a half minutes to get a verdict on a pull request. The operator's target, set on 2026-11-16, is 10 to 15 seconds for a full run of the tests and the deployment. Nothing today measures where the time goes, states a limit, or says what to try next when a limit is missed.

Measured on 2026-11-16 from GitHub's own records (`gh run list`, `gh run view --json jobs`, and the timestamps in one run's log):

| Scenario | Runs | p50 | p90 |
| --- | --- | --- | --- |
| Push to `main` that deployed | 27 | 361 s | 456 s |
| Push to `main` passed over as superseded | 13 | 327 s | 361 s |
| Pull request checks | 60 | 268 s | 338 s |
| Pull request preview published | 26 | 146 s | 174 s |

Where one run of 297 s spent its time (run 43962555621, a `main` push that was passed over):

| Step | Seconds |
| --- | --- |
| Site tests: 687 tests, one file at a time (`--test-concurrency=1`) | 89 |
| Rehearsal: the production build of 2,557 pages, then Wrangler's dry run | 94 |
| Pipeline tests: 1,795 tests in one process | 41 |
| Database: pull the image, wait until healthy | 15 |
| Waiting between jobs and for runners | 13 |
| Deploy job before it deploys: checkout, Node, `npm ci`, `wrangler whoami`, latest-revision check | 18 |
| Runner set-up, checkout, uv, Node | 8 |
| Lint and types, with the Python install | 5 |
| `npm ci` | 5 |
| Seed site build (64 pages), extension tests and build, script tests | 5 |

Three things stand out. Everything runs one after another in one job. The production site is built in the rehearsal and then built again from nothing in the deploy job (88 to 153 s for the deploy step across 28 runs), and a third time by the preview workflow. And a push to `main` repeats every check the pull request already passed on the same files.

## What Changes

- **Stated limits and targets for four scenarios**, each a number that a command can show to be met or missed (`specs/delivery-time/spec.md`). A limit is what this change must reach to be finished. The target is the operator's 15 seconds.
- **A timing report** built from GitHub's records: p50 and p90 per scenario, the seconds each step spent on the path that decided the run's length, and a pass or a miss against each limit and target.
- **A guard that speed removes no check.** Every check either runs or is answered by a recorded pass for the same inputs, and a set of deliberately broken changes must still fail.
- **The seeded strategies** from the measurements above: checks in parallel, the production build made once and handed to the deployment, a pass and a build reused when the files are the same, checks scoped to what changed, tests that run concurrently, and stored build work.
- **A discovery procedure** for when the limits or the target are still missed: measure, rank, state a prediction and what would refute it, try it, keep or discard it, and record it. It ends with a verdict for each scenario, either met or not met with the measured floor that prevents it.
- The `deployment` capability changes in two places: a check may be answered by a recorded pass, and the deployment publishes the build the rehearsal checked.

Not in this change:

- Any change to what is tested, to the deploy checks (`deploy-checks.mjs`), or to what a preview may reach.
- Moving the site off a static build. `cloudflare-source-of-truth` changes where the data lives; this change takes the build as it finds it.
- A runner on the home network, a paid runner, or any other spending. The discovery procedure may recommend one with evidence; the operator decides.

## Capabilities

### New Capabilities

- `delivery-time`: how long the checks, the deployment and the preview may take, how that is measured, and what may and may not be skipped to get there.

### Modified Capabilities

- `deployment`: "Checks precede production deployment" allows a check to be answered by a recorded pass for the same inputs, and requires the deployment to publish the build that was rehearsed.

## Impact

- `.github/workflows/ci.yml`, `.github/workflows/pr-preview.yml`, `Makefile`.
- `site/scripts/deploy.mjs` and `site/scripts/pr-preview.mjs`: building and publishing become separable, still reached only through `make deploy-ci` and `make pr-preview`.
- `site/package.json` (test concurrency), possibly `pipeline/pyproject.toml` and the pipeline's test database fixture (tests in parallel).
- A new timing report script with its test, and `docs/deploy.md`.
- GitHub Actions cache and artifact storage. No new secret, no new service, no new cost.
