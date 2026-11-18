# Spec Delta

## ADDED Requirements

### Requirement: A claim page's lists, tables and panels share one scale
The lists of labelled values, the record rows, the tables and the pale panels of a claim page SHALL take their row padding, the rule between rows, the size of labels and column heads, the size of notes, and a panel's padding and corner from one set of values defined once. A build check SHALL fail when one of them is given a value of its own.

#### Scenario: A row in any section
- **WHEN** a reader compares a row of "At a glance", a registry record, a trial and a timetable row
- **THEN** each has the same space above and below it and the same soft rule between it and the next

#### Scenario: A section drifts
- **WHEN** a stylesheet change gives a record row its own padding
- **THEN** the site's tests fail and name the row

### Requirement: Every table on a claim page has the same head
The timetable, the trials table and the index table SHALL have the same head: small grey semibold column names on the pale table-head ground. No table head SHALL be navy.

#### Scenario: Trials table
- **WHEN** a claim page lists trials
- **THEN** the column names People, Compared with, Main measure, State and Trial are grey on the pale ground, as the timetable's are
