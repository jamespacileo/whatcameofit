# Spec Delta

## ADDED Requirements

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
