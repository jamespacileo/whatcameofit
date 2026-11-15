# Spec Delta

## ADDED Requirements

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
