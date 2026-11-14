# Spec Delta

## ADDED Requirements

### Requirement: An organisation match is approved by rule only on strong evidence
An organisation match SHALL be approved and recorded as approved by rule only when all of these hold: the registry marks the record as its chosen answer for the name; the name given, compared without regard to case, accents, punctuation, a leading "The" or a closing bracket, equals one of the record's names, labels or aliases, or equals one of its acronyms as written; a one-word name also appears among the record's names with the same letters and capitals; the registry does not type the record as "other"; the name is not the title or abbreviation of a journal of any paper record held; and, when the registry types the record as a government body, the name given states the record's country by its name or its two-letter code. Any other organisation match SHALL be pending, and its organisation SHALL stay unidentified. No looser or second match SHALL be tried. An operator SHALL be able to reject an approved match afterwards, and a rejected match SHALL NOT be approved again by a later run.

#### Scenario: Registry chooses one record by its own name
- **WHEN** the registry returns one record marked chosen for "University of Nottingham", and that is the record's name
- **THEN** that match is approved and marked as approved by rule

#### Scenario: Registry chooses another organisation
- **WHEN** the registry's chosen record for "CRISPR Therapeutics" is "Sprint PNS System", or for "Ulster University" is "RK University"
- **THEN** the match is pending and the organisation is listed as not identified

#### Scenario: Government body without its country
- **WHEN** a report names the "Food and Drug Administration" and the registry chooses a national agency of that exact name in another country
- **THEN** the match is pending, while "U.S. Food and Drug Administration" for the United States agency is approved

#### Scenario: Journal or newspaper named in a report
- **WHEN** a report names the journal "Neuron" or "The New York Times" and the registry chooses a record
- **THEN** the match is pending: "Neuron" is a journal title on record and not exactly "NeurON", and the newspaper's record is typed "other"

#### Scenario: Registry chooses none
- **WHEN** the registry returns three records for a name and marks none chosen
- **THEN** none is approved and the entity has no approved match

#### Scenario: Operator rejected the chosen record
- **WHEN** resolution runs again for an entity whose approved match an operator rejected
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
