# Spec Delta

## ADDED Requirements

### Requirement: Approach set by rule from registry intervention types
For a claim with no approach, the pipeline SHALL set one when the claim's approved trials list its intervention, under a name equal to the intervention's name or one of its synonyms, with exactly one registry intervention type, and a checked-in table maps that type to a configured approach. No model SHALL take part. A trial stored more than once SHALL count once. An intervention a trial lists under another name SHALL NOT be read.

#### Scenario: One mapped type
- **WHEN** a claim for semaglutide has no approach and 3 approved trials list "Semaglutide" with the type drug
- **THEN** the claim's approach becomes drug

#### Scenario: Comparator ignored
- **WHEN** an approved trial lists the claim's intervention with the type device and a sham comparator with the type other
- **THEN** only the type device is read

#### Scenario: Types do not agree
- **WHEN** 2 approved trials list the claim's intervention with the type drug and 1 with the type biological
- **THEN** the claim's approach stays empty

#### Scenario: Type with no approach in the table
- **WHEN** every approved trial lists the claim's intervention with the type biological, which the table does not map
- **THEN** the claim's approach stays empty

#### Scenario: No approved trial names the intervention
- **WHEN** a claim has no approved trial, or none lists its intervention by an equal name
- **THEN** the claim's approach stays empty

### Requirement: An approach records who set it and on what basis
A claim's approach SHALL record who set it: a person, the seed, an assistant or a rule. An approach set by rule SHALL also record its basis: the registry intervention type and the number of approved trials that list it. An approach stored before this requirement, with no record of who set it, SHALL be treated as not set by rule.

#### Scenario: Approach set by rule
- **WHEN** the rule sets the approach drug from 3 approved trials
- **THEN** the claim records that a rule set it, with the type drug and the count 3

#### Scenario: Approach set by an operator
- **WHEN** an operator edits a claim's approach to vaccine
- **THEN** the claim records that a person set it, and no basis

### Requirement: A rule never overwrites an approach set otherwise
The rule SHALL change a claim's approach only when the approach is empty or was set by rule. It SHALL leave an approach set by a person, the seed or an assistant as it is, and one stored with no record of who set it.

#### Scenario: Operator's approach kept
- **WHEN** an operator set a claim's approach to gene therapy and its approved trials list the intervention with the type drug
- **THEN** the approach stays gene therapy

#### Scenario: Rule-set approach no longer supported
- **WHEN** a rule set a claim's approach to drug and a newly approved trial lists the intervention with the type biological
- **THEN** the approach becomes empty and its basis is removed

#### Scenario: Rule-set approach still supported
- **WHEN** a rule set a claim's approach to drug from 2 trials and a third approved trial also lists the type drug
- **THEN** the approach stays drug and its basis counts 3 trials

### Requirement: Claims the rule could not give an approach are listed
The pipeline SHALL list, on request, each claim that has approved trials and no approach, with the reason the rule set none: the types found with their trial counts, or that no approved trial lists the intervention by an equal name.

#### Scenario: Conflicting types listed
- **WHEN** an operator asks for the claims the rule gave no approach
- **THEN** a claim whose trials list drug twice and biological once is shown with both types and their counts

#### Scenario: Unmapped type listed
- **WHEN** a claim's only type is biological
- **THEN** it is shown with that type and the note that the table does not map it

## MODIFIED Requirements

### Requirement: Suggested group from matched trials
For a claim with clinical categories, the pipeline SHALL suggest each group that the topic mapping derives from those categories. It SHALL show the MeSH term that produced each suggestion. A suggestion SHALL NOT change a claim's vertical. Only an operator SHALL.

#### Scenario: Trials point to one group
- **WHEN** a claim's clinical categories sit under the MeSH category "Skin Diseases"
- **THEN** the pipeline suggests the group "Skin and hair" and names the claim's category and "Skin Diseases" as the reason, and the claim's vertical is unchanged

#### Scenario: Trials point to different groups
- **WHEN** a claim's clinical categories derive two different groups
- **THEN** both groups are shown, each with its MeSH term, and none is preferred

#### Scenario: No usable MeSH term
- **WHEN** a claim has no clinical category, or none that the topic mapping covers
- **THEN** no group is suggested and the pipeline says which of the two it is
