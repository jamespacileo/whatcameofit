# Spec Delta

## ADDED Requirements

### Requirement: A long timetable folds by year
On a claim page whose timetable holds more than 20 records, the years before last year SHALL each be drawn as one line that states how many records the year holds and of which kinds, and that opens to those records. The current year and last year SHALL be drawn open. A year that a promise names SHALL be drawn open, so that a promise is never folded away from its record. A folded year that holds a record the status rests on SHALL say so with the basis mark and in words for a screen reader. A link to a record in a folded year SHALL open that year. While the timetable is narrowed to one kind of entry, and on paper, every year SHALL be open. A claim with 20 records or fewer SHALL NOT be folded.

#### Scenario: A claim with many records
- **WHEN** a reader opens a claim with 147 records
- **THEN** this year's and last year's records are listed, and each earlier year is one line with its count and its kinds

#### Scenario: Following the status to its record
- **WHEN** a reader follows a link from the status card to a record in a folded year
- **THEN** that year opens and the record is in view

#### Scenario: A short record
- **WHEN** a claim has five records
- **THEN** every year is drawn open

### Requirement: A record page's sections share one container and one opening note
On a claim page and a topic page, every section's rows SHALL stand between a rule above and a hairline below, with no rounded frame around a table. A section's opening note SHALL be set in the note size and the muted colour. A note that says the page is not advice SHALL NOT be cut short.

#### Scenario: Reading down the page
- **WHEN** a reader scrolls a claim page
- **THEN** each section starts with its heading, at most one muted note, and rows under one rule, whether the section is a table or a list
