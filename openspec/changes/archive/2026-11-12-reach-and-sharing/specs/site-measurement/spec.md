# Spec Delta

## Purpose

What the public site may count about how it is used, and what it may never record, so that reach can be judged without watching readers.

## ADDED Requirements

### Requirement: Only counts, never people
The public site SHALL NOT set a cookie, store an identifier in a reader's browser for measurement, or load a script or image from another party that can recognise a reader across pages or sites. Measurement SHALL be limited to counts per page per day, the referring site, and counts of downloads of card images and the data file. No count SHALL be kept at a finer grain than one day, and no network address SHALL be stored with a count.

#### Scenario: Reader visits a claim page
- **WHEN** a reader opens a claim page
- **THEN** no cookie is set, nothing is stored in their browser for measurement, and no other party's script runs

#### Scenario: Operator reads the numbers
- **WHEN** the operator looks at the site's use
- **THEN** they see counts by page, day and referring site, and nothing that describes one reader

### Requirement: The site says what it counts
The page that explains the method SHALL say, in plain words, what is counted and that readers are not tracked. If nothing is counted, it SHALL say that.

#### Scenario: Reader asks what is recorded
- **WHEN** a reader opens the page that explains the method
- **THEN** they can read what the site counts and that it keeps no record of individual readers
