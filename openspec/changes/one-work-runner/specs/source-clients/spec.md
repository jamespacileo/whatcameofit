# Spec Delta

## ADDED Requirements

### Requirement: A stated wait is honoured in either form and bounded
A wait a source states SHALL be honoured whether it is given as a number of seconds or as a time. No single wait inside a fetch SHALL be longer than a configured ceiling, sixty seconds unless set. A source that asks for a longer wait SHALL be treated as one that cannot be asked now: the fetch SHALL end at once, saying until when.

#### Scenario: A wait given as a time
- **WHEN** a source answers too-many-requests and states the time at which it may be asked again, twenty seconds ahead
- **THEN** the next attempt is made no sooner than that time

#### Scenario: A wait longer than the ceiling
- **WHEN** a source states a wait of one hour
- **THEN** the fetch ends without waiting, and its caller is told the source cannot be asked for an hour

### Requirement: A pause is seen by every process
When a source cannot be asked until a time, that time SHALL be kept where every process and every later run reads it, and no request SHALL be sent to that source before it by any command. A command that needs the source SHALL be told the source is paused and until when, without sending a request.

#### Scenario: Two commands and one throttled source
- **WHEN** one command is told by a registry to wait an hour, and a second command starts a minute later
- **THEN** the second sends that registry no request and reports that it is paused and until when

#### Scenario: The pause has passed
- **WHEN** the time a source was paused until has passed
- **THEN** the next command asks it as usual

#### Scenario: A pause begins while a client awaits its turn

- **WHEN** a request was admitted for 12:00:10 and another worker records a pause until 13:00 during the pacing wait
- **THEN** the client sends no request during the pause and reports the persisted deadline

### Requirement: Every command's requests count against the source's allowance
Requests to a source SHALL be counted against that source's allowance whichever command sends them. A command SHALL send no request to a source whose allowance for the period is used up.

#### Scenario: Preparing claims and a backfill share a registry
- **WHEN** a backfill step and the preparation of claims ask one registry in the same period
- **THEN** the allowance's count holds the requests of both

### Requirement: Try later is told apart from not found
A fetch that ends because the source could not be asked, was paused, or failed on every attempt SHALL give its caller a result that says so and until when, where the source said. It SHALL NOT give an empty result, and SHALL NOT be stored as an answer.

#### Scenario: A search while the registry is down
- **WHEN** a registry fails on every allowed attempt of a search
- **THEN** the caller is told the search did not run, and nothing records that the search found no trial
