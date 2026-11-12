# Spec Delta

## ADDED Requirements

### Requirement: A lookup returns ranked trial candidates for a piece of text
Given the text of a news article or a post, the lookup SHALL name the treatment and the condition the text reports, search the trial registry for them, and return the records found, each with the probability that it is a trial of that treatment for that condition, likeliest first. A record for the same treatment in another condition SHALL be returned as such, below the matches. The lookup SHALL NOT approve anything, derive a status, or present its answer as reviewed.

#### Scenario: Article about a treatment with registered trials
- **WHEN** the text reports a named treatment for a condition, and the registry holds one trial of it for that condition and one for another condition
- **THEN** both are returned, the first as a match with the higher score, the second as the same treatment for another indication

#### Scenario: Text that is not about a treatment
- **WHEN** the text reports no specific treatment for a specific condition
- **THEN** the lookup says so, searches nothing and returns no candidates

### Requirement: Every way of finding the trial is used
The lookup SHALL look up directly any registry number the text states. It SHALL search the registry for the treatment's name, each other name the text gives, each part of a combination, each name the model knows the treatment by, and up to three search phrases for a treatment with no product name, each within the reported condition. A description that is not a name SHALL NOT be searched for as a name, and a registry number SHALL NOT be treated as a name. Names that come from the model's knowledge SHALL be reported apart from the names the text gives.

#### Scenario: Text that states a registry number
- **WHEN** the text contains a ClinicalTrials.gov number in any letter case
- **THEN** that trial is among the candidates even when no name search finds it

#### Scenario: Registry lists the treatment under a name the text does not give
- **WHEN** the model knows a development code for the treatment that the text does not state, and the registry lists a trial under that code
- **THEN** the trial is among the candidates and the code is reported as a name the text does not give

#### Scenario: Combination of two treatments
- **WHEN** the text reports "A and B" as one treatment and the registry lists a trial under B
- **THEN** that trial is among the candidates

### Requirement: A tracked claim is named
When a claim is already tracked under one of the names found, the lookup SHALL name that claim.

#### Scenario: Treatment already tracked
- **WHEN** the text names a treatment by a name recorded as another name of a tracked claim's intervention
- **THEN** the answer names that claim

### Requirement: A lookup keeps nothing it read
A lookup SHALL NOT store a claim, an entity, a match, an article or any of the text. It MAY record that a model was called and what it cost.

#### Scenario: Nothing is kept
- **WHEN** a lookup finds a trial
- **THEN** the numbers of claims, entities, matches and articles stored are unchanged
