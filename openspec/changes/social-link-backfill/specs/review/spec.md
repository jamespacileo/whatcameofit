## ADDED Requirements

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
