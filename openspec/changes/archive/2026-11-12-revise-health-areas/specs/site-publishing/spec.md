# Spec Delta

## ADDED Requirements

### Requirement: Approach on the claim page
A claim page SHALL show the label of the claim's approach when it has one, in the site's own wording, and SHALL show nothing in its place when it has none. The label SHALL describe the kind of intervention only, and SHALL NOT suggest that the intervention works or is available.

#### Scenario: Claim with an approach
- **WHEN** a reader opens a claim whose approach is gene therapy
- **THEN** the page shows the label for gene therapy

#### Scenario: Claim without an approach
- **WHEN** a reader opens a claim with no approach
- **THEN** the page shows no approach label and no placeholder

#### Scenario: Approach code without site wording
- **WHEN** the export carries an approach code that the site has no label for
- **THEN** the site build fails and names the code

### Requirement: Topics page lists every group with claims
The topics page SHALL list each group that has at least one published claim, with that group's verticals that have published claims under it. A group or vertical with no published claim SHALL NOT be listed.

#### Scenario: Group with one listed vertical
- **WHEN** the group "Kidneys and bladder" has one published claim, filed under its general vertical
- **THEN** the topics page lists "Kidneys and bladder" with that one vertical

#### Scenario: Empty group
- **WHEN** no published claim is filed under "Pregnancy and fertility"
- **THEN** the topics page does not list that group
