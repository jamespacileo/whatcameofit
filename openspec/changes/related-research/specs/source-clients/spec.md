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

#### Scenario: Another run on the same day
- **WHEN** one run has used the day's allowance up and another run or process searches before it resets
- **THEN** no search is sent and the reason is reported

#### Scenario: Paid credit on the account
- **WHEN** a source's answer shows that the account holds prepaid credit
- **THEN** no further search is sent until the allowance resets, and the reason given names the credit

#### Scenario: Allowance not stated
- **WHEN** a source's answer to a charged search does not state what is left
- **THEN** no further search is sent until the next day

### Requirement: A charged search is not repeated needlessly
A source that charges for each search SHALL be asked once for all the terms of a claim where it can take them together, SHALL NOT be asked a looser search when that one finds nothing, SHALL keep a search's answer for seven days, and SHALL report for each run how many searches it sent, what they cost and what is left of the allowance.

#### Scenario: Intervention with a name and two phrases
- **WHEN** the literature is searched for a claim whose intervention has a name and two search phrases
- **THEN** one search is sent that names all three together with the indication

#### Scenario: The one search finds nothing
- **WHEN** the search for all of a claim's terms finds no paper
- **THEN** the result is empty, no second or looser search is sent, and the run reports that the claim has no related paper

#### Scenario: Claim resolved again within the week
- **WHEN** the same search was answered three days ago
- **THEN** the kept answer is used and no search is sent

#### Scenario: End of a run
- **WHEN** a run that sent one search ends
- **THEN** it reports one search, its cost and what the source said is left of the day

### Requirement: Organisation lookups
An organisation source SHALL support looking an organisation up by name and SHALL return records that carry the organisation's identifier, name, country, website and the source's measure of how well the name matched.

#### Scenario: Known organisation
- **WHEN** an organisation is looked up by a name the source matches
- **THEN** a record is returned with its identifier and match measure

#### Scenario: Unknown organisation
- **WHEN** an organisation is looked up by a name the source does not match
- **THEN** an empty result is returned and no error is raised
