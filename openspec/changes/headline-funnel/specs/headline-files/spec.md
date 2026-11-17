# Spec Delta

## Purpose

Says how headlines that a third party publishes in bulk become leads: what a headline file is, what is read from it and what is never read, the rule that keeps a headline, what a kept headline becomes, and what a load reports.

## ADDED Requirements

### Requirement: What is read from a headline file
A headline file SHALL be a file a third party publishes that lists news articles one to a row. From each row the pipeline SHALL read only the article's address, its outlet's name and domain, its title, its publication date and its language. It SHALL NOT read, hold, log or write a description, an excerpt, an author, an image or the article's text, in a file, a cache, a log or a test fixture.

#### Scenario: A row with a description and an author
- **WHEN** a row of a headline file carries a description and an author beside its address and title
- **THEN** the address, outlet, title, date and language are read, and the description and the author reach no file, log or table

#### Scenario: A file that also holds article text
- **WHEN** a headline file's rows hold the article's text in a field of their own
- **THEN** the fields named above are asked for by name and the text field is never read from the file

### Requirement: A headline file comes from its publisher, never from a news outlet
A headline file SHALL be fetched from the host its publisher names for it, by a script the operator runs, and no request SHALL be sent to a news outlet to obtain a headline. The file's source SHALL have a dated entry in `docs/sources.md`, with its terms, its limits and the fields read, before the script that fetches it is written.

#### Scenario: A source with no entry
- **WHEN** a load is asked for a file whose source has no dated entry in `docs/sources.md`
- **THEN** the load refuses and names the missing entry

#### Scenario: A day of files is fetched
- **WHEN** the operator fetches one day of a source's files
- **THEN** requests go to the publisher's data host only, and what is written to disk holds no description, author or text

### Requirement: Loading a file sends no request and can be run again
`thenwhat backfill load-headlines` SHALL read files from disk and send no request. Loading a file a second time SHALL add nothing. The load SHALL record which source and which span of time it has loaded.

#### Scenario: The same file twice
- **WHEN** a file is loaded and then loaded again
- **THEN** the second load stores no lead and reports that every row was already seen

### Requirement: Only headlines in a configured language are considered
A headline whose language, as the file gives it, is not one of the configured languages SHALL be counted and SHALL NOT be considered or stored.

#### Scenario: A headline in another language
- **WHEN** the configured language is English and a row's language is German
- **THEN** the row is counted as another language and nothing is stored for it

### Requirement: Candidate terms are built by rule from stored trials
The terms a headline is tried against SHALL be built by fixed rules from every stored trial's registry record, with no model and no request: the registry number; the development codes among its intervention names and other names; an acronym that is fit, as `trial-coverage` defines fit; and each intervention name and other name that is not made only of ordinary words. A word SHALL count as ordinary when the project's word list holds it or holds the word it is an inflected form of.

#### Scenario: A substance with an invented name
- **WHEN** a stored trial's intervention is named "asundexian"
- **THEN** "asundexian" is a candidate term

#### Scenario: A name that is an ordinary word
- **WHEN** a stored trial's intervention is named "Home"
- **THEN** it is not a candidate term

#### Scenario: A plural of an ordinary word
- **WHEN** a stored trial lists the other name "drugs"
- **THEN** it is not a candidate term

### Requirement: A term most headlines could hold is not a candidate
A term that more than the configured share of loaded headlines hold SHALL NOT be a candidate term, whatever kind of term it is. The share SHALL be a setting with no default, chosen by the operator from the load's report. While it is empty, a load SHALL count what each term would keep and SHALL keep nothing.

#### Scenario: A person's surname among other names
- **WHEN** a stored trial lists the other name "Johnson" and more than the configured share of loaded headlines hold it
- **THEN** "Johnson" is not a candidate term and keeps no headline

#### Scenario: The share is not set
- **WHEN** a load is run and the share is not configured
- **THEN** the report lists the terms and how many headlines each would keep, and no lead is stored

### Requirement: A headline is kept when it holds a candidate term
A headline SHALL be kept when its title or its address holds a candidate term as whole words, whatever the letter case, and with or without a code's hyphen. A word of a trial's condition SHALL NOT be required. A kept headline SHALL be stored as a link lead, once per address as the site compares addresses, with its address, outlet, title and date, the source it came from, and the terms it was kept on as its reason.

#### Scenario: A headline that names a treatment and no condition
- **WHEN** a headline reads that a regulator has approved a named treatment and holds no word of any trial's condition
- **THEN** it is kept on the treatment's name

#### Scenario: A code written without its hyphen
- **WHEN** a headline holds "tara002" and a stored trial lists "TARA-002"
- **THEN** the headline is kept on that code

#### Scenario: The same article in two files
- **WHEN** two loaded files list one address
- **THEN** one link lead holds it

### Requirement: A headline that holds no candidate term is not stored
A headline that holds no candidate term SHALL be counted and dropped, and its address and title SHALL NOT be stored.

#### Scenario: A day of headlines
- **WHEN** a day's file holds 480,000 rows and 3,000 hold a candidate term
- **THEN** 3,000 link leads at most are stored and the rest are counted only

### Requirement: Keeping a headline links it to no trial
Keeping a headline SHALL decide only that it is stored. It SHALL NOT link the lead to a trial, mark a link strong, or change the order in which leads are read. A lead's links to stored trials SHALL be made by screening, under the rules of `trial-report-links`, as for any other lead.

#### Scenario: A kept headline is screened
- **WHEN** a headline kept on a substance's name is screened
- **THEN** its links, their reasons and their strengths are those screening gives any lead with that title

### Requirement: An address already held gains a reason and no second record
A kept headline whose address is already a link lead SHALL add its source and terms to that lead's reasons and SHALL create no second lead. A kept headline whose address is already a source article SHALL be counted as tracked and SHALL create no lead.

#### Scenario: An article that was also shared
- **WHEN** a kept headline's address is already a link lead that people shared
- **THEN** that lead records the headline file as a further reason and nothing else about it changes

### Requirement: A kept headline goes through the existing path unchanged
A link lead made from a headline SHALL go through every step any link lead goes through, by the same rules: screening, triage, the page reader, the same-claim decision, drafting or joining, `thenwhat prepare --pending`, and the audit hold until `thenwhat audit clear` releases it. It SHALL be read only when triage passed it or held it. The headline and the date in the file SHALL be used for triage and for ordering only: the read takes both from the page.

#### Scenario: A kept headline that triage rejects
- **WHEN** a kept headline names a tracked treatment in a story about its maker's finances and triage rejects it
- **THEN** it is not read

#### Scenario: A kept headline that triage passes
- **WHEN** a kept headline is passed by triage and read
- **THEN** a claim is drafted or joined, prepared, and held awaiting audit, and no export publishes it before it is cleared

### Requirement: A load reports what it kept and on which terms
A load SHALL report: rows read; rows by language; rows already seen; headlines kept, by outlet kind; headlines already tracked; and the terms that kept the most headlines, with their counts.

#### Scenario: One term keeps a large share
- **WHEN** one term kept 800 of 3,000 headlines
- **THEN** the report lists it first with its count, so the operator can see a term that is not telling
