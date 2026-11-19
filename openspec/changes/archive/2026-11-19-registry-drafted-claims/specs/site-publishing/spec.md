# Spec Delta

## ADDED Requirements

### Requirement: The export says whether a report is linked
Each exported claim SHALL say whether a source article is linked to it and what it was drafted from, as codes. The export SHALL carry no headline or summary for a claim with no source article.

#### Scenario: A registry-drafted claim in the export
- **WHEN** a claim drafted from registry records with no article is exported
- **THEN** it says no report is linked and that it was drafted from registry records, and it has no headline or summary text

### Requirement: A claim with no report says so in one fixed line
The page of a claim with no source article SHALL say, in one fixed line worded by the site, that no news report is linked to the claim yet. The line SHALL NOT appear on a claim with a source article. The page SHALL show no date first reported, no promise and no reported statement for such a claim.

#### Scenario: A reader opens a claim with no report
- **WHEN** a reader opens the page of a registry-drafted claim with no source article
- **THEN** the page shows the fixed line, the status and the trials that produced it, and no date first reported

#### Scenario: A report is linked later
- **WHEN** the claim gains a source article and the site is built again
- **THEN** the fixed line is gone and the article is listed

### Requirement: A claim with no report is worded by the site from its treatment and condition
The headline and summary of a claim with no source article SHALL be made by the site from fixed phrases, the intervention's name and the indication. The phrases SHALL say that trials are registered for the treatment and the condition and nothing more. The build SHALL fail on a phrase that says how a trial turned out, that a treatment works or is promising, or that a reader can get, ask for or join anything.

#### Scenario: The headline of a claim with no report
- **WHEN** a claim with no report tests a named treatment for a named condition
- **THEN** its headline is the treatment and the condition in the fixed phrase, with no other word

#### Scenario: A phrase of advice
- **WHEN** a fixed phrase for claims with no report holds a word that offers the treatment to a reader
- **THEN** the site build fails and names the phrase

### Requirement: Lists of claims can be narrowed to reported claims
Wherever the site lists claims, a reader SHALL be able to narrow the list to claims a report is linked to. The choice SHALL be kept in the page's address so a narrowed list can be shared, and SHALL work with the narrowing by status and by topic that exists.

#### Scenario: A reader narrows the Claims list
- **WHEN** a reader chooses to see only reported claims on the Claims list
- **THEN** the list holds only claims with a source article and its count says so

#### Scenario: A narrowed list is shared
- **WHEN** a reader opens an address that narrows a topic's list to reported claims
- **THEN** the list opens narrowed

### Requirement: Counts say how many claims a report is linked to
Where the site states how many claims it tracks, it SHALL state how many of them a report is linked to. A claim with no report SHALL NOT be counted as a report, an approval or a breakthrough.

#### Scenario: The home page's count
- **WHEN** the export holds 9,000 claims of which 2,000 have a source article
- **THEN** the home page states both figures

### Requirement: Lists made of reports hold no claim without one
A list or row whose subject is a report, a promise or a reported statement SHALL NOT hold a claim that has no source article.

#### Scenario: The day-by-day list's report rows
- **WHEN** a registry-drafted claim with no article has a trial event dated today
- **THEN** it can appear as a registry row and never as a report row
