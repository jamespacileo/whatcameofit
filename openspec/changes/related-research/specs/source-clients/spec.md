# Spec Delta

## ADDED Requirements

### Requirement: Literature search by words
A literature source SHALL support searching papers by words and SHALL return, in the source's own order of relevance and up to a stated limit, records that carry title, authors with their institutions where the source gives them, publication date, kind of paper and DOI when available.

#### Scenario: Search with results
- **WHEN** the literature is searched for an intervention and a condition that five papers concern, with a limit of twenty
- **THEN** five paper records are returned, most relevant first

#### Scenario: Search with more results than the limit
- **WHEN** a search matches three hundred papers and the limit is twenty
- **THEN** twenty records are returned and no further page is requested

### Requirement: A source that needs a key refuses without it
A source that requires a key SHALL send no request while the key is not configured, and the error SHALL name the missing setting. The key SHALL NOT appear in a cached request, a log line or a recorded fixture.

#### Scenario: Missing key
- **WHEN** a literature search is attempted and the source's key is not configured
- **THEN** no request is sent and the error names the setting

### Requirement: A source's daily allowance is respected
When a source reports that the day's allowance is used up, the client SHALL stop asking that source for the rest of the run and SHALL report it as the reason, without retrying.

#### Scenario: Allowance used up
- **WHEN** a source answers that the daily allowance is exhausted
- **THEN** the fetch fails with that reason and later searches in the same run are not sent

### Requirement: Organisation lookups
An organisation source SHALL support looking an organisation up by name and SHALL return records that carry the organisation's identifier, name, country, website and the source's measure of how well the name matched.

#### Scenario: Known organisation
- **WHEN** an organisation is looked up by a name the source matches
- **THEN** a record is returned with its identifier and match measure

#### Scenario: Unknown organisation
- **WHEN** an organisation is looked up by a name the source does not match
- **THEN** an empty result is returned and no error is raised
