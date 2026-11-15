# Spec Delta

## ADDED Requirements

### Requirement: Organisations on the claim page
A claim page SHALL list each of the claim's organisations once, under its own heading, with its name, its roles in the site's words, and, when it is identified, its kind, country, website, a link to its registry record and the match score. A sponsor's role SHALL link to the trials it sponsors. A claim with no organisation SHALL show no such section.

#### Scenario: Claim with a university and a company
- **WHEN** a reader opens a claim whose report names a university and whose three trials are sponsored by one company
- **THEN** the page lists the university as named in the report and the company as sponsor of three trials, each trial linked

#### Scenario: Claim with no organisation
- **WHEN** a claim names no organisation
- **THEN** the page shows no organisations section and no placeholder for one

### Requirement: An unidentified organisation is listed plainly
An organisation that is not identified SHALL be shown by the name it was given with its roles, and SHALL say that it was not matched to a registry record. It SHALL show no kind, country or website.

#### Scenario: Start-up the registry does not know
- **WHEN** a claim names a company with no approved match
- **THEN** its entry shows the report's name and role and says no registry record was matched

### Requirement: Organisations are listed without rank or judgement
The organisations section SHALL order organisations by role and then by name. It SHALL NOT rank them, count their other claims, describe their standing, or say that an organisation endorses, backs or vouches for the claim. It SHALL say that the registry identifies an organisation and does not verify its part in the claim. The site SHALL word each kind and role code itself and SHALL fail the build on a code it has no wording for.

#### Scenario: Kind code without site wording
- **WHEN** the export carries an organisation kind the site has no wording for
- **THEN** the site build fails and names the code

#### Scenario: Well-known and unknown organisations together
- **WHEN** a claim names a large university and a small clinic in the same role
- **THEN** they are listed in name order, with the same facts shown for each

### Requirement: A report published by a named organisation says so
Where the claim page names a source article that is marked as published by one of the claim's organisations, it SHALL say, beside that report, that the report is on that organisation's website. The wording SHALL state where the report is and SHALL NOT call it promotional, biased or unreliable.

#### Scenario: University press release
- **WHEN** a claim's report is marked as published by Kyoto University
- **THEN** the page says, beside the report, that it is on Kyoto University's website

#### Scenario: Newspaper report
- **WHEN** a claim's report carries no such mark
- **THEN** the page says nothing of the kind beside it

### Requirement: No person is named in the organisations section
The organisations section SHALL NOT show the name of a researcher, an investigator, an author or any other person.

#### Scenario: Trial sponsored by a person
- **WHEN** one of a claim's trials is sponsored by a person
- **THEN** the organisations section lists nothing for that sponsor
