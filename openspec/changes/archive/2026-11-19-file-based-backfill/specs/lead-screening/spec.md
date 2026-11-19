# Spec Delta

## MODIFIED Requirements

### Requirement: Screening uses stored data only
Screening SHALL send no request, call no model and record no spend. It SHALL decide from the run's own files and the run's reference file, and from nothing else.

#### Scenario: A screening run
- **WHEN** screening runs over 50,000 leads
- **THEN** no request is sent, no model is called and no usage is recorded

#### Scenario: No reference file
- **WHEN** screening is run in a run that has no reference file
- **THEN** it refuses and names the pull command

### Requirement: Outlet rule
A lead SHALL go on to scoring only when its outlet kind is general news, health or clinical trade press, or press release. A lead whose outlet kind is journal or paper index, regulator, video, or social SHALL be kept with the outcome awaiting a route, and SHALL NOT be scored or read until a route for its kind exists. The load applies the list: a run holds no lead on an outlet that is on no list. No model decides an outlet's kind.

#### Scenario: A link to a listed outlet
- **WHEN** a post links to an outlet listed as general news
- **THEN** the run holds a lead for it and its outcome is in scope

#### Scenario: A link to a journal
- **WHEN** a post links to a paper on a listed journal's site
- **THEN** the run holds a lead for it with the outcome awaiting a route, and no model call is made for it

#### Scenario: A link to a code repository
- **WHEN** a post links to a domain that is on no list
- **THEN** the run holds no lead for it and the tally counts it

#### Scenario: A domain is added to the list
- **WHEN** a domain is added to the outlet list and a new run is started over the same files
- **THEN** the leads on that domain are in scope in the new run

### Requirement: Articles already tracked
A lead whose address is the address of a source article in the reference file SHALL get the outcome already tracked, with a link to that claim. A lead the reference file gives a read outcome for SHALL get the outcome already read elsewhere. Neither SHALL be scored or read.

#### Scenario: An address with a tracking parameter
- **WHEN** a lead's address is a source article's with a `utm_source` parameter added
- **THEN** its outcome is already tracked

#### Scenario: Read by another device
- **WHEN** a lead's address key is one another device's pushed run read
- **THEN** its outcome is already read elsewhere

### Requirement: Screening report
`thenwhat backfill runs report` SHALL report, by platform and community, how many shares were loaded, how many leads are in scope by outlet kind, how many are already tracked, how many are already read elsewhere, how many are linked to a claim and how many to a registry trial. It SHALL list the unlisted domains with the most link posts, and those with the most posts naming a topic word, from the run's tally.

#### Scenario: After a load and a screening run
- **WHEN** 50,000 leads are loaded and screened
- **THEN** the report gives the counts for each platform and community, and the twenty unlisted domains with the most link posts

#### Scenario: Nothing screened yet
- **WHEN** no lead has been screened
- **THEN** the report says so and gives no percentages
