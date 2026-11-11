# Spec Delta

## ADDED Requirements

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
