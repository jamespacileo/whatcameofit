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
