# Spec Delta

## Purpose

Says how stored leads that tell one story are grouped before they are read, so that a story many outlets ran costs one or two reads, and what a group may and may not change.

## ADDED Requirements

### Requirement: Leads that tell one story are grouped by their titles
Two link leads SHALL be in one story group when a versioned measure of how alike their titles are is at or above the group threshold and their dates are within the configured number of days of each other. A lead that is alike to no other SHALL be a group of one. The measure SHALL use titles only, SHALL send no request to a news outlet, and SHALL hold no article text.

#### Scenario: One announcement, many outlets
- **WHEN** twelve leads dated the same week report one regulator's warning in different words
- **THEN** they are in one story group

#### Scenario: The same treatment, another event
- **WHEN** two leads name one treatment, one reporting a trial's results and one a regulator's decision months later
- **THEN** they are in different groups

### Requirement: A group orders reading and settles nothing
Within a story group, leads that triage passed or held SHALL be read in the order of outlet kinds the operator sets, and reading in that group SHALL stop once the claim its reads joined or drafted holds enough articles, by the setting that already says how many articles one claim needs. A lead left unread for that reason SHALL NOT be rejected, SHALL keep its triage score, and SHALL be due again when the setting rises or the group's version changes.

#### Scenario: A story with twelve leads
- **WHEN** a group holds twelve passed leads and a claim needs three articles
- **THEN** leads are read in the set order until the claim holds three, and the others stay unread and not rejected

#### Scenario: The first reads did not make a claim
- **WHEN** the first two leads read in a group drafted and joined no claim
- **THEN** the next lead in the group is read

### Requirement: A group decides nothing else
A story group SHALL NOT change a triage score, approve or reject a lead, link a lead to a trial, create or change a claim, a match, an evidence event or a status, and SHALL NOT appear in the export or on the site.

#### Scenario: Export after grouping
- **WHEN** leads are grouped and nothing has been read
- **THEN** the export is identical to the one produced before

### Requirement: The threshold comes from a judged sample
The group threshold SHALL be a setting with no default. It SHALL be chosen from a sample of pairs judged as the same story or not, and stored with the measure's version, the sample's size and the share of judged pairs it places rightly. While it is empty, no lead SHALL be grouped and leads SHALL be read as they are without groups.

#### Scenario: No threshold set
- **WHEN** the reading step runs and the threshold is not configured
- **THEN** every lead is read as before, and the report says grouping is off and why

### Requirement: The measure is versioned and named in the settings
The model the measure uses SHALL be named in the settings and never in code. Each group SHALL record the measure's version. A new version SHALL group every lead in scope again.

#### Scenario: A new version
- **WHEN** the measure's version is raised
- **THEN** leads are grouped again and each group records the new version

### Requirement: Grouping is reported
`thenwhat backfill story-groups` SHALL report how many leads are grouped, how many groups there are by size, and how many reads the stop within a group has left unread.

#### Scenario: After a day's headlines
- **WHEN** 240 passed leads fall into 130 groups
- **THEN** the report gives both figures and the count of groups of each size
