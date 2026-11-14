# Spec Delta

## Purpose

Keeps every process that asks an external source inside one shared allowance of requests for that source, so that a large run cannot exceed a limit that no single process can see.

## ADDED Requirements

### Requirement: Allowance per source
A source used by a step SHALL have an allowance: a number of requests permitted in a period, and the least time between two requests. The allowance SHALL be at or below what the source publishes, and SHALL be read from configuration, not from code.

#### Scenario: Allowance shown
- **WHEN** the operator runs `thenwhat backfill plan`
- **THEN** each step's source is shown with its allowance, the requests used in the current period and the requests left

#### Scenario: A source with no allowance
- **WHEN** a step names a source that has no configured allowance
- **THEN** the step refuses to run and says which allowance is missing

### Requirement: Shared across processes
Requests counted against an allowance SHALL be counted for every process that asks that source, and the count SHALL survive a restart.

#### Scenario: Four processes
- **WHEN** four processes ask a source whose allowance is 200 requests in the period
- **THEN** together they send no more than 200 requests in that period

#### Scenario: Restart within a period
- **WHEN** a run uses 150 of 200 requests, stops and starts again within the same period
- **THEN** it may send 50 more requests in that period

### Requirement: Spacing between requests
Two requests to the same source SHALL be at least the allowance's least time apart, whichever process sends them.

#### Scenario: Two processes, one source
- **WHEN** two processes ask a source that allows one request every five seconds
- **THEN** no two requests to that source are sent less than five seconds apart

### Requirement: Allowance used up
When an allowance is used up, a run SHALL stop asking that source, leave the remaining records due, and report when the period ends. It SHALL NOT wait silently or retry.

#### Scenario: Running out mid-run
- **WHEN** a run uses the last request of a source's allowance with 500 records still due
- **THEN** the run ends, reports 500 records due, and states when the allowance is restored

### Requirement: A source's refusal
When a source answers that the client is sending too many requests, the run SHALL stop asking that source for the time the source states, or for a configured time when it states none, and SHALL record the refusal against the source.

#### Scenario: Refused by the source
- **WHEN** a source answers a request with a too-many-requests refusal
- **THEN** no further request is sent to that source until the pause has passed, the record stays due, and the plan shows the source as paused

#### Scenario: Refusals do not count as failures
- **WHEN** a record's request is refused for too many requests
- **THEN** the record's attempt count does not rise
