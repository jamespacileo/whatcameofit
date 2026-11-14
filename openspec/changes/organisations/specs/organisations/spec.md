# Spec Delta

## Purpose

States which organisations a claim names, in what role, and what an open registry says each one is, so that a reader can see who is behind a reported breakthrough without the site passing any judgement on them.

## ADDED Requirements

### Requirement: One organisation per identity
The export SHALL list, for each published claim, each organisation the claim names once. Two names that an approved match ties to the same registry record SHALL be one organisation. An organisation with no approved match SHALL be listed under the name it was given.

#### Scenario: University named in the report and sponsoring a trial
- **WHEN** a report names "Kyoto University" and a trial's lead sponsor is "Kyoto University Hospital", and both are matched to different registry records
- **THEN** the export lists two organisations

#### Scenario: Same organisation under two spellings
- **WHEN** a report's "UCLA" and a trial's sponsor "University of California, Los Angeles" have approved matches to one registry record
- **THEN** the export lists one organisation with both roles

### Requirement: Roles
Each organisation SHALL carry every role it plays for the claim: named in a report, with the report's address, or sponsor of a trial, with the trial's identifier. A role SHALL state what a source says and SHALL NOT state that the organisation endorses, funds or stands behind the claim.

#### Scenario: Sponsor of three trials
- **WHEN** one company is the lead sponsor of three of a claim's trials
- **THEN** it is listed once, as sponsor, with the three trial identifiers

#### Scenario: Organisation named in two reports
- **WHEN** two of a claim's source articles name the same institution
- **THEN** it is listed once, as named in a report, with both addresses

### Requirement: Identified organisations carry the registry's facts
An organisation with an approved match SHALL carry the registry's name for it, its kinds as codes, its country, its website, a link to its registry record, the match score and the date the record was read. No other fact about the organisation SHALL be carried.

#### Scenario: Identified university
- **WHEN** an institution's match is approved
- **THEN** the organisation carries the registry's name, an education kind, a country, a website, the record link, the score and the date read

### Requirement: Unidentified organisations say so
An organisation with no approved match SHALL be marked as not identified and SHALL carry only its given name and roles.

#### Scenario: Name the registry does not know
- **WHEN** a report names a start-up the registry returns no chosen match for
- **THEN** the organisation is listed by the report's name, marked not identified, with no kind, country or website

### Requirement: A person is never an organisation
A trial sponsor that is a person SHALL NOT become an organisation. No organisation SHALL carry the name of a person recorded for the claim.

#### Scenario: Sponsor-investigator
- **WHEN** a trial's lead sponsor is a person
- **THEN** no organisation is listed for that sponsor

### Requirement: A report published by an organisation it names is marked
A source article whose address is on the website of an identified organisation of its claim, or on a subdomain of it, SHALL be marked as published by that organisation. An article on any other site SHALL carry no such mark.

#### Scenario: University press release
- **WHEN** a claim's source article is at `www.kyoto-u.ac.jp` and the claim names Kyoto University, identified, with the website `kyoto-u.ac.jp`
- **THEN** the article is marked as published by Kyoto University

#### Scenario: Newspaper report
- **WHEN** a claim's source article is on a newspaper's site
- **THEN** the article carries no such mark

#### Scenario: Organisation not identified
- **WHEN** the organisation whose site holds the article has no approved match
- **THEN** the article carries no such mark

### Requirement: Organisations do not change the status
Organisations and the publisher mark SHALL NOT be inputs to a claim's status.

#### Scenario: Claim gains an industry sponsor
- **WHEN** a claim's organisations change
- **THEN** its status and explaining events are unchanged
