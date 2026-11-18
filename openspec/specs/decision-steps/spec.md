# decision-steps Specification

## Purpose
Routes bounded classification choices through one interface, so that the backend making them can be replaced and every choice can later be checked against human labels.

## Requirements

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

### Requirement: Several items in one backend call
A decision step SHALL be able to make the same choice for several items in one backend call, at most twenty items to a call. Each item SHALL get its own decision log entry, exactly as if it had been decided alone. A backend that cannot answer in batches SHALL be asked item by item. When any item of a batch has no usable answer, the batch SHALL fail after every one of its items is logged.

#### Scenario: Batch of candidates
- **WHEN** three candidates are scored by a backend that answers in batches
- **THEN** the backend is called once and three decision log entries are written

#### Scenario: Item left out
- **WHEN** the model's answer to a batch omits one item
- **THEN** that item is asked alone, and every item still gets its answer

#### Scenario: Usage of a batch
- **WHEN** a batch is answered by one model call
- **THEN** the usage ledger records one call

### Requirement: The statement check is a decision step
Checking a reported statement against its article SHALL go through the decision interface as its own step, with the three options the reported-statements capability defines. Its log record SHALL refer to the article and to the statement's place among that article's proposed statements, and SHALL NOT hold the article's text or the statement's text.

#### Scenario: Six statements from one article
- **WHEN** six statements from one article are checked
- **THEN** six log records exist for the step, each referring to the article and a place from one to six, and none holds text from the article

#### Scenario: Backend failure
- **WHEN** the backend fails for one statement
- **THEN** the failure is logged and that statement is not stored

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

### Requirement: A model call is retried within bounds
A call to a backend that fails for a cause that passes, a timeout, a too-many-requests answer or a server error, SHALL be retried a bounded number of times with increasing delay, honouring a wait the backend states up to the configured ceiling. This SHALL hold for every backend. A result the backend gave that is invalid SHALL NOT be retried under this rule: it fails as before.

#### Scenario: The backend asks for a short wait
- **WHEN** a backend answers too-many-requests and states a wait of five seconds
- **THEN** the call is made again no sooner than five seconds later, and the decision is given if that attempt succeeds

#### Scenario: An invalid result
- **WHEN** a backend returns a result that fails validation
- **THEN** the decision fails as an invalid result and this rule makes no further attempt

### Requirement: A backend that cannot be asked is not a failed decision
When retries are exhausted, the key is refused, the quota is used up or the spend ceiling is reached, the caller SHALL be told the backend cannot be asked, apart from a decision that failed. No decision SHALL be logged as made. The step that asked SHALL stop as the work ledger says, with no attempt counted against its record.

#### Scenario: The quota is used up
- **WHEN** a backend answers that the account's quota is used up
- **THEN** the caller is told the backend cannot be asked, and the record being decided is not recorded as failed

#### Scenario: One item of a batch gets no answer
- **WHEN** a backend answers a batch and leaves one item out
- **THEN** that item alone fails as a decision, and the backend is not treated as one that cannot be asked
