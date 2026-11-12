# source-clients Specification

## Purpose
Gives the pipeline uniform, polite and replayable access to public registries of clinical trials, scientific papers and DOI records.

## Requirements

### Requirement: Common record contract
Every source SHALL return records that carry the source name, the record's external identifier, its canonical public URL, the raw payload as received, and the time the payload was fetched.

#### Scenario: Trial record
- **WHEN** a trial is fetched by its registry identifier
- **THEN** the record carries the registry's name, the identifier, the trial's public URL, the unmodified payload and the fetch time

### Requirement: Trial registry lookups
The trial registry source SHALL support fetching one trial by registry identifier and searching trials by intervention term.

#### Scenario: Search by intervention term
- **WHEN** the registry is searched for an intervention term that three trials use
- **THEN** three trial records are returned

#### Scenario: Search with many results
- **WHEN** a search matches more trials than fit in one page of results
- **THEN** all matching trials are returned

### Requirement: Literature lookups
The literature source SHALL support fetching one paper by DOI and listing the papers that cite a given paper.

#### Scenario: Citing papers
- **WHEN** citing papers are requested for a paper that has 40 citations
- **THEN** 40 paper records are returned, each with title, authors, publication date and DOI when available

### Requirement: DOI registry lookups
The DOI registry source SHALL support fetching metadata for a DOI and listing retraction and correction notices attached to that DOI.

#### Scenario: Retracted paper
- **WHEN** notices are requested for a DOI that has a retraction notice
- **THEN** the notice is returned with its type, date and own DOI

#### Scenario: Paper with no notices
- **WHEN** notices are requested for a DOI that has none
- **THEN** an empty list is returned

### Requirement: Not found
A lookup for an identifier the source does not know SHALL return an explicit not-found result and SHALL NOT be treated as a failure.

#### Scenario: Unknown trial identifier
- **WHEN** a trial is fetched by an identifier the registry does not have
- **THEN** the result is not-found and no error is raised

### Requirement: Response caching
An identical request repeated within the cache lifetime SHALL be answered from the cache without a network call, and SHALL keep the original fetch time. An operator SHALL be able to force a fresh fetch.

#### Scenario: Repeated request
- **WHEN** the same trial is fetched twice within the cache lifetime
- **THEN** only one network request is made and both records carry the same fetch time

#### Scenario: Forced refresh
- **WHEN** an operator forces a refresh of a cached trial
- **THEN** a network request is made and the fetch time is updated

### Requirement: Rate limiting
Requests to a source SHALL NOT exceed that source's configured rate. The default rate for each source SHALL be at or below the rate the source publishes.

#### Scenario: Burst of requests
- **WHEN** ten requests are issued at once to a source limited to three requests per second
- **THEN** the requests are spread over at least three seconds

### Requirement: Client identification
Every request SHALL carry a User-Agent that names the project and a contact address taken from configuration. Without a configured contact address the system SHALL NOT send requests.

#### Scenario: Missing contact address
- **WHEN** a fetch is attempted and no contact address is configured
- **THEN** no request is sent and the error names the missing setting

### Requirement: Failure handling
Transient failures SHALL be retried a bounded number of times with increasing delay, honouring any retry delay the source states. When retries are exhausted the fetch SHALL fail as a whole and return no partial records.

#### Scenario: Source asks the client to slow down
- **WHEN** a source answers with a too-many-requests response that states a retry delay
- **THEN** the next attempt is made no sooner than the stated delay

#### Scenario: Source stays down
- **WHEN** a source fails on every allowed attempt
- **THEN** the fetch reports an error and returns no records
