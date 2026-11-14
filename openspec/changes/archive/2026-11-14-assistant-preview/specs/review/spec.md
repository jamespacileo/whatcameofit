# Spec Delta

## ADDED Requirements

### Requirement: Assistant decisions
An AI assistant working through the review queue SHALL record its decisions with the decider "assistant". A decision made by the assistant SHALL NOT be recorded as the operator's and SHALL NOT be stored as a human label. A rule SHALL NOT be nameable as the decider of a queue decision.

#### Scenario: Assistant approves a match
- **WHEN** the assistant approves a candidate match that a decision step had scored
- **THEN** the match is approved with the decider "assistant" and the score's human label stays empty

#### Scenario: Operator takes over a decision
- **WHEN** the operator approves an item the assistant had approved
- **THEN** the decider becomes the operator and the human label is recorded
