# Spec Delta

## Purpose

Records what a source article says about a claim's intervention beyond its timeline, in the site's own words and with how sure the pipeline is that the article says it, so that a reader can see what was reported apart from what is on record.

## ADDED Requirements

### Requirement: Statement record
A reported statement SHALL belong to one source article of one claim and SHALL have a text of at most 200 characters, a kind, a firmness, a speaker role, a basis, a confidence between 0 and 1, the date its article was read and a review state. No article SHALL have more than the configured number of statements, six by default.

#### Scenario: Article that says nine things
- **WHEN** an article makes nine statements about the intervention
- **THEN** at most six are stored for it

#### Scenario: Statement with no article
- **WHEN** a statement is created without a source article
- **THEN** the statement is refused

### Requirement: Kind of statement
A statement's kind SHALL be one of: effect, safety, how it works, who it could help, comparison with existing treatment, or what it could lead to. A timeline SHALL NOT be stored as a statement; it remains a promise.

#### Scenario: Report that gives a date
- **WHEN** an article says human trials will start by 2027
- **THEN** a promise is stored and no statement

#### Scenario: Report of an effect
- **WHEN** an article says the treatment cut pain for most patients in a study
- **THEN** a statement of the kind effect is stored

### Requirement: Firmness and speaker
A statement SHALL record whether the article puts it as fact or as a possibility, and who the article has saying it, as one of: the article itself, a researcher, a company, a patient, or another expert. The speaker SHALL be a role and SHALL NOT be a name.

#### Scenario: Researcher's hope
- **WHEN** an article quotes a named professor saying the treatment could replace surgery
- **THEN** the statement is stored as a possibility said by a researcher, and names no one

### Requirement: Basis as the article gives it
A statement SHALL record what the article says it rests on, as one of: a study in people, a study in animals, laboratory work, or not said. The basis SHALL be what the article says and SHALL NOT be taken from a registry or a paper.

#### Scenario: Effect reported from a mouse study
- **WHEN** an article reports an effect and says the study was in mice
- **THEN** the statement's basis is a study in animals

#### Scenario: Article that does not say
- **WHEN** an article states an effect and gives no source for it
- **THEN** the statement's basis is not said

### Requirement: Statements are in the site's own words
A statement's text SHALL NOT repeat a run of consecutive words of the article at or above the configured length, eight by default, SHALL NOT contain a quotation, and SHALL NOT contain the name of a person the article named. A statement that does SHALL be refused before it is stored, and the refusal SHALL be counted in the command's output.

#### Scenario: Statement that copies a sentence
- **WHEN** a proposed statement repeats ten consecutive words of the article
- **THEN** it is not stored and the output says one statement was refused for copying

#### Scenario: Statement that names a researcher
- **WHEN** a proposed statement contains the name of a person recorded for the claim
- **THEN** it is not stored

### Requirement: Each statement is checked against its article
While the article text is in memory, each proposed statement SHALL be put to a bounded decision with three options: the article says this, the article says something weaker, the article does not say this. The statement's confidence SHALL be the probability of the first option.

#### Scenario: Statement the article makes
- **WHEN** the decision gives "the article says this" a probability of 0.93
- **THEN** the statement's confidence is 0.93

#### Scenario: Statement stronger than the article
- **WHEN** the decision's choice is "the article says something weaker"
- **THEN** the statement's confidence is the probability of "the article says this", which is below one half

### Requirement: Statements are decided by rule
A new statement whose confidence is at or above the configured threshold SHALL be approved and recorded as approved by rule. One below it SHALL be pending. An operator SHALL be able to approve or reject a statement afterwards, and a rejected statement SHALL NOT be created again by a later run.

#### Scenario: Confident statement
- **WHEN** a statement has a confidence of 0.9 and the threshold is 0.8
- **THEN** it is approved and marked as approved by rule

#### Scenario: Unsure statement
- **WHEN** a statement has a confidence of 0.6 and the threshold is 0.8
- **THEN** it is pending and is not published

#### Scenario: Rejected statement found again
- **WHEN** a later run proposes a statement an operator rejected for the same article
- **THEN** it stays rejected and no new statement is created

### Requirement: Only approved statements are published
The export SHALL carry, for each published claim, its approved statements with their text, kind, firmness, speaker role, basis, confidence and the address of their article. Pending and rejected statements SHALL NOT appear in the export.

#### Scenario: Claim with four approved and two pending statements
- **WHEN** the export is built
- **THEN** the claim carries four statements, each with its confidence

### Requirement: Statements do not change the status
Reported statements SHALL NOT be inputs to a claim's status or to its evidence stage.

#### Scenario: Statement with a basis in people
- **WHEN** a preclinical-only claim gains an approved statement whose basis is a study in people
- **THEN** the claim's status, explaining events and evidence stage are unchanged
