# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: The home page offers the claims in four orders`
- TO: `### Requirement: The home page offers the claims in five lists`

## MODIFIED Requirements

### Requirement: The home page offers the claims in five lists
Under the lookup, the home page SHALL offer these lists of published claims, in this order, and SHALL show one at a time, the first unless the address names another:

1. Headlines: every source article, newest first.
2. Claims: every published claim once, by the date it was first reported, newest first.
3. Status changes: every change from one status to another, newest first, each with the day, the status from that day and the status before it. A claim's first status is not a change.
4. Promises: every claim with a dated promise, in order of its latest promised date, earliest first, with the promise beside the status now.
5. No signal: every claim carrying the no-signal overlay, the most years first.

A list with no rows SHALL NOT be offered, except Headlines. Each list SHALL show how many rows it has. Every order SHALL be a date or a count from the record: the page SHALL NOT rank or grade claims, and SHALL NOT word a promise as kept, missed or late. The list in view SHALL be recorded in the page's address. With scripting off, every list SHALL be shown, one under the other.

#### Scenario: Lists on the home page
- **WHEN** one published claim has changed status twice, and another has a dated promise and the no-signal overlay
- **THEN** the home page offers Headlines, Claims with two rows, Status changes with two rows, Promises with one row and No signal with one row

#### Scenario: Every claim once
- **WHEN** a published claim has three source articles
- **THEN** it has three rows under Headlines and one row under Claims

#### Scenario: Claims in order of first report
- **WHEN** one claim was first reported on 12 November 2026 and another on 30 October 2026
- **THEN** the first is listed above the second under Claims, whatever their statuses or how much either has been tested

#### Scenario: A first status is not a change
- **WHEN** a claim's history holds only its first status
- **THEN** the claim has no row under Status changes

#### Scenario: A promise whose date has passed
- **WHEN** a claim's promised date is earlier than today
- **THEN** it is listed first under Promises with its status now, and the page adds no wording about the date having passed

#### Scenario: Nothing has gone quiet
- **WHEN** no published claim carries the no-signal overlay
- **THEN** the No signal list is not offered

#### Scenario: A list named in the address
- **WHEN** the home page is opened at an address naming the Claims list
- **THEN** that list is the one shown

## ADDED Requirements

### Requirement: The Claims list is narrowed and paged like the others
The home page's Claims list SHALL show each claim's name and headline, the date it was first reported, how much it has been tested in people, its latest dated promise where it has one, and its status with its place on the path. It SHALL be narrowed by the home page's status and topic controls and read a page at a time, as the other lists are.

#### Scenario: Narrowed to a status
- **WHEN** a reader picks Phase 3 trial among the home page's status counts while the Claims list is in view
- **THEN** the list shows only claims whose status is Phase 3 trial, and says how many there are

#### Scenario: Narrowed to a topic
- **WHEN** a reader picks a topic while the Claims list is in view
- **THEN** the list shows only that topic's claims

#### Scenario: More claims than a page holds
- **WHEN** 84 claims are published
- **THEN** the Claims list shows the first page and says which rows of 84 are in view

#### Scenario: Promise beside the record
- **WHEN** a listed claim has a dated promise for 2027
- **THEN** its row shows the promise on the site's promise colour, between how much it has been tested and its status

### Requirement: A list of claims says how much each has been tested in people
Wherever the site lists claims in its claims table, each row SHALL say whether the claim has been tested in people: with trials on record, how many, and beneath it the largest stated size and whether results are posted to the registry; with none, "None on record" and, where the claim records it, what its first report was about. The words SHALL be read by the same rule as the first answer of "The record in brief". A list that carries the column SHALL say, once, that it counts trials on record and does not say what they found. No row SHALL carry a result value, and nothing SHALL order or mark claims by how much they have been tested.

#### Scenario: Claim with three trials
- **WHEN** a list shows a claim with 3 trials on record, the largest stating 135 participants, all with results posted
- **THEN** its row says it was tested in 3 trials, with 135 people in the largest and results posted by all 3

#### Scenario: Claim with no trial
- **WHEN** a list shows a claim with no trial on record whose first report was about a study in animals
- **THEN** its row says "None on record" and that the first report was about a study in animals

#### Scenario: Trials with no results posted
- **WHEN** a list shows a claim with 2 trials on record, neither with results posted
- **THEN** its row says no results are posted

#### Scenario: Same words as the claim page
- **WHEN** a claim's page answers "Tested in people?" with "In 3 trials. 135 people in the largest"
- **THEN** every list that shows the claim gives the same count and the same size

#### Scenario: Topic page
- **WHEN** a reader opens a topic page
- **THEN** its table of claims carries the column, and the line that says what the column counts

#### Scenario: Narrow screen
- **WHEN** a reader opens a list of claims on a screen 320 pixels wide
- **THEN** each claim is a block with "Tested in people" as a labelled line, and the page is not widened
