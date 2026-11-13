# Spec Delta

## MODIFIED Requirements

### Requirement: Candidate matches
For each intervention entity the system SHALL search the trial registry by the entity's name, every synonym and every search phrase. A search phrase SHALL be searched only within the claim's indication. For each paper entity with a DOI the system SHALL look the DOI up. Every hit SHALL be stored as a candidate match with its source, external identifier and score.

#### Scenario: Intervention with two synonyms
- **WHEN** resolution runs for an intervention with a name and two synonyms, and each term finds a different trial
- **THEN** three candidate matches are stored

#### Scenario: Same trial found by two terms
- **WHEN** the name and a synonym both find the same trial
- **THEN** one candidate match is stored for that trial

#### Scenario: Trial found only by a search phrase
- **WHEN** the name as written finds only trials for other conditions and a search phrase finds a trial within the claim's indication
- **THEN** that trial is stored as a candidate match

#### Scenario: Search phrase that identifies nothing
- **WHEN** a search phrase returns more than a hundred trials within the indication, or none
- **THEN** that phrase contributes no candidates

## ADDED Requirements

### Requirement: Organisations are looked up by name
For each institution or company entity the system SHALL look its name up in an open organisation registry and store each hit as a candidate match with the registry's identifier and a one-line record of the organisation's name, country and website. The score SHALL be the registry's own measure of the name match, and no model SHALL score it.

#### Scenario: University named in the article
- **WHEN** resolution runs for an institution entity that the organisation registry matches exactly
- **THEN** one candidate match is stored with that registry's identifier and a score of 1

#### Scenario: Name the registry does not know
- **WHEN** the registry returns no organisation for the name
- **THEN** no candidate is stored and nothing fails

### Requirement: People are not looked up
The system SHALL NOT search any registry or directory for a person entity.

#### Scenario: Claim with a named researcher
- **WHEN** resolution runs for a claim that has a person entity
- **THEN** no request is made for that person and no candidate is stored
