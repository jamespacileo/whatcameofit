# claim-extraction Specification

## Purpose
Turns a news article into a structured draft claim for a human to confirm, without retaining the article's text.

## Requirements

### Requirement: Structured extraction
Given a news article, the system SHALL produce a draft containing a headline, a summary, the intervention and indication, other named entities (papers, people, institutions, companies), the DOI of the underlying paper when the article gives one, and any promised timelines.

#### Scenario: Article with a paper and a promise
- **WHEN** extraction runs on an article that names a drug, cites a journal paper and says human trials will start by 2025
- **THEN** the draft contains the drug as an intervention entity, the paper as a paper entity and one promise for 2025

#### Scenario: Article with no promise
- **WHEN** extraction runs on an article that states no timeline
- **THEN** the draft contains no promises

### Requirement: Output validation
Extraction output SHALL be validated against a fixed schema. Output that fails validation after a bounded number of retries SHALL be discarded and reported as an error.

#### Scenario: Invalid output
- **WHEN** the model returns output that fails validation on every allowed attempt
- **THEN** no draft is saved and the operator sees which fields failed

### Requirement: Summary limits
A draft summary SHALL be written in the system's own words and SHALL be at most 500 characters long.

#### Scenario: Overlong summary
- **WHEN** the model returns a summary longer than 500 characters
- **THEN** the output fails validation

### Requirement: Transient article text
Article text SHALL be held only while extraction runs. After extraction the system SHALL keep only the extraction output, the article URL, a hash of the text and an archive URL when one was used.

#### Scenario: After successful extraction
- **WHEN** extraction of a fetched article has finished
- **THEN** the article text is no longer stored anywhere and the content hash is recorded

#### Scenario: After failed extraction
- **WHEN** extraction of a fetched article fails
- **THEN** the article text is no longer stored anywhere

### Requirement: Robots exclusion
The system SHALL NOT fetch an article URL that the site's robots.txt disallows for the system's client.

#### Scenario: Disallowed URL
- **WHEN** an operator requests extraction for a URL that robots.txt disallows
- **THEN** the page is not fetched and the operator is asked to supply the text directly

### Requirement: Pasted text
An operator SHALL be able to supply article text directly instead of having it fetched. Pasted text SHALL be handled under the same retention rules as fetched text.

#### Scenario: Paywalled article
- **WHEN** an operator supplies the text of a paywalled article together with its URL
- **THEN** extraction runs on the supplied text and the text is discarded afterwards

### Requirement: Archived copies
When an article URL cannot be retrieved, the system SHALL look for an archived snapshot. If one exists, the system SHALL extract from it and record the snapshot URL with the article.

#### Scenario: Dead link with a snapshot
- **WHEN** the article URL returns not found and an archived snapshot exists
- **THEN** extraction uses the snapshot and the article record carries the snapshot URL

#### Scenario: Dead link without a snapshot
- **WHEN** the article URL returns not found and no snapshot exists
- **THEN** the operator is asked to supply the text directly

### Requirement: Drafts need confirmation
A draft produced by extraction SHALL be pending until an operator approves it. The operator SHALL be able to edit any field of the draft before approving it.

#### Scenario: Unapproved draft
- **WHEN** extraction has produced a draft that no operator has approved
- **THEN** the draft does not appear on the public site

#### Scenario: Edited draft
- **WHEN** an operator corrects the headline of a draft and approves it
- **THEN** the claim carries the corrected headline

### Requirement: Other names are names
Extraction SHALL record as another name of the intervention only a name: a brand, a code or a generic name. A description the model returns as a name, such as "the drug" or "a one-time treatment", SHALL NOT be recorded.

#### Scenario: Article that only describes the intervention
- **WHEN** the model returns "EX-1", "the drug" and "experimental antibody jab" as other names
- **THEN** only "EX-1" is recorded

### Requirement: Preparing many claims
An operator SHALL be able to have unread articles read, registries searched and approved matches fetched for many claims with one command, several claims at a time. A step that fails SHALL be reported with its claim, and the claim's other steps SHALL still run. The command SHALL approve nothing and SHALL say how long each step took.

#### Scenario: Article that cannot be read
- **WHEN** one of a claim's articles cannot be read
- **THEN** the failure is reported and the claim is still searched
