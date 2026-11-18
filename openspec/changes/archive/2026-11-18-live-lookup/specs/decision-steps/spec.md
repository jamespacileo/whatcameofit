# decision-steps

## ADDED Requirements

### Requirement: A backend that answers without writing text
The pipeline SHALL offer a second decision backend, named `openai-decisions`, that puts every item of a step to OpenAI's Decisions API in one request: the step's shared introduction as the evidence and each item as its own question, with each option described in the question's own words. It SHALL take as many items per request as the API allows, in place of the twenty a general model is given. Which backend answers SHALL be set by `DECISION_BACKEND`; the callers and the decision log SHALL NOT change with it.

#### Scenario: Many items, one call
- **WHEN** sixty candidate records are scored with the `openai-decisions` backend
- **THEN** one request is sent, each record gets its own choice, probabilities and log entry, and the log names the backend and its model

#### Scenario: Unusable answer
- **WHEN** the API declines to answer one item of a request
- **THEN** every item is logged, the declined one with an error, and the step fails without a substituted answer

### Requirement: Decision calls are counted and capped like every other model call
A call to the Decisions API SHALL be recorded in the usage ledger with its input tokens at the price set in `DECISIONS_INPUT_USD_PER_MTOK`, and SHALL be refused once the month's recorded cost has reached the ceiling. No call SHALL be made while the model, its price or the provider's credential is not configured. A failed call SHALL be reported by its status and SHALL NOT repeat anything that was sent.

#### Scenario: Usage recorded
- **WHEN** a request of three questions is answered using 709 input tokens at 0.10 dollars per million
- **THEN** one ledger entry records 709 input tokens, no output tokens and that cost

#### Scenario: Not configured
- **WHEN** the backend is chosen and its price is not set
- **THEN** the step fails saying which setting is missing, and no request is sent
