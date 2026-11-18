## MODIFIED Requirements

### Requirement: Usage ledger
Every language model call SHALL be recorded with its purpose, model, input and output token counts, cost and time. Incurred usage SHALL persist independently of the transaction performing claim work, so a later rollback cannot erase paid usage or hide it from the spending ceiling.

#### Scenario: Extraction call
- **WHEN** an extraction call completes
- **THEN** a ledger entry exists with purpose extraction, the model used, token counts and cost

#### Scenario: Claim work is rolled back after a call
- **GIVEN** a model call has incurred usage
- **WHEN** later claim work fails and its transaction rolls back
- **THEN** that usage remains recorded and counts towards the monthly ceiling
