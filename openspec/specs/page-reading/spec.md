# page-reading Specification

## Purpose
How the pipeline fetches a news page: through one page reader that holds the rules about each site, what the reader answers and what the pipeline does with each answer, and what the reader must never do with a page.

## Requirements

### Requirement: One page reader
The pipeline SHALL fetch a news page through the configured page reader and in no other way. When the reader does not give the page, the pipeline SHALL NOT fetch the page by another route.

#### Scenario: A page drawn by scripts
- **WHEN** an article's page holds its text only after its scripts have run
- **THEN** the text the pipeline reads is the text of the page as drawn

#### Scenario: The reader gives no page
- **WHEN** the reader answers that the site did not serve the page
- **THEN** the pipeline sends the site no request of its own

### Requirement: The reader holds the rules about each site
Whether an address may be fetched, how often a site may be asked and where a copy of a page comes from SHALL be decided by the page reader. The pipeline SHALL NOT keep rules about individual sites for fetching: it SHALL NOT read a site's robots.txt, space its requests per site, or ask an archive for a copy.

#### Scenario: Two articles of one outlet read side by side
- **WHEN** two processes each ask for an article of the same outlet at the same time
- **THEN** the pipeline sends both requests to the reader, and how far apart the outlet is asked is the reader's doing

#### Scenario: A new site
- **WHEN** an article of a site the pipeline has never read is asked for
- **THEN** it is asked for in the same way as any other, with no setting or code of the pipeline's naming that site

### Requirement: The reader says what happened
The page reader's answer to a request SHALL be one of: the page was read; the address is not allowed, with the reason; the site cannot be asked now, with when it may be asked again; the site did not serve the page, with the status it gave. The pipeline SHALL treat an answer that is none of these as the reader failing, not as the site failing.

#### Scenario: Not allowed
- **WHEN** the reader answers that an address is not allowed
- **THEN** the article is not read, the reason the reader gave is recorded with it, and it is not asked for again

#### Scenario: Not now
- **WHEN** the reader answers that a site cannot be asked now
- **THEN** the article is given no outcome, no attempt is counted against it, it stays due, and the run goes on with articles of other sites

#### Scenario: The site did not serve the page
- **WHEN** the reader answers that the site gave a status other than success
- **THEN** the article counts as one that could not be retrieved, with that status

#### Scenario: An answer the pipeline does not know
- **WHEN** the reader answers in a form that is none of the four
- **THEN** the run stops and reports the reader's answer as a fault of the reader, and the article stays due

### Requirement: What the reader must never do
The pipeline SHALL be configured only with a page reader that has been checked to keep nothing of a page after it has answered, with the result and its date recorded in `docs/sources.md`. The check SHALL be made again whenever the reader's version or configuration changes. How a site is asked, whether its robots.txt is followed and how the request is made SHALL be the reader's to decide.

#### Scenario: Nothing kept
- **WHEN** the reader has answered a request
- **THEN** it holds no copy of the page, and a second request for the same address asks the site again

#### Scenario: A post on a social platform
- **WHEN** the reader is asked for a post on a social or video platform
- **THEN** the pipeline takes whatever the reader answers, a page read or a refusal, and holds no rule of its own about that platform

#### Scenario: A site whose robots.txt disallows the address
- **WHEN** the reader is asked for an address its site's robots.txt disallows
- **THEN** the pipeline takes whatever the reader answers, and reads no robots.txt itself

### Requirement: The pipeline holds a page only while it reads it
The pipeline SHALL hold what the reader returns only as long as it holds any article text, and SHALL NOT write it to a log, a cache or a test fixture.

#### Scenario: After a read
- **WHEN** a read has finished, whether it succeeded or failed
- **THEN** the page's text is stored nowhere by the pipeline

### Requirement: The reader runs no model for the pipeline
The pipeline SHALL ask the reader for the page and for nothing made from it by a model: no summary, no structured extraction, no answer to a prompt. Every model call on an article's text SHALL be the pipeline's own, recorded and counted as its other model calls are.

#### Scenario: A read that drafts a claim
- **WHEN** an article is read and a claim is drafted from it
- **THEN** the only model calls made are the pipeline's, and each is in the model usage record

### Requirement: A reader that cannot be asked stops the run
When the page reader is not configured, cannot be reached, or answers that it is itself overloaded, the command SHALL stop and say which of these happened. It SHALL give the article no outcome and count no attempt against it.

#### Scenario: No reader configured
- **WHEN** a command that reads an article is run and no reader address is configured
- **THEN** the command refuses, names the setting that is missing, and fetches nothing

#### Scenario: The reader's machine is down during a backfill run
- **WHEN** the reader stops answering part way through a run that reads link leads
- **THEN** the run ends, the leads not yet read stay due with their attempts unchanged, and the report says the reader could not be reached

### Requirement: Outlets are measured through the reader
`thenwhat outlets` SHALL ask for each tracked article through the page reader, and SHALL count per outlet the articles read, thin, refused and failed, with a refusal counted from the reader's not-allowed answer.

#### Scenario: An outlet whose pages are drawn by scripts
- **WHEN** the outlets report is made and an outlet's articles hold their text only after scripts run
- **THEN** those articles are counted as read, not thin

#### Scenario: An outlet the reader does not allow
- **WHEN** the reader answers not allowed for an outlet's articles
- **THEN** they are counted as refused
