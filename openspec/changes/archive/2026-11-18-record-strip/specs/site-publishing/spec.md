# Spec Delta

## ADDED Requirements

### Requirement: A record strip shows a claim's dated records on one time axis
The site SHALL be able to draw, for any published claim, a record strip: one horizontal time axis that ends at the day the registries were last checked, with a mark at the date of each news report, dated registry record, posting of trial results, regulator's decision and dated promise. Kinds of mark SHALL differ by shape or position, not by colour alone. The strip SHALL be built from the export alone, with no script in the reader's browser.

#### Scenario: Records before and after a report
- **WHEN** a claim first reported in 2026 has a trial registered in 2012 and results posted in 2015
- **THEN** its strip shows the registration mark and the results mark to the left of the report mark, each at its own date

#### Scenario: A claim with a report and nothing else
- **WHEN** a claim has one news report and no dated record
- **THEN** its strip is drawn with the axis, the report mark and the last-check end, and nothing else

#### Scenario: A promise with no date in the export
- **WHEN** a claim's report holds a promise whose date the export does not hold
- **THEN** the strip has no promise mark: a position is never estimated

#### Scenario: A promise dated after the last check
- **WHEN** a claim's promise is dated after the day the registries were last checked
- **THEN** the strip has no promise mark

#### Scenario: Many records in one year
- **WHEN** a claim has 79 dated records
- **THEN** every record is marked at its own date, marks may overlap, and a mark for posted results is never hidden by a mark for another record

### Requirement: Every record strip uses one time scale
Every record strip on the site SHALL use the same time scale: the axis SHALL start at the same year and end at the day the registries were last checked, so that the same date falls at the same place in every strip of the same width. The start year SHALL be fixed at build from the earliest dated record among published claims.

#### Scenario: Two claims in one list
- **WHEN** a list shows a claim reported in 2017 and a claim reported in 2026
- **THEN** the 2017 report mark sits to the left of the 2026 report mark by the same distance in both strips' scale

#### Scenario: A claim reported this year
- **WHEN** a claim was first reported in the year of the last check and has no earlier record
- **THEN** in a list its report mark sits near the right end of the axis and the rest of the axis is drawn empty

### Requirement: A claim page draws the claim's records on its own axis
A claim page SHALL draw the claim's record strip at the head of its recorded records, on an axis of its own: from the year of the claim's earliest dated record, or five years before its first report when that is earlier, to the day the registries were last checked. The strip SHALL have the axis's first year and the day of the last check written under its ends, and a key under it SHALL name only the kinds of mark the strip draws.

#### Scenario: A trial years before the report
- **WHEN** a claim reported in 2026 has a trial registered in 2012
- **THEN** its page's strip starts at 2012, is notched every year, and the registration mark sits at the left of the axis

#### Scenario: A report and nothing else
- **WHEN** a claim reported in 2026 has no dated record
- **THEN** its page's strip starts at 2021 and its key names the news report and no other mark

### Requirement: A record strip does not judge
The axis of a record strip SHALL be drawn at one weight and one colour along its whole length. A stretch with no mark SHALL NOT be set apart, and nothing SHALL be filled between two marks. A promise mark SHALL NOT differ according to whether its date has passed. Marks of one kind SHALL be one size. The strip SHALL NOT use a tick, a cross, or red and green.

#### Scenario: Two trials of different size
- **WHEN** a claim has a trial of 40 people and a trial of 981 people
- **THEN** their registration marks are the same size

#### Scenario: No signal for nine years
- **WHEN** a claim reported in 2017 has no dated record since
- **THEN** the axis from the report mark to the last-check end is drawn exactly as the rest of the axis

#### Scenario: A promised date that has passed
- **WHEN** a claim's report promised trials for 2020 and no trial is on record
- **THEN** the promise mark for 2020 is drawn the same as a promise mark that a record followed

### Requirement: A record strip is readable without seeing it
A record strip SHALL be exposed to assistive technology as one image with a text alternative in sentences that state counts and dates only. Its marks SHALL stay distinguishable when printed and when the reader's system forces its own colours. The strip SHALL NOT be a control and SHALL NOT respond to pointing.

#### Scenario: Screen reader on a report row
- **WHEN** a screen reader reaches the strip of a claim with five trials on record, the first registered in 2012
- **THEN** it reads that the first trial was registered in 2012, 14 years before the report, and that 5 trials are on record with the counts completed and with results posted

