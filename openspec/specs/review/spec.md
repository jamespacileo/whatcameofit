# review Specification

## Purpose
Keeps a human between collected data and the public site. Draft claims, entity matches and evidence events wait in a queue until an operator approves or rejects them.

## Requirements

### Requirement: Review states
Every draft claim, entity match and evidence event SHALL be in exactly one review state: pending, approved or rejected. Each decision SHALL record when it was made and whether a human, a rule, the seed loader or an assistant made it. An item approved by rule SHALL be published without waiting for a person.

#### Scenario: Operator approves a match
- **WHEN** an operator approves a pending entity match
- **THEN** the match is approved, with the decision time and a human decider recorded

#### Scenario: Rule approves a match
- **WHEN** a rule approves an entity match
- **THEN** the match is approved, recorded as decided by a rule, and counts toward the claim's status in the next export

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

### Requirement: Assistant decisions
An AI assistant working through the review queue SHALL record its decisions with the decider "assistant". A decision made by the assistant SHALL NOT be recorded as the operator's and SHALL NOT be stored as a human label. A rule SHALL NOT be nameable as the decider of a queue decision.

#### Scenario: Assistant approves a match
- **WHEN** the assistant approves a candidate match that a decision step had scored
- **THEN** the match is approved with the decider "assistant" and the score's human label stays empty

#### Scenario: Operator takes over a decision
- **WHEN** the operator approves an item the assistant had approved
- **THEN** the decider becomes the operator and the human label is recorded

### Requirement: Archive
An operator SHALL be able to archive a published claim or source page by its slug, giving a reason, and to unarchive it. Archiving SHALL keep every record in the database. The next export SHALL leave an archived item out of every public file and SHALL list its slug and the date it was archived. The reason SHALL NOT be exported.

#### Scenario: Operator takes a claim down
- **WHEN** an operator archives a published claim with the reason "wrong trial"
- **THEN** the claim and its events stay in the database, and the next export lists its slug and date and holds nothing else about it

#### Scenario: Unknown slug
- **WHEN** an operator archives a slug that no claim or source has
- **THEN** the command is refused and names the slug

#### Scenario: Putting it back
- **WHEN** an operator unarchives an archived claim
- **THEN** the next export contains the claim again

### Requirement: Evidence stage can be confirmed by rule
With draft approval by rule enabled, resolving a claim SHALL confirm its latest valid stored evidence-stage suggestion only when the stage is empty and both the chosen-stage probability and confidence meet the existing positive review threshold. Confirmation SHALL refresh status, retain the original decision and leave human labels untouched. Uncertain suggestions SHALL remain unconfirmed.

#### Scenario: Confident existing human-study reading
- **WHEN** a prepared claim has no confirmed stage and its recorded early-human reading meets the threshold
- **THEN** resolving it confirms early human and refreshes its no-trial status without another model reading

#### Scenario: Existing confirmation or rule disabled
- **WHEN** the claim already has a confirmed stage or draft approval by rule is disabled
- **THEN** the rule does not change its stage or human labels

#### Scenario: Uncertain reading
- **WHEN** either the chosen-stage probability or recorded confidence is below the threshold
- **THEN** the stage remains unconfirmed and the existing suggestion is not repeatedly sent to the model

### Requirement: Lower-band stage reading is shown and never used
A stage reading that did not confirm the claim's stage, and whose chosen stage has at least the configured show probability, SHALL be exported apart from the stage with its score and the other stages it weighed. The claim's stage SHALL stay empty beside it, the reading SHALL NOT be an input to the status, and no review SHALL be required to show it. A reading under the show probability, or for a claim with a confirmed stage, SHALL NOT be exported.

#### Scenario: Lower-band reading is shown and not used
- **WHEN** a claim with no approved trial has no confirmed stage and its latest stage reading chose early human with probability 0.7, below the threshold for confirming by rule
- **THEN** the export carries that reading with its score and the other stages it weighed, the claim's stage is empty, and the status is `no_trial_found`

#### Scenario: Reading below the lower band
- **WHEN** the latest stage reading of a claim with no confirmed stage chose its stage with probability 0.45 and the show probability is 0.5
- **THEN** the export carries no stage reading for the claim

#### Scenario: Confirmed stage
- **WHEN** a claim's stage is confirmed, by a person, an assistant or the rule
- **THEN** the export carries the stage and no stage reading
