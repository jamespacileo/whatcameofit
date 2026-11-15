# Spec Delta

## MODIFIED Requirements

### Requirement: Evidence stage at announcement
A claim SHALL be able to carry the stage of evidence at the time of announcement: in vitro, animal, early human or late human. The stage SHALL stay empty until an operator or the separately specified evidence-stage threshold rule confirms it.

#### Scenario: Suggested but unconfirmed stage
- **WHEN** a stage has been suggested for a claim, no operator has confirmed it, and the threshold rule has not confirmed it
- **THEN** the claim's stage is empty

#### Scenario: Eligible stage confirmed by rule
- **WHEN** the enabled evidence-stage rule confirms a sufficiently confident recorded suggestion
- **THEN** the claim carries that stage without marking the suggestion as human-reviewed
