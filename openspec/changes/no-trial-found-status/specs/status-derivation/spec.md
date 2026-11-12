# Spec Delta

## ADDED Requirements

### Requirement: With no trial found, the evidence stage decides the status
When a claim has no approved trial event and no rule above applies, the status SHALL be `no_trial_found` if the claim's confirmed evidence stage is early human or late human, and `preclinical_only` otherwise. The evidence stage SHALL NOT change any status that an approved trial, approval or retraction decides. A `no_trial_found` status SHALL list no explaining events and SHALL be able to carry the no-signal overlay.

#### Scenario: Studied in people, no trial found
- **WHEN** a claim's confirmed evidence stage is early human and its only approved event is a follow-up paper
- **THEN** the status is `no_trial_found`

#### Scenario: Laboratory or animal work, no trial found
- **WHEN** a claim's evidence stage is in vitro, animal or not yet confirmed and it has no approved trial event
- **THEN** the status is `preclinical_only`

#### Scenario: Trial found for a claim first reported from animal work
- **WHEN** a claim's confirmed evidence stage is animal and it has an approved started Phase 2 trial
- **THEN** the status is `phase_2`

#### Scenario: Quiet claim studied in people
- **WHEN** a claim with stage early human has no approved trial event and its latest signal is four years before the as-of date
- **THEN** the status is `no_trial_found` with an overlay of 4 years

### Requirement: Confirming a stage brings the status up to date
Confirming or correcting a claim's evidence stage SHALL re-derive and store the claim's status.

#### Scenario: Stage confirmed on a claim with no trial
- **WHEN** the reviewer sets the stage of a claim with no approved trial event to early human
- **THEN** the stored status is `no_trial_found`, and setting the stage to animal afterwards returns it to `preclinical_only`
