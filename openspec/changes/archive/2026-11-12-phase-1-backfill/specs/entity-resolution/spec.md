# Spec Delta

## Purpose

Links the things a claim names (interventions, papers, people, institutions and companies) to identifiers in public registries, with every link confirmed by a human.

## ADDED Requirements

### Requirement: Entities and synonyms
Each claim SHALL have entities of type intervention, paper, person, institution or company. An entity SHALL have a name and MAY have any number of synonyms, which an operator can add at any time.

#### Scenario: Compound renamed
- **WHEN** an operator adds a company code name as a synonym of an intervention
- **THEN** later registry searches for that intervention also use the code name

### Requirement: Origin paper
A claim MAY designate one of its paper entities as the origin paper, meaning the publication the first news reports were about. A claim SHALL have at most one origin paper.

#### Scenario: Second origin paper
- **WHEN** an operator designates an origin paper for a claim that already has one
- **THEN** the new paper replaces the old one as the origin paper

### Requirement: Candidate matches
For each intervention entity the system SHALL search the trial registry by the entity's name and every synonym. For each paper entity with a DOI the system SHALL look the DOI up. Every hit SHALL be stored as a candidate match with its source, external identifier and score.

#### Scenario: Intervention with two synonyms
- **WHEN** resolution runs for an intervention with a name and two synonyms, and each term finds a different trial
- **THEN** three candidate matches are stored

#### Scenario: Same trial found by two terms
- **WHEN** the name and a synonym both find the same trial
- **THEN** one candidate match is stored for that trial

### Requirement: Human confirmation
Every candidate match SHALL start as pending. A match SHALL become approved only through an operator's action, whatever its score.

#### Scenario: High-scoring match
- **WHEN** a candidate match has a score of 0.99
- **THEN** it remains pending until an operator approves it

### Requirement: Match score
Each candidate match SHALL carry a score between 0 and 1 that estimates how likely it is to be correct. The score SHALL inform the order of review and SHALL NOT approve or reject a match.

#### Scenario: Low-scoring match
- **WHEN** a candidate match has a score of 0.05
- **THEN** it remains pending and visible in the review queue

### Requirement: Repeatable resolution
Running resolution again for a claim SHALL NOT create a second candidate for an entity, source and external identifier that already have one, and SHALL NOT change the review state of an existing candidate.

#### Scenario: Rejected match found again
- **WHEN** resolution runs again and finds a trial whose match an operator rejected earlier
- **THEN** the match stays rejected and no new candidate is created
