# entity-resolution Specification

## Purpose
Links the things a claim names (interventions, papers, people, institutions and companies) to identifiers in public registries, with every link confirmed by a human.

## Requirements

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

### Requirement: Matches are scored for the claim's indication
A candidate trial match SHALL be scored on whether the record is a trial of the claim's intervention for the claim's indication. A record of the same intervention for another indication SHALL score lower than one for the claim's indication and SHALL be shown to the reviewer as being for another indication.

#### Scenario: Same drug, another condition
- **WHEN** a claim is about a vaccine for melanoma and the registry holds a trial of that vaccine for lung cancer
- **THEN** the lung cancer trial scores below the melanoma trials and is labelled as another indication

#### Scenario: Laboratory compound with unrelated trials
- **WHEN** an animal study used a compound that has registered trials only in unrelated diseases
- **THEN** none of those trials scores as a match for the claim

### Requirement: Broad names are searched within the indication
When the registries are searched for a claim, the search SHALL be narrowed by the claim's indication, so that a broad intervention name returns trials for that condition.

#### Scenario: Broad intervention name
- **WHEN** the intervention is "CAR-T cell therapy" and the indication is stiff person syndrome
- **THEN** the search returns trials of CAR-T cell therapy in stiff person syndrome, not every CAR-T trial

#### Scenario: Name that identifies nothing
- **WHEN** a search name still returns more than a hundred trials within the indication, or none
- **THEN** that name contributes no candidates

### Requirement: Scores given without the indication are marked
A pending trial candidate whose score was given before the indication was part of the question SHALL be shown in the review queue as scored without the indication. An operator SHALL be able to have the pending trial candidates that the search still returns scored again. A candidate that has been decided SHALL keep the score it was decided on.

#### Scenario: Old score in the queue
- **WHEN** a pending trial candidate was last scored on the intervention alone
- **THEN** the review queue says it was scored without the indication

#### Scenario: Scoring again
- **WHEN** an operator resolves a claim again and asks for rescoring
- **THEN** its pending trial candidates that the search returns get a new score, and decided candidates are unchanged

### Requirement: Near-zero candidates are rejected by rule
A newly scored candidate match whose score is under a configured threshold SHALL be rejected by rule instead of waiting for review. The decision SHALL be recorded as made by a rule, SHALL NOT be stored as a human label, and the candidate SHALL be kept. An operator SHALL be able to list the candidates a rule rejected and to approve any of them. A threshold of zero SHALL turn the rule off. A rule SHALL never approve a candidate. This replaces the earlier statement that a score never rejects a match: a candidate scored exactly at the threshold, such as 0.05 with the default, still remains pending.

#### Scenario: Candidate scored near zero
- **WHEN** a new candidate is scored 0.02 and the threshold is 0.05
- **THEN** it is rejected, recorded as decided by a rule, and absent from the review queue

#### Scenario: Seeing what the rule rejected
- **WHEN** an operator lists the candidates rejected by rule for a claim
- **THEN** each is shown with its id, score, record line and link, and can be approved

#### Scenario: Rule turned off
- **WHEN** the threshold is zero
- **THEN** every new candidate stays pending whatever its score
