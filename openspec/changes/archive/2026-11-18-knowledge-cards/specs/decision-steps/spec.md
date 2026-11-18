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

### Requirement: Choosing an intervention's kind is a decision step
Choosing the kind of a claim's intervention SHALL go through the decision interface as its own step, with one option for each kind on the project's list and one for none of them. The state judged SHALL be the claim's headline, summary and intervention names. Its log record SHALL refer to the claim.

#### Scenario: One claim
- **WHEN** a kind is chosen for one claim's intervention
- **THEN** one log record exists for the step, referring to the claim, with the probability of each kind

#### Scenario: Backend failure
- **WHEN** the backend fails for a claim
- **THEN** the failure is logged, no kind link is stored and the claim is tried again on the next run

### Requirement: The named-gene check is a decision step
Checking a gene named in a claim's intervention SHALL go through the decision interface as its own step, with the two options the knowledge-cards capability defines. The state judged SHALL be the claim's headline, summary and intervention names with the word that matched, the gene's symbol and its name. Its log record SHALL refer to the claim and the gene.

#### Scenario: Two candidate genes for one claim
- **WHEN** two candidate genes for one claim are checked
- **THEN** two log records exist for the step, each referring to the claim and one gene
