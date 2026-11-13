# Spec Delta

## Purpose

Lets the operator learn which untracked articles readers ask about, as counts per article and day, so that new claims are chosen by demand. Nothing about any reader is kept.

## ADDED Requirements

### Requirement: A missed lookup is counted by article and day
When the lookup service reads a public article by its address and no published claim cites it, the service SHALL add one to a count held for that article's cleaned address and that day. The count SHALL hold the address, the day and the number, and nothing else.

#### Scenario: Untracked article looked up twice in a day
- **WHEN** two readers each look up the same untracked article on one day
- **THEN** one count for that address and day reads two, and nothing records who asked or when in the day

#### Scenario: Tracked article
- **WHEN** a reader looks up an article that a published claim cites
- **THEN** no count is added

### Requirement: Only a public, cleaned address is counted
The service SHALL count an address only when it fetched the article itself from the public web under the article's robots rules, and SHALL count it in its cleaned form: no tracking parameters, no fragment. An address the cleaning rules refuse SHALL NOT be counted. A lookup of pasted text, of a screenshot or of a post SHALL NOT be counted.

#### Scenario: Address with a private-looking parameter
- **WHEN** a looked-up address carries a query parameter the cleaning rules do not allow
- **THEN** the lookup is answered and no count is added

#### Scenario: Pasted text
- **WHEN** a reader pastes an article's text with no address
- **THEN** no count is added

#### Scenario: Article that could not be read
- **WHEN** the article's site refuses the service or its robots rules disallow it
- **THEN** no count is added

### Requirement: Counts carry nothing about the reader
A count SHALL NOT be stored with a network address, a browser's description, a referring page, a time finer than the day, or any text of the article. A failure to count SHALL NOT change or delay the reader's answer.

#### Scenario: Counting fails
- **WHEN** the count cannot be written
- **THEN** the reader receives the same answer as if it had been

### Requirement: Counts are kept for ninety days
A count SHALL be deleted once its day is more than ninety days past.

#### Scenario: Old count
- **WHEN** a count's day is ninety-one days ago
- **THEN** the next daily clean-up deletes it

### Requirement: The operator reads the counts as an intake list
The operator SHALL be able to list missed addresses with their total count and the number of days on which each was asked for, most asked first, as a file. The list SHALL be available only to the operator and SHALL NOT be published on the site, in the open data or in any feed. An address SHALL become a claim only through the existing extraction and review steps.

#### Scenario: Operator asks for the list
- **WHEN** the operator runs the intake command
- **THEN** a file lists each missed address with its total and its number of days, most asked first

#### Scenario: Reader looks for the list
- **WHEN** a reader requests any public address of the site
- **THEN** no response contains a missed address or its count

### Requirement: The site says that missed lookups are counted
The method page and the privacy page SHALL say that an untracked article's address is counted by day when it is looked up, that nothing about the reader is kept with it, and how long the count is kept.

#### Scenario: Reader asks what a lookup records
- **WHEN** a reader opens the privacy page
- **THEN** they can read that a looked-up article's address is counted by day, without anything about them, for ninety days
