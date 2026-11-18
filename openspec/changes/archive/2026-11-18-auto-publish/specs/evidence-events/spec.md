# Spec Delta

## MODIFIED Requirements

### Requirement: Initial review state
A new event whose confidence is below the configured threshold SHALL be pending. A new event at or above the threshold SHALL be approved and recorded as approved by rule. This SHALL hold for follow-up paper events as for trial events. Manually entered events SHALL always start pending.

#### Scenario: Trial event from an approved match
- **WHEN** a registered event is created from a human-approved trial match with confidence above the threshold
- **THEN** the event is approved and marked as approved by rule

#### Scenario: Follow-up paper
- **WHEN** a follow-up paper event is created with a confidence below the threshold
- **THEN** it is pending

#### Scenario: Confident follow-up paper
- **WHEN** a follow-up paper event is created with a confidence of 0.9 and the threshold is 0.9
- **THEN** it is approved and marked as approved by rule
