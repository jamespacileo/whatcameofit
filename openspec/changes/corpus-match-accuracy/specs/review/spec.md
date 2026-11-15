# Spec Delta

## ADDED Requirements

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
