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
The system SHALL NOT read an article whose address the page reader answers is not allowed, for whatever reason the reader gives. Whether a site's robots.txt is a reason is the reader's to decide. The reason SHALL be shown to the operator.

#### Scenario: Disallowed URL
- **WHEN** an operator requests extraction for a URL and the reader answers that it is not allowed because of the site's robots.txt
- **THEN** the article is not read, the operator is told why, and is asked to supply the text directly

#### Scenario: An address the reader refuses for another reason
- **WHEN** an operator requests extraction for an address the reader answers is not allowed, for a reason other than robots.txt
- **THEN** the operator is told the reader's reason and is asked to supply the text directly

### Requirement: Pasted text
An operator SHALL be able to supply article text directly instead of having it fetched. Pasted text SHALL be handled under the same retention rules as fetched text.

#### Scenario: Paywalled article
- **WHEN** an operator supplies the text of a paywalled article together with its URL
- **THEN** extraction runs on the supplied text and the text is discarded afterwards

### Requirement: Archived copies
The system SHALL NOT look for an archived snapshot itself. When the page reader says the copy it returned came from an archive, the system SHALL extract from it and record the archive address with the article. When the reader returns no page, the operator SHALL be asked to supply the text directly.

#### Scenario: Dead link with a snapshot
- **WHEN** the reader returns the page and says it came from an archived snapshot
- **THEN** extraction uses it and the article record carries the snapshot URL

#### Scenario: Dead link without a snapshot
- **WHEN** the reader answers that the site did not serve the page
- **THEN** the operator is asked to supply the text directly

### Requirement: Drafts need confirmation
A draft produced by extraction SHALL be approved by rule when its output passes validation and it duplicates no existing claim. A draft that fails validation SHALL be rejected by rule, kept, and listed for the operator. The operator SHALL be able to edit any field of a claim after it is published and to archive it.

#### Scenario: Valid draft
- **WHEN** extraction produces a draft that passes validation and duplicates no claim
- **THEN** the draft is approved by rule and appears on the site after the next export

#### Scenario: Unapproved draft
- **WHEN** extraction produces a draft that fails validation, and no operator approves it
- **THEN** it is rejected by rule, kept, and does not appear on the public site

#### Scenario: Edited draft
- **WHEN** an operator corrects the headline of a rejected draft and approves it
- **THEN** the claim carries the corrected headline

#### Scenario: Edited claim
- **WHEN** an operator corrects the headline of a published claim
- **THEN** the claim carries the corrected headline after the next export

### Requirement: Other names are names
Extraction SHALL record as another name of the intervention only a name: a brand, a code or a generic name. A description the model returns as a name, such as "the drug" or "a one-time treatment", SHALL NOT be recorded.

#### Scenario: Article that only describes the intervention
- **WHEN** the model returns "EX-1", "the drug" and "experimental antibody jab" as other names
- **THEN** only "EX-1" is recorded

### Requirement: Preparing many claims
An operator SHALL be able to have unread articles read, registries searched and approved matches fetched for many claims with one command, several claims at a time. A step that fails SHALL be reported with its claim, and the claim's other steps SHALL still run. The command SHALL approve nothing and SHALL say how long each step took. Each part of a claim's preparation SHALL be a step of the work ledger whose record is the claim: reading its unread articles, looking up its substance, searching the registries, searching for papers, fetching its approved records, reading its trial records, and proposing its terms. A part that finished for a claim's current input SHALL NOT be done again by a later run. The command SHALL finish by saying, for each step, how many claims were done, put off, need a fix, failed and remain due.

#### Scenario: Article that cannot be read
- **WHEN** one of a claim's articles cannot be read
- **THEN** the failure is reported and the claim is still searched

#### Scenario: A run stopped half way through a claim
- **WHEN** a run is stopped after a claim's registries were searched and before its records were fetched, and is started again
- **THEN** the registries are not searched again, and the fetch runs

#### Scenario: A source is paused
- **WHEN** a registry cannot be asked during a run
- **THEN** the claims waiting for it stay due for that step, the steps that need other sources still run, and the report says how many wait and for what

#### Scenario: A publisher is temporarily unavailable
- **WHEN** the page reader reports a temporary site response (including 202, 429 or 503) for an unread source article
- **THEN** the article step is put off for the configured site wait and the next due run tries it again

#### Scenario: The ceiling is reached with free work still due
- **WHEN** the month's model spend has reached its ceiling
- **THEN** source-only work and a decision by rule can still finish, and each step requiring a model stops when it needs the paid call

#### Scenario: The model refuses its key during trial readings
- **WHEN** the model cannot be asked while reading trials
- **THEN** the step stops with its current and remaining claims due, keeps completed readings, and reports the provider's cause

#### Scenario: A source pauses after a paid part
- **WHEN** a claim's completed classifications are followed by a failed drug lookup which pauses its source
- **THEN** the step stops with the claim due and a later run reuses its completed classifications

