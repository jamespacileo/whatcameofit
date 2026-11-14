# Spec Delta

## ADDED Requirements

### Requirement: A claim page summarises what is on record
A claim page whose claim has at least one trial or paper on record SHALL show a section, "At a glance", with a list headed "On record". Each line SHALL be fixed wording filled only with counts, sizes, years and dates taken from the trials and papers the page shows. A line that counts trials or papers SHALL link to those records on the page. The lines SHALL be chosen by rule alone; no model and no person writes them.

#### Scenario: Claim with completed trials
- **WHEN** a reader opens a claim with 3 trials on record, all in a completed state
- **THEN** the list says 3 trials are on record and that all are completed, and the line links to the trials on the page

#### Scenario: Largest trial with a comparison group
- **WHEN** the claim's largest trial enrolled 135 participants and its record names a sham comparator
- **THEN** the list says the largest trial enrolled 135 people and names what it was compared with, in the site's fixed wording for that kind of comparator

#### Scenario: Results posted
- **WHEN** 2 of the claim's 3 trials have results posted to the registry
- **THEN** the list says 2 of 3 trials have posted results and gives the date of the latest posting

#### Scenario: Papers on record
- **WHEN** the claim has 9 papers on record whose known years run from 2020 to 2023
- **THEN** the list says 9 papers are on record, published 2020 to 2023, and the line links to the papers on the page

#### Scenario: Trial with no stated enrolment
- **WHEN** no trial of the claim states how many participants it enrolled
- **THEN** the list has no line about the largest trial

#### Scenario: Claim with no trial and no paper
- **WHEN** a reader opens a claim with no trial and no paper on record
- **THEN** the page has no "At a glance" section and no placeholder for it

### Requirement: A claim page states what is not on record
The "At a glance" section SHALL show a second list, headed "Not on record", of absences found by rule in the same records. A line SHALL state only that a kind of record is absent, and where the rule has one, the date of the last record of that kind. A line SHALL NOT say why a record is absent, SHALL NOT predict, SHALL NOT advise and SHALL NOT use verdict wording. The section SHALL say, in one line, that it is built by fixed rules from the records on the page and is neither a verdict nor advice.

#### Scenario: No trial running
- **WHEN** a claim has trials on record and none is in a recruiting or active state
- **THEN** the list says no trial is running now and gives the date the last one completed

#### Scenario: No results posted
- **WHEN** a claim has trials on record and none has results posted to the registry
- **THEN** the list says no trial has posted results to the registry

#### Scenario: No comparison group
- **WHEN** a claim has trials on record and no trial's record names a comparator
- **THEN** the list says no trial on record had a comparison group

#### Scenario: Nothing absent by rule
- **WHEN** no absence rule applies to a claim
- **THEN** the "Not on record" list is left out and the "On record" list is shown alone

#### Scenario: Approval and phase are not repeated
- **WHEN** a reader opens a claim that is not approved
- **THEN** neither list has a line about approval, about a trial's phase or about whether a trial in people exists

#### Scenario: Line with verdict wording
- **WHEN** the site is built and a line's wording contains the word "abandoned"
- **THEN** the build fails and quotes the wording

### Requirement: A claim page links to its own sections
A claim page SHALL show, under the digest panel, a row of links to the page's sections: the "At a glance" section, the trials, the papers, the timetable and the background. A link SHALL carry the count of what its section lists where the section lists records, and the timetable's link SHALL carry the first and last year it shows. A section the page does not have SHALL NOT be linked. The row SHALL NOT move with the page as it scrolls.

#### Scenario: Claim with trials and papers
- **WHEN** a reader opens a claim with 3 trials and 9 papers on record
- **THEN** the row links to the trials with the count 3 and to the papers with the count 9, and each link leads to that section

#### Scenario: Claim with no papers
- **WHEN** a reader opens a claim with no paper on record
- **THEN** the row has no link to papers

#### Scenario: Narrow screen
- **WHEN** a reader opens a claim page on a screen 320 pixels wide
- **THEN** every link in the row can be reached, each is at least 44 pixels tall, and the page is not widened
