# health-areas Specification

## Purpose
Files every claim under a health area that a reader recognises: a group, a broad body system or disease area, and within it a vertical. It also tags each claim with the kind of approach it reports, separately from the disease. The site can then be browsed by condition without intervention types distorting the tree.

## Requirements

### Requirement: Groups are anchored to a standard classification
Every configured group SHALL name at least one UKCRC HRCS health category it covers, and every HRCS health category except "Generic health relevance", "Disputed aetiology and other" and "Congenital disorders" SHALL be covered by at least one group. The anchors SHALL stay in pipeline configuration. The export and the site SHALL NOT carry HRCS codes or names.

#### Scenario: Group without an anchor
- **WHEN** the configuration has a group that names no HRCS category
- **THEN** the pipeline's configuration check fails and names the group

#### Scenario: Uncovered category
- **WHEN** no group covers the HRCS category for respiratory conditions
- **THEN** the configuration check fails and names that category

#### Scenario: Export carries no HRCS data
- **WHEN** the export is built
- **THEN** it contains each group's slug and title and no HRCS code or name

### Requirement: Every vertical has a group
Every configured vertical SHALL belong to exactly one group.

#### Scenario: Vertical without a group
- **WHEN** the configuration has a vertical that names no group
- **THEN** the configuration check fails and names the vertical

### Requirement: Each group has a general vertical
Every group SHALL have a general vertical whose slug and title equal the group's. A claim that fits a group but none of its specific verticals SHALL be filed under the general vertical.

#### Scenario: Claim with no specific vertical
- **WHEN** an operator files a claim about epilepsy and "Brain and nerves" has no epilepsy vertical
- **THEN** the claim is filed under the vertical `brain-and-nerves`

#### Scenario: Group missing its general vertical
- **WHEN** the configuration has a group `lungs-and-breathing` with no vertical of the same slug
- **THEN** the configuration check fails and names the group

### Requirement: Approach facet
A claim MAY carry one approach from a configured set: drug, vaccine, gene therapy, cell therapy, tissue regeneration, transplant, device, surgery or procedure, and diet or lifestyle. An approach outside the set SHALL be refused, with the valid approaches listed. An approach SHALL NOT change a claim's status.

#### Scenario: Claim with an approach
- **WHEN** an operator enters a claim about a donor kidney grown in a pig with the approach transplant
- **THEN** the claim is stored with the approach transplant

#### Scenario: Unknown approach
- **WHEN** an operator enters the approach "miracle"
- **THEN** the claim is not created and the valid approaches are listed

#### Scenario: Claim without an approach
- **WHEN** an operator enters a claim and gives no approach
- **THEN** the claim is stored with no approach

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

### Requirement: Retired slugs keep their address after launch
Once the site has been deployed to its public address, a vertical slug that is renamed or retired SHALL be recorded with its successor, and its topic address SHALL redirect permanently to the successor's.

#### Scenario: Vertical renamed after launch
- **WHEN** the vertical `eyes-and-ears` is renamed to `sight-and-hearing` after launch
- **THEN** `/topic/eyes-and-ears` redirects permanently to `/topic/sight-and-hearing`

#### Scenario: Retired vertical with no record
- **WHEN** a vertical slug is removed after launch and no successor is recorded
- **THEN** the site build fails and names the slug

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

#### Scenario: An editor commits while a rule is fetching

- **WHEN** a fetch starts with a rule-owned approach and a person saves gene therapy before the rule tries to write drug
- **THEN** the committed approach, its human owner and its basis survive the later write

### Requirement: Claims the rule could not give an approach are listed
The pipeline SHALL list, on request, each claim that has approved trials and no approach, with the reason the rule set none: the types found with their trial counts, or that no approved trial lists the intervention by an equal name.

#### Scenario: Conflicting types listed
- **WHEN** an operator asks for the claims the rule gave no approach
- **THEN** a claim whose trials list drug twice and biological once is shown with both types and their counts

#### Scenario: Unmapped type listed
- **WHEN** a claim's only type is biological
- **THEN** it is shown with that type and the note that the table does not map it
