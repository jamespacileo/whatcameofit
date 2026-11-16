# Spec Delta

## Purpose

How long the checks, the production deployment and a pull request's preview may take, how that time is measured from GitHub's own records, and what may and may not be skipped to reach it.

## ADDED Requirements

### Requirement: Each scenario has a limit and a target
Four scenarios SHALL each have a limit and a target, in seconds from the moment GitHub records the run as created to the moment its last job completes. A limit SHALL hold at p50 and at p90 over the scenario's last 20 successful runs. A target SHALL be judged at p50 over the same runs. The numbers SHALL be held in one file that the timing report reads.

#### Scenario: A push to main that deploys and checks the live site
- **WHEN** the scenario's last 20 successful runs are judged
- **THEN** the limit is 120 s at p50 and 180 s at p90, and the target is 15 s at p50

#### Scenario: Pull request checks
- **WHEN** the scenario's last 20 successful runs are judged
- **THEN** the limit is 120 s at p50 and 150 s at p90, and the target is 15 s at p50

#### Scenario: A pull request preview is published
- **WHEN** the scenario's last 20 successful runs are judged
- **THEN** the limit is 20 s at p50 and 30 s at p90, and the target is 15 s at p50

#### Scenario: A run whose checked inputs are unchanged since a recorded pass
- **WHEN** the scenario's last 20 successful runs are judged
- **THEN** the limit is 30 s at p50 and 45 s at p90, and the target is 10 s at p50

#### Scenario: A limit is met
- **WHEN** the last 20 successful pull request check runs have a p50 of 110 s and a p90 of 140 s
- **THEN** the report shows the pull request checks limit as met

#### Scenario: A limit is missed at p90 only
- **WHEN** the last 20 successful deploying runs have a p50 of 100 s and a p90 of 200 s
- **THEN** the report shows the deployment limit as missed and names p90 as the reason

#### Scenario: A limit is met and the target is not
- **WHEN** a scenario's p50 is 40 s
- **THEN** the report shows its limit as met and its target as missed, as two separate results

#### Scenario: Too few runs
- **WHEN** a scenario has fewer than 20 successful runs since the change that is being judged
- **THEN** the report says how many it has and gives no verdict for that scenario

### Requirement: Time is measured from GitHub's records by one command
One command SHALL produce the timing report from GitHub's records of past runs, with no timing code inside the workflows deciding the result. It SHALL give p50 and p90 for each scenario, classify each run into exactly one scenario or none, and exit with a failure status when any limit is missed. Cancelled and failed runs SHALL be counted and shown but SHALL NOT enter the percentiles.

#### Scenario: A superseded push
- **WHEN** a push to `main` passed its checks and did not deploy because a newer revision existed
- **THEN** it is not counted as a deploying run

#### Scenario: A limit is missed
- **WHEN** any scenario with 20 or more runs misses its limit
- **THEN** the command exits with a failure status

#### Scenario: Only targets are missed
- **WHEN** every limit is met and one target is missed
- **THEN** the command exits successfully and shows the missed target

### Requirement: A report names where the time went
For each scenario the report SHALL give the median seconds of every step on the chain of jobs that decided the run's length, and the seconds spent waiting for a runner or between jobs. It SHALL list them largest first. The seconds listed for a run SHALL add up to that run's wall-clock time to within 5 seconds.

#### Scenario: Jobs run side by side
- **WHEN** two jobs ran at the same time and one finished 40 s after the other
- **THEN** the steps of the longer job are listed as deciding the run's length, and the shorter job is shown as not on that chain

#### Scenario: Waiting is counted
- **WHEN** 12 s passed between one job finishing and the next job starting
- **THEN** those 12 s appear in the report as waiting, not inside any step

### Requirement: Speed removes no check
Every check that ran before this capability existed SHALL, on every run, either run or be answered by a recorded pass for the same inputs. A check's inputs SHALL include every file it reads, the locked dependency versions, the tool versions and the settings it is given. A recorded failure SHALL NOT be reused as a pass, and a check whose inputs cannot be established SHALL run.

#### Scenario: Nothing a check reads has changed
- **WHEN** a run's inputs for the pipeline tests are identical to those of a recorded pass
- **THEN** the pipeline tests are answered by that pass, and the run says which earlier run answered them

#### Scenario: One input has changed
- **WHEN** a dependency lock file differs from the recorded pass
- **THEN** every check that reads that lock file runs

#### Scenario: A file outside any check's declared inputs changes
- **WHEN** a changed file is not listed as an input of any check and is not listed as read by none
- **THEN** every check runs

### Requirement: Deliberately broken changes still fail
A fixed set of deliberately broken changes SHALL exist, at least one for each check: lint, types, pipeline tests, script tests, site tests, site build, extension tests, and the deployment rehearsal. Applied one at a time, each SHALL make the checks fail. The set SHALL be run after every change to how the checks are scheduled, skipped or reused.

#### Scenario: A broken pipeline rule
- **WHEN** the change that breaks one status rule is applied and the checks run
- **THEN** the pipeline tests fail and the run fails

#### Scenario: A broken change is answered by a stale pass
- **WHEN** a deliberately broken change passes because a recorded pass answered its check
- **THEN** the set reports that check as unguarded and fails

### Requirement: Stored work is reused only from this repository's own runs
A recorded pass or a stored build SHALL be reused only when it was produced by a run of this repository's workflows on a branch of this repository, for identical inputs. Nothing produced by a pull request from a fork SHALL be reused by a run that holds a secret. A production deployment SHALL verify a stored build against the digest recorded when it was checked, and SHALL build afresh when the build is absent or does not match.

#### Scenario: A build made for a pull request from this repository
- **WHEN** a push to `main` has the same files and settings as a pull request run that built and rehearsed the site
- **THEN** the deployment publishes that build after its digest matches

#### Scenario: A build made by a fork's pull request
- **WHEN** the only stored build for these files came from a fork's pull request
- **THEN** it is not used and the site is built afresh

#### Scenario: A stored build does not match its digest
- **WHEN** a stored build's digest differs from the recorded one
- **THEN** it is discarded, the site is built afresh, and the run says so

### Requirement: Each scenario ends with a verdict on its target
For each scenario the project SHALL record a verdict on the target: met, or not met. A verdict of not met SHALL state the measured floor that prevents it, how the floor was measured, and what would have to change to lower it. A target SHALL NOT be declared met or abandoned without the timing report's figures for it.

#### Scenario: A target is met
- **WHEN** the report shows a scenario's p50 at or under its target over 20 runs
- **THEN** the verdict is recorded as met with the report's figures

#### Scenario: A target cannot be reached on the present runners
- **WHEN** a run that does nothing but start and finish takes longer than a scenario's target
- **THEN** the verdict is recorded as not met, with that measurement and the options that would lower the floor