#### Scenario: A claim with a report and nothing else
- **WHEN** a screen reader reaches the strip of a claim with one report and no dated record
- **THEN** it reads the number of reports and that no dated record is on file as of the last check

### Requirement: Claim list tables carry the record strip
Every claim list table SHALL show each claim's record strip on the axis every list shares, drawing registry records, posted results and news reports only: a promise is in the list's own column and a regulator's decision is in the status. On a wide screen the strips SHALL sit in one column at one width so their axes align from row to row. The status label SHALL remain in sight in the same row.

#### Scenario: Topic index
- **WHEN** a reader opens a topic index with 18 claims on a wide screen
- **THEN** each row shows the claim's strip in the same column and the claim's status label

#### Scenario: Phone
- **WHEN** the same index is opened below the site's one breakpoint
- **THEN** each claim's strip is drawn across the width of its row, under its status

### Requirement: The marks of a record strip are named once per page
A page that shows a record strip SHALL carry one key that names each kind of mark in words, before the first strip. The guide SHALL hold an entry that explains the strip, what its marks rest on in the records and what it does not tell the reader.

#### Scenario: Topic index
- **WHEN** a reader opens a topic index
- **THEN** the key above the table names the registry record, results posted and news report marks, and gives the years the axis runs between

#### Scenario: Home page
- **WHEN** a reader opens the home page
- **THEN** the day list shows no record strip and no key

#### Scenario: Guide entry missing
- **WHEN** the site is built and the guide has no entry for the record strip
- **THEN** the build fails and says so

## MODIFIED Requirements

### Requirement: A report row says what the records add
Under the outlet's title, a report row SHALL show at most one line of counts in numerals: how many trials are on record and how many have posted results. A count the export does not hold SHALL be left out, never estimated. The row SHALL NOT draw a record strip; the claim page does. The row SHALL also carry at most two sentences built by fixed rules from the claim's records: the first two that apply, in one fixed order of preference, each stating a count or a date only. These sentences SHALL follow the counts for a screen reader and SHALL NOT be shown in sight on the row.

#### Scenario: The order of preference
- **WHEN** more than two sentences apply to a claim
- **THEN** the row's screen-reader text carries the first two of: a regulator's decision with its date; the year of the first registered trial, when it is two or more calendar years before the report; how many trials are on record, how many are completed and how many have posted results; that no record is dated since the first report, with the no-signal years

#### Scenario: A trial registered long before the report
- **WHEN** a claim reported in 2026 has five trials on record, the first registered in 2012, three completed and two with results posted
- **THEN** the row shows the counts "5 trials" and "2 with results posted" in numerals; its screen-reader text says the first trial was registered in 2012, 14 years before the report, and that 5 trials are on record, 3 completed, 2 with results posted

#### Scenario: Nothing since the report
- **WHEN** a claim reported in 2017 from laboratory work has no trial and carries "No signal for 9 years"
- **THEN** the row shows the count "0 trials", and its screen-reader text says no record is dated in the 9 years since the first report

#### Scenario: Nothing to add
- **WHEN** a claim reported from an animal study has no trial, no regulator’s decision and no no-signal note
- **THEN** the row shows the count "0 trials" and no sentence

#### Scenario: An approval
- **WHEN** a claim has a regulator's approval dated 3 September 2026
- **THEN** the claim page's strip shows the decision mark at that date and the first sentence of the row's screen-reader text is the approval as recorded, with that date

### Requirement: Row sentences describe records and nothing else
A sentence the site writes for a home page row or for a record strip's text alternative, a line of counts beside a strip, and the words of a strip's key SHALL pass the site's checks for verdict wording and for wording about how a trial turned out. None SHALL say that a promise was kept, missed or late, characterise the time between a report and a record, or present a trial as open to join. A build SHALL fail when the wording of any of them breaks one of these rules.

#### Scenario: A promised date that has passed
- **WHEN** a claim's report promised trials for 2020 and no trial is on record
- **THEN** the row shows the promise with its year and the status now, the strip marks 2020 as a promised date, and no sentence, count or key says the date passed or the promise was missed

#### Scenario: Wording that judges
- **WHEN** a sentence's wording is changed to include "still" or "only" before a count
- **THEN** the site's build fails and names the sentence

#### Scenario: Key wording with a verdict
- **WHEN** the site is built and the key names a mark with verdict wording
- **THEN** the build fails and names the wording
