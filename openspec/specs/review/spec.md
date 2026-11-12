# review Specification

## Purpose
Keeps a human between collected data and the public site. Draft claims, entity matches and evidence events wait in a queue until an operator approves or rejects them.

## Requirements

### Requirement: Review states
Every draft claim, entity match and evidence event SHALL be in exactly one review state: pending, approved or rejected. Each decision SHALL record when it was made and whether a human, a rule or the seed loader made it.

#### Scenario: Operator approves a match
- **WHEN** an operator approves a pending entity match
- **THEN** the match is approved, with the decision time and a human decider recorded

### Requirement: Review queue
An operator SHALL be able to list pending items, for all claims or for one claim, by kind. Each listed item SHALL show what it asserts, its source link and its score or confidence.

#### Scenario: Queue for one claim
- **WHEN** an operator lists pending items for a claim with two pending matches and three pending events
- **THEN** five items are shown, each with its source link

#### Scenario: Empty queue
- **WHEN** an operator lists pending items and none exist
- **THEN** the operator is told the queue is empty

### Requirement: Approve and reject
An operator SHALL be able to approve or reject any pending item. A rejected item SHALL be kept, not deleted.

#### Scenario: Rejected event
- **WHEN** an operator rejects a pending follow-up paper event
- **THEN** the event is kept in the rejected state

### Requirement: Changing a decision
An operator SHALL be able to change an earlier decision, including one made by rule.

#### Scenario: Rule-approved event found to be wrong
- **WHEN** an operator rejects an event that was approved by rule
- **THEN** the event is rejected, with a human decider recorded

### Requirement: Status follows review
After any review decision on an evidence event, the claim's status SHALL be derived again.

#### Scenario: Approving a started event
- **WHEN** an operator approves a started event for a Phase 1 trial on a claim whose status was trial registered
- **THEN** the claim's status becomes Phase 1

### Requirement: Failure flag
An operator SHALL be able to flag a trial as having missed its primary endpoint. A flag SHALL name the trial and an approved evidence event that reports the result, and SHALL carry a source URL. The system SHALL NOT set a failure flag by any other means.

#### Scenario: Flag with a source
- **WHEN** an operator flags a trial as failed, pointing at an approved results event and giving a source URL
- **THEN** the trial carries a failure flag and the claim's status is derived again

#### Scenario: Flag without a source
- **WHEN** an operator tries to flag a trial without a source URL
- **THEN** the flag is refused

#### Scenario: Results posted without a flag
- **WHEN** a trial has an approved results posted event and no operator has flagged it
- **THEN** the trial carries no failure flag

### Requirement: Human labels
When an operator decides an item for which a decision step made a suggestion, the operator's decision SHALL be recorded as the human label for that suggestion.

#### Scenario: Match scored by a decision step
- **WHEN** an operator rejects an entity match that a decision step scored as a likely match
- **THEN** the decision record for that suggestion carries the human label "not a match"

### Requirement: Evidence stage confirmation
An operator SHALL be able to confirm or correct the evidence stage suggested for a claim. Only the confirmed value SHALL be stored as the claim's stage.

#### Scenario: Operator corrects the suggestion
- **WHEN** the suggested stage is early human and the operator sets it to animal
- **THEN** the claim's stage is animal and the human label for the suggestion is animal

### Requirement: The queue says what a registry record is
A candidate match SHALL keep one line from its registry record: for a trial its title, conditions, interventions, phase and state; for a paper its title. The review queue SHALL show that line with the candidate.

#### Scenario: Trial candidate in the queue
- **WHEN** an operator lists a claim's pending candidates
- **THEN** each trial candidate shows its title, conditions, phase and state beside its score and link

### Requirement: Deciding several items at once
An operator SHALL be able to approve or reject several items by id in one command, and to approve or reject all of one claim's pending candidate matches on one side of a score. Items already decided SHALL be left as they are.

#### Scenario: Clearing the noise
- **WHEN** an operator rejects a claim's candidates scored under 0.1
- **THEN** only that claim's pending candidates under 0.1 are rejected, each recorded as the operator's decision
