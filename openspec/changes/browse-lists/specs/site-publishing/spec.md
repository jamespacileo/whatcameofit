## ADDED Requirements

### Requirement: Long lists are read a page at a time
Each list on the home page SHALL show ten rows at a time. Every other list of claims SHALL show 25 rows at a time. A list longer than one page SHALL have, directly under it, a control to step to the next and the previous page and a line saying which rows are shown and how many there are. A list that fits one page SHALL show no such control. Where a list can be narrowed by status, the narrowing SHALL apply to the whole list and SHALL return the reader to its first page.

Every row SHALL be in the page as built: with scripting off, and in print, the whole list SHALL be shown. The page in view SHALL be recorded in the page's address, and an address naming a page that does not exist SHALL show the nearest page that does.

#### Scenario: More rows than one page
- **WHEN** published claims have 104 source articles between them
- **THEN** the home page shows the ten newest, says "1–10 of 104 headlines", and the next step shows the eleventh to the twentieth

#### Scenario: A list that fits one page
- **WHEN** a topic has four published claims
- **THEN** all four are shown and no paging control is shown

#### Scenario: A page that does not exist
- **WHEN** the address names page 99 of a list with eleven pages
- **THEN** the eleventh page is shown

#### Scenario: Narrowing by status
- **WHEN** a reader on the second page of a year's claims picks a status
- **THEN** the claims at that status across the whole year are listed from their first page

#### Scenario: Scripting off
- **WHEN** the home page is opened with scripting off
- **THEN** every headline and every claim is listed

### Requirement: The home page offers the claims in four orders
Under the lookup, the home page SHALL offer these lists of published claims, in this order, and SHALL show one at a time, the first unless the address names another:

1. Headlines: every source article, newest first.
2. Status changes: every change from one status to another, newest first, each with the day, the status from that day and the status before it. A claim's first status is not a change.
3. Promises: every claim with a dated promise, in order of its latest promised date, earliest first, with the promise beside the status now.
4. No signal: every claim carrying the no-signal overlay, the most years first.

A list with no rows SHALL NOT be offered, except Headlines. Each list SHALL show how many rows it has. Every order SHALL be a date or a count from the record: the page SHALL NOT rank or grade claims, and SHALL NOT word a promise as kept, missed or late. The list in view SHALL be recorded in the page's address. With scripting off, every list SHALL be shown, one under the other.

#### Scenario: Lists on the home page
- **WHEN** one published claim has changed status twice, and another has a dated promise and the no-signal overlay
- **THEN** the home page offers Headlines, Status changes with two rows, Promises with one row and No signal with one row

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
- **WHEN** the home page is opened at an address naming the Status changes list
- **THEN** that list is the one shown
