# Design

## Context

See `proposal.md` for the measurements. What shapes the approach:

- `ci.yml` has two jobs. `check` runs `make check` and then `make deploy-ci-check` in sequence; `deploy` needs `check`, installs the site's dependencies again and runs `make deploy-ci`, which builds the whole site a second time inside `site/scripts/deploy.mjs` before calling Wrangler.
- `pr-preview.yml` builds the same snapshot a third time, with the registry search switched off, through `site/scripts/pr-preview.mjs`.
- The site's tests run with `node --test --test-concurrency=1`. That flag came in with commit `9351251` and no reason is written down. Several tests build the site, so a shared `dist` or data directory is the likely cause. It is not confirmed.
- The pipeline's tests use one Postgres database whose name must end in `_test` and which they drop and recreate.
- GitHub scopes an Actions cache to the branch that wrote it: a cache written by a pull request run cannot be read by a run on `main`. Artifacts can be fetched across runs by run id.
- A pull request run uses the workflow file from the pull request. A fork can therefore change what a run uploads. Forks already get no Cloudflare token.
- House rules that stay: production only through `make deploy-ci`, previews only through `make pr-preview`, actions pinned by commit, no live network in tests, nothing public from the home network.

One measurement decides how reachable the target is. The run-level overhead of two jobs was 13 s, and a job's own start and checkout about 4 s. So a run that only looks up a recorded pass, fetches a stored build, publishes it and checks the live site is plausibly within 15 s. A run that must really execute 1,795 pipeline tests (38 s of test time today) is not, unless those tests are answered by a recorded pass or cut to the ones a change can affect. The target is therefore reachable only where work is reused, and the design is built around that.

## Goals / Non-Goals

**Goals:**

- Meet every limit in `specs/delivery-time/spec.md`.
- Get as close to the 15 s target as the runners allow, and end with a verdict per scenario backed by figures.
- Leave a procedure and a ledger that a later session can continue from without this conversation.

**Non-Goals:**

- Changing any test's content, the deploy checks, or what the site builds.
- Choosing a different runner, a paid service or a home runner. These are recommendations for the operator, with evidence.
- Making a local `make check` faster, except where the same change does both.

## Decisions

### 1. Measure first, from GitHub's records, with one script

`scripts/ci-timing.mjs` reads runs and jobs through `gh api` and prints the report the spec describes. Limits and targets live in `scripts/ci-budgets.json`. Its test replays recorded API answers from `scripts/tests/fixtures/ci-timing/` (synthetic run ids, no live call) and joins `make scripts-test`.

Classification of a run:

- *Deploying*: workflow "CI and deploy", event `push` or `workflow_dispatch` on `main`, and the step "Deploy reviewed public snapshot" concluded `success`.
- *Pull request checks*: same workflow, event `pull_request`.
- *Preview published*: workflow "Pull request preview", job "Publish preview" concluded `success`.
- *Unchanged inputs*: any run in which every check was answered by a recorded pass. The workflow marks this in the run's summary and in a job output the script reads.

Step names are part of the script's contract. Renaming a step means updating the script and its fixtures in the same commit.

The path that decided a run's length is found by walking back from the job that finished last through `needs`, taking at each point the needed job that finished last. Waiting is the gap between a job's `startedAt` and the later of the run's `createdAt` and its needed jobs' `completedAt`.

Steps inside `make` are invisible to the jobs API. Where a step holds more than one piece of work, either split it into named workflow steps or have the script read the log's timestamps. Splitting is preferred: it costs nothing and the jobs API then answers.

*Alternative considered*: timing inside the workflow, written to the summary. Rejected as the judge, because a workflow that times itself cannot see its own queueing and can be edited to flatter itself. It is fine as an aid.

### 2. The guard comes before any speed work

A set of deliberately broken changes lives in `scripts/tests/ci-canaries/`, one patch per check, with a runner that applies each to a scratch branch, opens or updates one draft pull request per patch, waits for the checks and asserts failure. It is run by hand (`make ci-canaries`) after every change to scheduling, skipping or reuse, and its result is written into the ledger. It is not part of every run: it costs eight runs.

