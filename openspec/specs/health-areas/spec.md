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
For a claim with approved trial matches, the pipeline SHALL suggest a group from those trials' MeSH condition terms and ancestor terms, using a fixed lookup table. It SHALL show the MeSH term that produced the suggestion. A suggestion SHALL NOT change a claim's vertical. Only an operator SHALL.

#### Scenario: Trials point to one group
- **WHEN** a claim's approved trials carry the MeSH ancestor "Skin Diseases"
- **THEN** the pipeline suggests the group "Skin and hair" and names "Skin Diseases" as the reason, and the claim's vertical is unchanged

#### Scenario: Trials point to different groups
- **WHEN** a claim's approved trials map to two different groups
- **THEN** both groups are shown, each with its MeSH term, and none is preferred

#### Scenario: No usable MeSH term
- **WHEN** a claim's approved trials carry no MeSH term in the lookup table
- **THEN** no group is suggested and the pipeline says why

### Requirement: Retired slugs keep their address after launch
Once the site has been deployed to its public address, a vertical slug that is renamed or retired SHALL be recorded with its successor, and its topic address SHALL redirect permanently to the successor's.

#### Scenario: Vertical renamed after launch
- **WHEN** the vertical `eyes-and-ears` is renamed to `sight-and-hearing` after launch
- **THEN** `/topic/eyes-and-ears` redirects permanently to `/topic/sight-and-hearing`

#### Scenario: Retired vertical with no record
- **WHEN** a vertical slug is removed after launch and no successor is recorded
- **THEN** the site build fails and names the slug
