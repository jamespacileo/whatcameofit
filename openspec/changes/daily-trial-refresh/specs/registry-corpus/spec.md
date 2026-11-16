# registry-corpus

## MODIFIED Requirements

### Requirement: Registry terms
Bulk loads SHALL identify the client with the configured contact address, stay within the registry's allowance, and send no request while the contact address is empty. A load that may not ask the registry now, because the allowance is used up or the registry asked it to wait, SHALL stop with what it stored, say why, and not be recorded as a completed load.

#### Scenario: No contact address
- **WHEN** a load is started with no contact address configured
- **THEN** no request is sent and the command says the contact address is missing

#### Scenario: The allowance runs out part way
- **WHEN** the registry's allowance is used up after the first page of a load
- **THEN** the trials of that page are stored, the command reports them and says it stopped, it exits without an error, and the next changes-only load asks from the same date as this one did

#### Scenario: The registry asks the load to wait
- **WHEN** the registry still answers "too many requests" after the client's retries
- **THEN** the pause is recorded for the registry with the wait it stated, the load stops with what it stored and exits without an error, and a load started before the pause ends sends no request
