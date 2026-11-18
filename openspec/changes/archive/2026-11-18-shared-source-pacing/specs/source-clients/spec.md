# Source clients: changes

## MODIFIED Requirements

### Requirement: Rate limiting
Requests to a source SHALL NOT exceed that source's configured rate, counted across every client of the source and every process that asks it. The default rate for each source SHALL be at or below the rate the source publishes.

#### Scenario: Burst of requests
- **WHEN** ten requests are issued at once to a source limited to three requests per second
- **THEN** the requests are spread over at least three seconds

#### Scenario: Several clients of one registry at once
- **WHEN** two clients of one source, which share nothing but the source's name, issue requests in turn
- **THEN** each request waits until the source's interval has passed since the request before it, whichever client made that one

#### Scenario: Several processes ask one source
- **WHEN** two processes each issue requests to one source
- **THEN** the turns they take are never closer together than the source's interval
