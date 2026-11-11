# Spec Delta

## ADDED Requirements

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
