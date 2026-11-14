# Spec Delta

## ADDED Requirements

### Requirement: A paper is looked up by its PubMed number
The literature client SHALL return a paper's index record for a PubMed number, as it does for a DOI, and SHALL return nothing when the index holds no such paper. A number that is not all digits SHALL cause no request.

#### Scenario: Known PubMed number
- **WHEN** the client is asked for a PubMed number the index holds
- **THEN** it returns that paper's record with the time it was fetched

#### Scenario: Malformed number
- **WHEN** the client is asked for "PMC12345"
- **THEN** it makes no request and returns nothing

### Requirement: Stored paper records are refreshed when old
A fetch SHALL ask the index again for a stored paper record only when the stored record is older than the configured age, thirty days by default. A paper whose stored record is younger SHALL cause no request.

#### Scenario: Record fetched last week
- **WHEN** a fetch runs for a claim whose paper record was stored seven days ago
- **THEN** no request is made for that paper

#### Scenario: Record fetched two months ago
- **WHEN** a fetch runs for a claim whose paper record was stored sixty days ago
- **THEN** the record is fetched again and the stored record and its time are replaced
