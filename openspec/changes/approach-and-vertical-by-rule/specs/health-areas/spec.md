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

### Requirement: Vertical check against the MeSH suggestion
For any claim, the pipeline SHALL report whether the group of its vertical agrees with the groups suggested from its approved trials' MeSH terms. The answer SHALL be one of: agrees, when one suggested group is the claim's group; disagrees, when groups are suggested and none is the claim's; no suggestion. The check SHALL read stored records only, SHALL NOT change a vertical, and SHALL NOT change whether or when a claim is published.

#### Scenario: Specific vertical in the suggested group
- **WHEN** a claim is filed under dementia and its trials suggest "Brain and nerves"
- **THEN** the check answers agrees

#### Scenario: One of two suggested groups
- **WHEN** a claim is filed under "Eyes and ears" and its trials suggest both "Eyes and ears" and "Diabetes and hormones"
- **THEN** the check answers agrees

#### Scenario: Suggested group differs
- **WHEN** a claim is filed under "Skin and hair" and its trials suggest only "Cancer"
- **THEN** the check answers disagrees, names "Cancer" and the MeSH term that suggested it, and the claim stays under "Skin and hair" and stays published

#### Scenario: Nothing to compare
- **WHEN** a claim has no approved trial, or its trials carry no MeSH term the table maps
- **THEN** the check answers no suggestion and says which of the two it is

### Requirement: Disagreeing verticals are reported
`thenwhat prepare` SHALL say how many of the claims it handled disagree in the vertical check. The pipeline SHALL list, on request, every unarchived claim that disagrees, with its slug, intervention, indication, the vertical it is filed under, and each suggested group with its MeSH term. The list SHALL also be available as tab-separated rows.

#### Scenario: Prepare reports disagreements
- **WHEN** `thenwhat prepare --pending` handles 40 claims and 3 of them disagree
- **THEN** its summary says 3 claims are filed under a group their trials do not suggest, and how to list them

#### Scenario: Rows for the fault tab
- **WHEN** an operator asks for the disagreeing claims as tab-separated rows
- **THEN** each row carries the slug, intervention, indication, filed vertical, suggested groups and MeSH terms, and no article text

#### Scenario: Nothing disagrees
- **WHEN** no unarchived claim disagrees
- **THEN** the list says so and names how many claims agreed and how many had no suggestion
