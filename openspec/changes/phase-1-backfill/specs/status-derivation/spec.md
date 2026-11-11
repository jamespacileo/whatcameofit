# Spec Delta

## Purpose

Derives each claim's public status from its approved evidence events by fixed rules, so that every status can be explained and reproduced.

## ADDED Requirements

### Requirement: Deterministic derivation
A claim's status SHALL be a function of its approved evidence events, its first reported date and an as-of date, and of nothing else. No language model or decision step SHALL take part in deriving status.

#### Scenario: Same inputs
- **WHEN** status is derived twice from the same events and the same as-of date
- **THEN** both results are identical

### Requirement: Only approved events count
Pending and rejected events SHALL have no effect on status.

#### Scenario: Pending termination
- **WHEN** a claim has an approved started event for a Phase 2 trial and a pending terminated event for the same trial
- **THEN** the status is Phase 2

### Requirement: Status explanation
Every derived status SHALL come with the list of evidence events that produced it.

#### Scenario: Phase 2 claim
- **WHEN** a claim's status is Phase 2 because of one trial
- **THEN** the explanation lists that trial's registered and started events

### Requirement: Standing trials
A trial SHALL count as standing unless its most recent approved status change reports terminated or withdrawn, or it carries a failure flag. A trial SHALL count as started when it has an approved started event or an approved completed event.

#### Scenario: Suspended trial
- **WHEN** a trial's most recent status change reports suspended
- **THEN** the trial is standing

### Requirement: Stage from standing trials
When a claim has standing trials, its status SHALL be the furthest phase among those that have started, or trial registered when none has started. Early Phase 1 SHALL count as Phase 1. A trial registered under two phases SHALL count as the lower one. Phase 4 SHALL count as Phase 3. A started trial with no applicable phase SHALL count as trial registered.

#### Scenario: Terminated Phase 1 and recruiting Phase 2
- **WHEN** a claim has a terminated Phase 1 trial and a started Phase 2 trial
- **THEN** the status is Phase 2

#### Scenario: Registered but not started
- **WHEN** a claim's only trial is a Phase 1 trial that has not started
- **THEN** the status is trial registered

#### Scenario: Combined phase trial
- **WHEN** a claim's only trial is a started Phase 1/Phase 2 trial
- **THEN** the status is Phase 1

#### Scenario: Completed trial
- **WHEN** a claim's only trial is a completed Phase 2 trial with no failure flag
- **THEN** the status is Phase 2

### Requirement: Claims without standing trials
When a claim has no standing trial, its status SHALL be failed if any of its trials carries a failure flag, otherwise terminated if it has any trial, otherwise preclinical only.

#### Scenario: Only trial failed
- **WHEN** a claim's only trial carries a failure flag
- **THEN** the status is failed

#### Scenario: Every trial terminated
- **WHEN** a claim has two trials and both are terminated without a failure flag
- **THEN** the status is terminated

#### Scenario: No trials
- **WHEN** a claim has only follow-up paper events
- **THEN** the status is preclinical only

#### Scenario: Failed trial and a later standing trial
- **WHEN** a claim has a Phase 2 trial with a failure flag and a started Phase 3 trial
- **THEN** the status is Phase 3

### Requirement: Approved status
A claim with an approved regulatory decision event that records an approval SHALL have the status approved, whatever its trials show.

#### Scenario: Approval with a terminated trial
- **WHEN** a claim has a terminated trial and a regulatory decision event recording an approval
- **THEN** the status is approved

### Requirement: Retracted status
A claim whose origin paper has an approved retraction event SHALL have the status retracted, whatever its other events show. Retraction of any other paper SHALL NOT change the status.

#### Scenario: Origin paper retracted
- **WHEN** a claim has a started Phase 1 trial and a retraction event for its origin paper
- **THEN** the status is retracted

#### Scenario: Follow-up paper retracted
- **WHEN** a claim has a retraction event for a follow-up paper only
- **THEN** the status is unchanged

### Requirement: No-signal overlay
A claim whose status is preclinical only, trial registered or a phase SHALL also carry a no-signal overlay when its latest approved event is at least a configured number of years before the as-of date, 3 by default. A claim with no approved events SHALL be measured from its first reported date. The overlay SHALL state the number of whole years and SHALL NOT replace the status.

#### Scenario: Quiet preclinical claim
- **WHEN** a preclinical-only claim's latest approved event is four years and two months before the as-of date
- **THEN** the status is preclinical only with a no-signal overlay of 4 years

#### Scenario: Recent event
- **WHEN** a Phase 1 claim's latest approved event is one year before the as-of date
- **THEN** the status is Phase 1 with no overlay

#### Scenario: Terminal status
- **WHEN** an approved claim's latest event is ten years before the as-of date
- **THEN** the status is approved with no overlay

### Requirement: Status change time
A claim's stored status and its status-updated time SHALL change only when the derived status or overlay differs from the stored one.

#### Scenario: Re-derivation with no change
- **WHEN** status is re-derived and equals the stored status
- **THEN** the status-updated time is unchanged
