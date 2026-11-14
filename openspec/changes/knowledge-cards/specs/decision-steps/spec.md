# Spec Delta

## ADDED Requirements

### Requirement: The term check is a decision step
Checking a candidate subject term against a claim SHALL go through the decision interface as its own step, with the three options the knowledge-cards capability defines. The state judged SHALL be the claim's headline, summary, intervention names and indication with the term's label and definition. Its log record SHALL refer to the claim and the term.

#### Scenario: Ten candidates for one claim
- **WHEN** ten candidate terms for one claim are checked
- **THEN** ten log records exist for the step, each referring to the claim and one term

#### Scenario: Backend failure
- **WHEN** the backend fails for one candidate
- **THEN** the failure is logged and that candidate stays without a score and is not approved
