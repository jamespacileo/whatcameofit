# Spec Delta

## MODIFIED Requirements

### Requirement: Claims without standing trials
When a claim has no standing trial, its status SHALL be failed if any of its trials carries a failure flag, otherwise terminated if it has any trial, otherwise determined by the confirmed evidence stage: preclinical only for animal/in-vitro evidence and no trial record found for human or unknown evidence.

#### Scenario: Only trial failed
- **WHEN** a claim's only trial carries a failure flag
- **THEN** the status is failed

#### Scenario: Every trial terminated
- **WHEN** a claim has two trials and both are terminated without a failure flag
- **THEN** the status is terminated

#### Scenario: No trials
- **WHEN** a claim has only follow-up paper events and no confirmed evidence stage
- **THEN** the status is no trial record found

#### Scenario: Failed trial and a later standing trial
- **WHEN** a claim has a Phase 2 trial with a failure flag and a started Phase 3 trial
- **THEN** the status is Phase 3


### Requirement: With no trial found, the evidence stage decides the status
When a claim has no approved trial event and no rule above applies, the status SHALL be `preclinical_only` only if the claim's confirmed evidence stage is in vitro or animal, and `no_trial_found` for early human, late human or an unknown stage. The evidence stage SHALL NOT change any status that an approved trial, approval or retraction decides. A `no_trial_found` status SHALL list no explaining events and SHALL be able to carry the no-signal overlay.

#### Scenario: Studied in people, no trial found
- **WHEN** a claim's confirmed evidence stage is early human and its only approved event is a follow-up paper
- **THEN** the status is `no_trial_found`

#### Scenario: Laboratory or animal work, no trial found
- **WHEN** a claim's evidence stage is confirmed as in vitro or animal and it has no approved trial event
- **THEN** the status is `preclinical_only`

#### Scenario: Trial found for a claim first reported from animal work
- **WHEN** a claim's confirmed evidence stage is animal and it has an approved started Phase 2 trial
- **THEN** the status is `phase_2`

#### Scenario: Quiet claim studied in people
- **WHEN** a claim with stage early human has no approved trial event and its latest signal is four years before the as-of date
- **THEN** the status is `no_trial_found` with an overlay of 4 years


#### Scenario: Unknown stage, no trial found
- **WHEN** the claim has no approved trial event and its evidence stage is not confirmed
- **THEN** its status is `no_trial_found`, with no claim that the evidence is preclinical


#### Scenario: Newly entered claim
- **WHEN** a claim is created without a confirmed stage or approved evidence
- **THEN** its initial status is `no_trial_found`
- **AND** upgrading the database default does not rewrite existing stored statuses before normal derivation
