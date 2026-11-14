# Spec Delta

## ADDED Requirements

### Requirement: A chosen organisation match is approved by rule
A new organisation match that the registry marks as its chosen answer for the name SHALL be approved and recorded as approved by rule. Any other organisation match SHALL be pending. An operator SHALL be able to reject an approved match afterwards, and a rejected match SHALL NOT be approved again by a later run.

#### Scenario: Registry chooses one record
- **WHEN** the registry returns one record marked chosen for "University of Nottingham"
- **THEN** that match is approved and marked as approved by rule

#### Scenario: Registry chooses none
- **WHEN** the registry returns three records for a name and marks none chosen
- **THEN** the three matches are pending and the entity has no approved match

#### Scenario: Operator rejected the chosen record
- **WHEN** resolution runs again for an entity whose chosen match an operator rejected
- **THEN** the match stays rejected

### Requirement: A trial's organisation sponsor becomes an entity
When a trial has approved events, its lead sponsor SHALL be recorded as an entity of the claim, as a company when the registry classes it as industry and as an institution otherwise, marked as named by a registry record. A sponsor that is a person SHALL NOT be recorded. An entity the claim already has under the same name SHALL gain the mark and SHALL NOT be recorded twice.

#### Scenario: Industry sponsor not named in any report
- **WHEN** a fetch runs for a claim whose approved trial is sponsored by a company no report named
- **THEN** the claim gains a company entity for it, marked as named by a registry record

#### Scenario: Sponsor the report also named
- **WHEN** a trial's sponsor has the same name as an institution entity read from the report
- **THEN** the claim has one entity for it, marked as named by both

#### Scenario: Sponsor who is a person
- **WHEN** a trial's lead sponsor is a person
- **THEN** no entity is recorded