The last canary is the one that matters most for reuse. It changes a file that the input lists may have forgotten, and expects a failure. A pass there means an input list is incomplete.

### 3. Seeded strategies, in the order to try them

Each has a prediction to be confirmed or refuted by the report. Predictions are from one run and are rough.

| # | Strategy | Predicted effect | Refuted if |
| --- | --- | --- | --- |
| S1 | Split `check` into parallel jobs: lint and types; pipeline tests; site tests; extension and scripts; production build with rehearsal | Pull request checks fall from the sum (about 260 s) to the longest job plus overhead (about 105 s) | The longest job plus its start-up is over 120 s |
| S2 | Build the production site once. The rehearsal job uploads `dist` with a digest; the deploy job downloads it, verifies it, publishes and checks. `deploy.mjs` gains a way to publish a given build, still reached only through `make deploy-ci` | Deploy job falls from about 110 to 170 s to under 30 s | Download plus Wrangler's upload is over 30 s |
| S3 | Run the site's tests concurrently. First find what they share (likely a build output directory) and give each file its own | Site tests fall from 89 s to under 30 s on a four-core runner | The shared state cannot be separated without changing what a test asserts |
| S4 | Recorded pass by input key. Each check has a declared input list; its key is the hash of those files' git blob ids, the lock files, tool versions and the settings passed in. A pass is stored under that key. A later run with the same key is answered without running | A push to `main` after an up-to-date pull request runs no check, and a pull request touching only the site runs no pipeline test | Fewer than half of the last 40 pushes to `main` would have matched a pull request's keys |
| S5 | Stored build by the same key. The deploying run fetches the `dist` that the pull request run rehearsed | With S4, a deploying run is checkout, lookup, download, publish, live check: about 15 to 25 s | The build depends on something not in the key, shown by a canary or a differing digest on rebuild |
| S6 | Pipeline tests in parallel, one database per worker, and a database that starts faster (no image pull where the runner has it, a tighter health check, no durability) | Pipeline tests and database fall from 56 s to under 25 s | Tests share state beyond the database |
| S7 | Store the build's expensive pieces between runs, keyed by their own inputs. Profile the 86 s build first; the card images made with `satori` and `resvg` are the suspected bulk | Production build falls to under 30 s when the snapshot is unchanged | The profile shows time spread evenly across page rendering |
| S8 | Trim the deploy job's fixed steps: no second `npm ci` (carry Wrangler with the build or cache it), fold `whoami` into the publish, keep the latest-revision check | Saves about 8 s | The steps are already under 3 s together |
| S9 | The preview publishes a stored build. It differs from production's only by the registry search switch; find out whether that switch changes the built files or only the Worker's settings | Preview falls from 146 s to under 30 s | The switch changes many built files and cannot move to the Worker |

Order: S1 and S2 first, because they need no reuse and no input lists and should meet the limits on their own. S3 and S6 next. S4, S5 and S9 last, because they carry the correctness risk and the canaries must be in place and passing.

*How a recorded pass is stored* (S4, S5). A cache cannot cross from a pull request to `main`, so the record is an artifact: the checking run uploads a small file per check named by its key, and the build as `dist-<key>` with its digest. A later run finds the producing run by listing successful runs of this repository for the commit's tree and reading their artifacts. It accepts a run only when `head_repository` is this repository. The digest is checked after download.

*Alternative considered*: let `main` skip checks whenever the pull request was green. Rejected: a pull request that is behind `main` was tested on different files. The key is the files, not the pull request.

*Alternative considered*: a merge queue, so `main` only ever receives tested trees. It gives the same guarantee and may be simpler. It changes how the operator merges, so it is a recommendation for the discovery loop, not a seeded step.

### 4. Input lists fail closed

Each check's inputs are declared in one file as path patterns. A changed path that matches no check and is not on an explicit "read by nothing" list (for example `docs/**`, `openspec/**`, `*.md`) makes every check run. A new directory therefore costs time until someone lists it, and never costs a missed check.

### 5. The discovery procedure

Run this loop whenever a limit or a target is missed after the seeded strategies. One pass through it is one row in the ledger, `openspec/changes/fast-ci-and-deploy/experiments.md`.

