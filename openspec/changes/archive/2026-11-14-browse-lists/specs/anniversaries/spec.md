## ADDED Requirements

### Requirement: Anniversaries on the home page
The home page SHALL show, to a reader with scripting on, the published claims whose first report has its anniversary on the reader's own date, each with the year first reported and the claim's current status, and a link to the anniversaries page. When no anniversary falls on that date, it SHALL show those of the next date that has one and SHALL name that date. A first report less than one whole year before the date shown SHALL NOT be listed. In a year that is not a leap year, a report of 29 February SHALL fall on 28 February. The block SHALL state facts only, as the anniversaries page does. With scripting off, or when no claim has a first-reported date, the block SHALL NOT be shown.

#### Scenario: An anniversary today
- **WHEN** a reader opens the home page on 13 November 2026 and a claim was first reported on 13 November 2021
- **THEN** the claim is listed under "On this day" with 2021 and its current status

#### Scenario: No anniversary today
- **WHEN** no earlier first report falls on the reader's date and the next that does is on 20 November
- **THEN** the block is headed with 20 November and lists that day's claims

#### Scenario: Reported this year
- **WHEN** a claim was first reported earlier on the reader's date, in the same year
- **THEN** it is not listed

#### Scenario: A leap-day report in a common year
- **WHEN** a claim was first reported on 29 February 2020 and the reader's date is 28 February 2027
- **THEN** the claim is listed under "On this day"