#### Scenario: MeSH cannot resolve an entry term
- **WHEN** the vocabulary returns an entry term without the record that identifies its descriptor
- **THEN** the terms step reports the unresolved name and schedules another attempt

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

### Requirement: Preserve the stated product name
Extraction instructions SHALL prefer the most specific product name or code stated in the article over a broader category name. They SHALL NOT invent a product name or append a maker or mechanism. This SHALL use the existing extraction call.

#### Scenario: A named vaccine product
- **WHEN** an article supplies a vaccine product name or code
- **THEN** extraction is instructed to retain that identifier rather than replace it with COVID-19 vaccine

### Requirement: Alternate names preserve complete intervention scope
Extraction instructions SHALL ask only for names of the same complete intervention, excluding components, class members, broader categories, related substances and names omitting explicit stereochemistry, route or regimen restrictions. Before saving new synonyms, the pipeline SHALL exclude explicit regimen components using the existing whole-intervention boundary. Whole-regimen brand aliases SHALL remain eligible. No additional model call SHALL be introduced.

#### Scenario: A draft lists component names
- **GIVEN** a draft for EX-1 plus EX-2 lists EX-1, EX-2 and Dualex as alternate names
- **WHEN** its entities are saved
- **THEN** only Dualex is saved as an alternate name

#### Scenario: A brand is the primary name
- **GIVEN** a draft for Dualex lists EX-1 plus EX-2 and its individual components as alternate names
- **WHEN** its entities are saved
- **THEN** the whole-regimen alias is retained and component aliases are excluded

### Requirement: What a decision waits for
A claim a read drafted SHALL be decided by the rule for drafts only when its substance lookup, its registry search and the fetch of its approved records have finished for its current input. It SHALL NOT wait for its papers, its trial readings or its terms. Those SHALL stay due until they finish, for a claim that is decided as for one that is not.

#### Scenario: Terms failed and the claim is decided
- **WHEN** a claim's search and fetch finished and its terms could not be proposed
- **THEN** the claim is decided, and it is due for its terms on the next run

#### Scenario: The substance lookup did not finish
- **WHEN** a claim's registry search finished and its substance lookup failed
- **THEN** the claim is not decided, and stays pending until the lookup finishes

#### Scenario: Readings failed
- **WHEN** a claim's search and fetch finished and reading one of its trial records failed
- **THEN** the claim is decided, and that reading is due on the next run

#### Scenario: The DOI registry cannot answer about an article's paper
- **WHEN** the claim's trial search finished but the DOI registry cannot identify a paper entity
- **THEN** the trial search keeps its receipts, the paper lookup stays due, and the decision can proceed once its required steps finish

### Requirement: Unfinished parts of a published claim are completed
A run that prepares claims SHALL take, beside the claims awaiting review, every approved claim that is not archived and is due for a part of its preparation, so that a part left unfinished when the claim was decided is finished later without being asked for by name.

#### Scenario: A published claim with no terms
- **WHEN** an approved claim has no terms because proposing them failed when it was prepared
- **THEN** the next run that prepares claims proposes them

#### Scenario: A trial approved after the claim was published
- **WHEN** a trial match of a published claim is approved and its record has not been read
- **THEN** the next run reads it

#### Scenario: A paper approved after the claim was searched
- **WHEN** a related paper is approved after the last paper search
- **THEN** the next prepare looks up its stated trial numbers and considers it for origin paper

#### Scenario: The paper index is enabled after a page named a DOI
- **WHEN** the index was off when a claim was prepared and its article named a DOI
- **THEN** the unfinished lookup is reported and enabling the index makes the claim due for those identifiers

### Requirement: Search phrases
For an intervention the article describes without a product name, extraction SHALL give up to three search phrases: the words a registry or a paper would use for it. A search phrase SHALL be kept apart from the intervention's other names and SHALL NOT be shown as a name. A phrase that is only a generic word for a treatment, such as "the device", SHALL NOT be recorded.

#### Scenario: Device with no product name
- **WHEN** an article describes a wrist-worn device that stimulates the median nerve and gives it no name
- **THEN** the draft holds a search phrase such as "median nerve stimulation" and no other name

#### Scenario: Named drug
- **WHEN** an article names a drug by its generic name
- **THEN** the draft may hold no search phrase

### Requirement: People recorded are researchers
Extraction SHALL record a person only when the article names them as carrying out or leading the research. A patient, a relative, a reporter or a commentator SHALL NOT be recorded, by full name or by first name.

#### Scenario: Report featuring a patient
- **WHEN** an article names its reporter, a teenage patient by first name and the professor who led the study
- **THEN** the draft holds one person, the professor

#### Scenario: Article naming no researcher
- **WHEN** an article names only patients
- **THEN** the draft holds no person
