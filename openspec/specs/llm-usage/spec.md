# llm-usage Specification

## Purpose
Controls which language model the pipeline calls and how much it may spend, so that models can be swapped by configuration and cost cannot pass an agreed ceiling.

## Requirements

### Requirement: Configured provider and model
The provider and model used for language model calls SHALL come from configuration. The system SHALL have no built-in default model. When the configuration is missing, the system SHALL refuse to make the call.

#### Scenario: Model not configured
- **WHEN** extraction is requested and no model is configured
- **THEN** no call is made and the error names the missing setting

#### Scenario: Model changed
- **WHEN** the configured model is changed
- **THEN** the next call uses the new model without any other change

### Requirement: Usage ledger
Every language model call SHALL be recorded with its purpose, model, input and output token counts, cost and time.

#### Scenario: Extraction call
- **WHEN** an extraction call completes
- **THEN** a ledger entry exists with purpose extraction, the model used, token counts and cost

### Requirement: Monthly spend ceiling
When the recorded cost for the current calendar month has reached the configured ceiling, the system SHALL refuse further language model calls until the month ends or the ceiling is raised.

#### Scenario: Ceiling reached
- **WHEN** the month's recorded cost equals the ceiling and a decision is requested
- **THEN** no call is made and the error states that the monthly ceiling has been reached

#### Scenario: New month
- **WHEN** a call is requested on the first day of the next month
- **THEN** the call is made

### Requirement: Credentials stay in the environment
Provider credentials SHALL be read only from the environment and SHALL NOT be written to the database, logs or error messages.

#### Scenario: Provider rejects the key
- **WHEN** the provider rejects the configured credential
- **THEN** the error reported to the operator does not contain the credential
