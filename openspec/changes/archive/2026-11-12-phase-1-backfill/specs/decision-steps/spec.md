# Spec Delta

## Purpose

Routes bounded classification choices through one interface, so that the backend making them can be replaced and every choice can later be checked against human labels.

## ADDED Requirements

### Requirement: Decision result
Given a step name, the state to judge and a list of options, a decision SHALL return one choice taken from the options, a probability for every option, and a confidence between 0 and 1. The probabilities SHALL sum to 1.

#### Scenario: Evidence stage decision
- **WHEN** a decision is requested for the evidence stage step with the options in vitro, animal, early human and late human
- **THEN** the result has one of those four as its choice, four probabilities that sum to 1, and a confidence

### Requirement: Invalid results fail
A backend result whose choice is not among the options, or whose probabilities do not cover the options, SHALL fail the decision. The system SHALL NOT substitute a default choice.

#### Scenario: Choice outside the options
- **WHEN** a backend returns a choice that was not offered
- **THEN** the decision fails with an error and no choice is returned

### Requirement: Decision log
Every decision call SHALL be recorded with its step, a reference to its input, the backend and model that answered, the output, the confidence and the time. A failed call SHALL be recorded with its error. The human label SHALL be empty until a review decision supplies it.

#### Scenario: Successful call
- **WHEN** a decision call succeeds
- **THEN** one log record exists for it with an empty human label

#### Scenario: Failed call
- **WHEN** a decision call fails
- **THEN** one log record exists for it with the error

### Requirement: Swappable backend
The backend that answers decisions SHALL be chosen by configuration. Changing the backend SHALL NOT require any change to the steps that request decisions.

#### Scenario: Backend replaced
- **WHEN** the configured backend is changed and the same decision is requested
- **THEN** the result has the same shape and the log record names the new backend

### Requirement: Steps that use decisions
The evidence stage step and the entity match step SHALL obtain their suggestions through decisions. The entity match step SHALL offer the options match and not a match.

#### Scenario: Scoring a candidate match
- **WHEN** a candidate match is created for an intervention and a trial
- **THEN** a decision is requested for the entity match step and the probability of match becomes the candidate's score

### Requirement: Decisions are advisory
A decision SHALL NOT approve, reject or publish anything by itself. Its result SHALL only be a suggestion shown to the operator or a score used to order the review queue.

#### Scenario: Confident decision
- **WHEN** a decision returns match with a confidence of 0.99
- **THEN** the candidate match is still pending
