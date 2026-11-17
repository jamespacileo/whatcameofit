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

### Requirement: The trials on a claim page read as one table
On a wide screen the trials table's columns SHALL be named once, above every group, and SHALL stay in view while the groups scroll. Each group's own column names SHALL remain available to a screen reader. Each group SHALL be introduced by a row that names it and states how many trials it holds.

#### Scenario: Scrolling the trials
- **WHEN** a reader scrolls through a claim's trials at 1400 pixels wide
- **THEN** the column names stay at the top of the view and each group begins with a row naming it and its count

### Requirement: A record page's sections share two column stops and one right edge
On a wide screen the sections of a record page SHALL share two column stops: what a label, a group's name, a statement's kind or a year names SHALL start on the first, and a second column (the brief's answers, a paper's ties, an organisation's parts) SHALL start on the second. Every list, strip and rule of a section SHALL run to the section's right edge. A table with named columns MAY keep its own columns.

#### Scenario: Reading down the page
- **WHEN** a reader scrolls a claim page on a wide screen
- **THEN** the values of "At a glance", the questions of "The record in brief", a report's statements and the timetable's records start at one distance from the left edge, and no section's rule stops short of the right edge

### Requirement: Rows that open share one press
An answer of "The record in brief" SHALL open as a fact row does: by its whole line, which is tinted under the pointer and while open and ends in the round fold mark; what it opens to SHALL lie on the page's ground. Anything that folds the rest of a list or a part of a section SHALL be drawn as one kind of line with a chevron that turns.

#### Scenario: Opening an answer
- **WHEN** a reader opens "Tested in people?"
- **THEN** the line is tinted, its mark points up, and the sentences under it stand on the page's ground with no panel around them

