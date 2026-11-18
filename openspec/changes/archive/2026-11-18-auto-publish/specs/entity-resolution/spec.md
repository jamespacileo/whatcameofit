# Spec Delta

## ADDED Requirements

### Requirement: Confident candidates are approved by rule
A newly scored candidate match that was scored with the claim's indication and whose score is at or above the configured accept threshold SHALL be approved by rule. The decision SHALL be recorded as made by a rule and SHALL NOT be stored as a human label. A candidate scored without the indication SHALL never be approved by rule. An accept threshold of zero or none SHALL turn the rule off. An operator SHALL be able to reject a candidate the rule approved.

#### Scenario: Confident candidate
- **WHEN** a new candidate scored with the indication scores 0.91 and the accept threshold is 0.8
- **THEN** it is approved, recorded as decided by a rule

#### Scenario: Scored without the indication
- **WHEN** a new candidate scored without the indication scores 0.95
- **THEN** it stays pending

#### Scenario: Between the thresholds
- **WHEN** a new candidate scores 0.4 with an accept threshold of 0.8 and a reject threshold of 0.05
- **THEN** it stays pending and does not count toward the claim's status

## MODIFIED Requirements

### Requirement: Human confirmation
Every candidate match SHALL start as pending. A match SHALL become approved only through an operator's action or the rule for confident candidates.

#### Scenario: High-scoring match
- **WHEN** a candidate match has a score of 0.99 and no accept threshold is set
- **THEN** it remains pending until an operator approves it

### Requirement: Match score
Each candidate match SHALL carry a score between 0 and 1 that estimates how likely it is to be correct. The score SHALL order the review queue, SHALL be published with the match, and SHALL approve or reject a match only through the rules for confident and near-zero candidates.

#### Scenario: Low-scoring match
- **WHEN** a candidate match has a score of 0.3, between the thresholds
- **THEN** it remains pending and visible in the review queue

### Requirement: Near-zero candidates are rejected by rule
A newly scored candidate match whose score is under a configured threshold SHALL be rejected by rule instead of waiting for review. The decision SHALL be recorded as made by a rule, SHALL NOT be stored as a human label, and the candidate SHALL be kept. An operator SHALL be able to list the candidates a rule rejected and to approve any of them. A threshold of zero SHALL turn the rule off. A candidate scored exactly at the threshold, such as 0.05 with the default, still remains pending.

#### Scenario: Candidate scored near zero
- **WHEN** a new candidate is scored 0.02 and the threshold is 0.05
- **THEN** it is rejected, recorded as decided by a rule, and absent from the review queue

#### Scenario: Seeing what the rule rejected
- **WHEN** an operator lists the candidates rejected by rule for a claim
- **THEN** each is shown with its id, score, record line and link, and can be approved

#### Scenario: Rule turned off
- **WHEN** the threshold is zero
- **THEN** no new candidate is rejected by rule
