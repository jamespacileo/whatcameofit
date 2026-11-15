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

### Requirement: Statements are part of a draft
When an article is read for a pending claim, the extraction SHALL also return the statements the article makes about the intervention, each with its kind, firmness, speaker role and basis. The instructions SHALL forbid copying a sentence, quoting, and naming a person. An article that makes no such statement SHALL give none.

#### Scenario: Article with an effect and a hope
- **WHEN** an article reports an effect in a study and a researcher's hope for wider use
- **THEN** the draft carries two statements, one stated as fact and one as a possibility

#### Scenario: Article that only announces a trial
- **WHEN** an article says only that a trial will begin next year
- **THEN** the draft carries a promise and no statement

### Requirement: A decided claim's article can be read again for statements
An operator SHALL be able to have the articles of a claim in any review state read again for reported statements only. The read SHALL follow the same robots, archived-copy and pasted-text rules as a first read, SHALL keep nothing of the text, and SHALL NOT change the claim's headline, summary, intervention, indication, promises or entities.

#### Scenario: Approved claim with no statements
- **WHEN** the command is run for an approved claim whose article can be read
- **THEN** statements are stored for the article and nothing else about the claim changes

#### Scenario: Article that cannot be read
- **WHEN** the command is run for a claim whose article is disallowed by robots and has no archived copy
- **THEN** no statement is stored, the output names the article and says pasted text is needed

#### Scenario: Article whose text has changed
- **WHEN** the article's text no longer matches the hash stored at its first read
- **THEN** statements are stored and the output says the article has changed since it was first read

### Requirement: Statements are found once per article
A run SHALL skip an article that already has statements, in any review state, unless the operator asks for it to be read again.

#### Scenario: Second run with no change
- **WHEN** the command is run twice for the same claim
- **THEN** the second run reads no article and makes no model call

### Requirement: Only research organisations are recorded as institutions or companies
Extraction SHALL record an institution or a company only for a university, hospital, research institute, company, funder or public body that the article names. It SHALL NOT record a journal, a news outlet, a bank or an investment analyst as one. Entities already recorded are not changed by this requirement; the organisation registry's approval rule keeps them from being identified.

#### Scenario: Article names the journal and the newspaper that reported first
- **WHEN** an article says a study was published in a journal and was first reported by a newspaper
- **THEN** neither the journal nor the newspaper is recorded as an institution or a company
