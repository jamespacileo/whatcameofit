# Spec Delta

## ADDED Requirements

### Requirement: Reported statements on the claim page
A claim page SHALL list the claim's approved reported statements under their own heading, placed after the summary and before the records. Each statement SHALL show its text, its kind, its article by outlet and date with a link, and how sure the pipeline is that the article says it, as a word and a percentage. A claim with no approved statement SHALL show no such section.

#### Scenario: Claim with three statements from one report
- **WHEN** a reader opens a claim with three approved statements from one article
- **THEN** the page lists the three under the report's outlet and date, each with its confidence

#### Scenario: Claim with no statement
- **WHEN** a claim has no approved statement
- **THEN** the page shows no statements section and no placeholder for one

### Requirement: A statement is worded as a report's statement
Each statement SHALL be shown as something its report said, with the site's wording for how firmly the report put it and for who the report had saying it. The section SHALL say that a report's statement is not a record and that the records follow. The site SHALL NOT show a statement as a finding, and SHALL NOT say whether a statement held, was confirmed or was contradicted.

#### Scenario: Possibility voiced by a researcher
- **WHEN** a statement was put as a possibility and said by a researcher
- **THEN** the page reads that the report had a researcher saying it could be so, and names no one

#### Scenario: Statement beside a trial result
- **WHEN** a claim has a statement of an effect and a trial with posted results
- **THEN** the page shows both, in their own sections, and no word compares them

### Requirement: A statement shows what the report said it rested on
Each statement SHALL show its basis in the site's words: a study in people, a study in animals, laboratory work, or that the report did not say. The wording SHALL attribute the basis to the report.

#### Scenario: Effect reported from a mouse study
- **WHEN** a statement's basis is a study in animals
- **THEN** the page says the report gave a study in animals as its basis

### Requirement: Statement codes are worded by the site
The site SHALL word each kind, firmness, speaker role and basis code itself and SHALL fail the build on a code it has no wording for. The wording SHALL pass the site's check against verdict wording.

#### Scenario: Kind code without site wording
- **WHEN** the export carries a statement kind the site has no wording for
- **THEN** the site build fails and names the code

### Requirement: The method page explains reported statements
The method page SHALL explain that statements are read from a report by a language model, put in the site's own words, checked against the report and shown with a confidence; that they are what a report said and not what is on record; and that they never change a status.

#### Scenario: Reader doubts a statement
- **WHEN** a reader follows the method link from the statements section
- **THEN** they can read how a statement is found, what its confidence means and how to report an error