1. **Measure.** Run the timing report for the scenario. Take the path that decided its length.
2. **Classify every second on that path** into one of: waiting for a runner; starting a job (set-up, checkout, tools); installing dependencies; starting a service; computing (tests, build); moving bytes (cache, artifact, upload to Cloudflare); waiting on a remote answer; waiting between jobs.
3. **Take the largest class.** If one step is more than 30% of the path, profile inside it before going on: `pytest --durations=25`, Node's test reporter per file, the build's own timings per route, Wrangler's output, `time` around each `make` target.
4. **Generate candidates** by asking each question of that step, and write down every answer, including "no":
   - *Remove*: is it needed on this path at all, or can it happen after the verdict?
   - *Reuse*: has it been done for these inputs before, and by whom?
   - *Narrow*: can it do only the part this change can affect?
   - *Parallelise*: can it be split across cores or jobs, and what does it share?
   - *Reorder*: can something slow start earlier, or something failing fast run first?
   - *Warm*: can its start-up be paid once, in an image, a cache or a long-lived process?
   - *Relocate*: would a different place do it faster (a bigger or closer runner, Cloudflare's own build, the operator's machine before the push)?
   - *Replace*: is there a faster tool or setting for the same result? Check the tool's current documentation and release notes; do not rely on memory of them.
5. **Write the hypothesis before trying it**: the step, the change, the seconds predicted to be saved, and the observation that would refute it.
6. **Try it** on a branch through `workflow_dispatch` or a draft pull request, at least five runs, and compare medians with the same five from before.
7. **Keep it** when the median saving on the deciding path is at least 2 s and at least half of what was predicted, the canaries pass, and no limit got worse at p90. Otherwise revert it. Record either outcome with the figures.
8. **Stop** for a scenario when its target is met over 20 runs, or when the floor rule below is met. Otherwise go to step 1.

**The floor rule.** Measure the floor with a workflow that has one job doing only a checkout, dispatched ten times, at two different hours. If the scenario's remaining path is within 20% of what its steps would cost at that floor, or the floor alone exceeds the target, record "not met" with the floor, and list what would lower it under *Relocate* with a rough cost each. Then stop. Do not redefine the scenario to make the number fit.

Three consecutive refuted hypotheses for the same step also end work on that step. Say so in the ledger and move to the next largest.

### 6. What is reported at the end

`docs/deploy.md` gains a section with the limits, the targets, the command, the input list file and the canaries. The change's ledger holds every experiment. The verdicts go into the main spec through the change's delta.

## Risks / Trade-offs

- [An input list misses a file and a broken change is answered by an old pass] → Lists fail closed (decision 4); the forgotten-file canary; the first two weeks of reuse run in shadow, computing what would have been skipped while still running everything, and the ledger records any shadow skip that then failed.
- [A stored build is tampered with or belongs to different settings] → Reuse only from this repository's runs, the key covers the settings, the digest is checked, and a mismatch rebuilds.
- [Tests in parallel become flaky] → Each of S3 and S6 is kept only after 20 consecutive green runs; a flake reverts it.
- [The p50 over real runs depends on what people happened to push] → Limits are judged on real runs; experiments are judged on five paired dispatches of the same commit, which removes the mix.
- [More jobs means more waiting for runners at busy hours] → The report counts waiting separately, so the cost shows; S1's grouping can be coarsened.
- [Artifact and cache storage fills up] → Seven-day retention on builds and pass records; the report notes total stored size.
- [The 15 s target is not reachable when checks really run] → Expected, and stated. The verdict requirement makes this a recorded finding with evidence, not a quiet miss.

## Migration Plan

Each strategy lands as its own pull request and can be reverted alone. S4, S5 and S9 sit behind one repository variable, `CI_REUSE`, with three values: `off`, `shadow` (compute and report, run everything) and `on`. Rollback is setting it to `off`. The canaries run before `shadow` becomes `on`.

## Open Questions

- Whether a merge queue would replace S4 and S5 more simply. To be answered in the discovery loop with the share of `main` pushes it would cover; it does not change the limits, the report or the guard.
- Whether the operator would accept a larger or third-party runner if the floor rule fires. Asked only if it fires, with the measured floor.
