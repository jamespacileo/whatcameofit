# Spec Delta

## Purpose

How the pipeline fetches a news page: through one page reader, only where the outlet's own rules allow it, identified as the pipeline's client, with nothing of the page kept by the reader and no model run by it.

## ADDED Requirements

### Requirement: One page reader
The pipeline SHALL fetch a news page through the configured page reader and in no other way. When the reader cannot give the page, the pipeline SHALL NOT fetch the page by another route.

#### Scenario: A page drawn by scripts
- **WHEN** an article's page holds its text only after its scripts have run
- **THEN** the text the pipeline reads is the text of the page as drawn

#### Scenario: The reader gives no page
- **WHEN** the reader answers that the outlet did not serve the page
- **THEN** the pipeline sends the outlet no request of its own, and the article is handled as one that could not be retrieved

### Requirement: The outlet's rules are read first
The pipeline SHALL read the outlet's robots.txt itself, with the contact User-Agent, before the reader is asked for a page. The reader SHALL NOT be asked for a page the rules disallow for the pipeline's client, or a page of an outlet whose rules could not be read.

#### Scenario: Robots.txt forbids the fetch
- **WHEN** an outlet's robots.txt disallows the article's address for the pipeline's client
- **THEN** the reader is sent no request for that address

#### Scenario: Rules that could not be read
- **WHEN** an outlet does not answer for its robots.txt or answers with a server error
- **THEN** the reader is sent no request for any page of that outlet

### Requirement: The outlet sees who is asking
A page SHALL be asked for with the pipeline's contact User-Agent, and without any means of the reader's that hides the client from the outlet. An outlet that refuses the identified client SHALL be recorded as refusing, and SHALL NOT be asked again in a way that hides the client.

#### Scenario: The outlet refuses the identified client
- **WHEN** the outlet answers the identified request with a refusal
- **THEN** the page counts as failed with the outlet's answer, and no second request is made through a proxy that hides the client

#### Scenario: No contact address configured
- **WHEN** a page is asked for and no contact address is configured
- **THEN** the command refuses before the reader is sent anything

### Requirement: The reader keeps nothing
Every request to the reader SHALL ask for a fresh copy of the page and SHALL tell the reader not to keep it. The pipeline SHALL hold what the reader returns only as long as it holds any article text, and SHALL NOT write it to a log, a cache or a test fixture.

#### Scenario: The same article read twice
- **WHEN** one article is read twice
- **THEN** the outlet is asked for the page both times, and neither answer came from a copy the reader kept

#### Scenario: After a read
- **WHEN** a read has finished, whether it succeeded or failed
- **THEN** the page's text is stored nowhere by the pipeline

### Requirement: The reader runs no model
The reader SHALL be asked for the page and for nothing made from it by a model: no summary, no structured extraction, no answer to a prompt. Every model call on an article's text SHALL be the pipeline's own, recorded and counted as its other model calls are.

#### Scenario: A read that drafts a claim
- **WHEN** an article is read and a claim is drafted from it
- **THEN** the only model calls made are the pipeline's, and each is in the model usage record

### Requirement: A reader that cannot be asked stops the run
When the page reader is not configured, does not answer, or refuses the pipeline's request, the command SHALL stop and say which of these happened. It SHALL give the article no outcome and count no attempt against it. When the reader says it is asked too often, the pipeline SHALL send it no further request for the time the reader states.

#### Scenario: No reader configured
- **WHEN** a command that reads an article is run and no reader address is configured
- **THEN** the command refuses, names the setting that is missing, and fetches nothing

#### Scenario: The reader does not answer during a backfill run
- **WHEN** the reader stops answering part way through a run that reads link leads
- **THEN** the run ends, the leads not yet read stay due with their attempts unchanged, and the report says the reader could not be reached

#### Scenario: The reader says it is asked too often
- **WHEN** the reader answers a request with a too-many-requests refusal
- **THEN** the run ends, the article stays due, and no request is sent to the reader until the stated time has passed

### Requirement: Outlets are measured through the reader
`thenwhat outlets` SHALL ask for each tracked article through the page reader, under the same rules as any other read, so that its report says what the pipeline can read.

#### Scenario: An outlet whose pages are drawn by scripts
- **WHEN** the outlets report is made and an outlet's articles hold their text only after scripts run
- **THEN** those articles are counted as read, not thin
