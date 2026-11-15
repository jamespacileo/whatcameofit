# Spec Delta

## ADDED Requirements

### Requirement: Papers on the claim page
A claim page SHALL list each of the claim's papers once, under its own heading, grouped by role: the paper first reported, results papers listed by a trial, follow-up papers, and related research. Each entry SHALL show the title linked to the paper, the journal, the year, the kind of publication, and the facts the export carries for it. A claim with no paper SHALL show no such section.

#### Scenario: Claim with an origin paper and two results papers
- **WHEN** a reader opens a claim that has an origin paper and a trial with two results papers
- **THEN** the page lists three papers, the origin paper under its own group and two under the trial's results

#### Scenario: Paper with two roles
- **WHEN** a paper is both the origin paper and a results paper of a trial
- **THEN** it is listed once, in the origin paper's group, and names the trial it reports

#### Scenario: Claim with no paper
- **WHEN** a claim has no paper
- **THEN** the page shows no papers section and no placeholder for one

### Requirement: A results paper names its trial
A results paper's entry SHALL name the trial whose record lists it, linked to that trial's entry, and SHALL say whether the sponsor listed the paper or the registry linked it. A trial's entry SHALL lead to its results papers.

#### Scenario: Reader goes from a trial to its paper
- **WHEN** a reader opens a trial entry whose record lists a results paper
- **THEN** the entry links to the paper's entry, and the paper's entry links back to the trial

### Requirement: A paper says whether it studied people or animals
A paper's entry SHALL state, in the site's words, whether its index record says the study was in people, in animals or both, and SHALL state nothing when the record does not say. The wording SHALL attribute the statement to the index.

#### Scenario: Paper of a study in mice
- **WHEN** a paper's facts state a study in animals
- **THEN** its entry says the index files it as a study in animals

#### Scenario: Paper with no statement
- **WHEN** a paper's facts state neither
- **THEN** its entry says nothing about people or animals

### Requirement: The claim page counts its records in people and in animals
A claim page SHALL state, among its facts, how many of its records are of studies in people (its trials, and its papers filed as studies in people) and how many of its papers are filed as studies in animals. The statement SHALL be counts and SHALL NOT say that a treatment works in people or in animals.

#### Scenario: Claim with three trials and one mouse paper
- **WHEN** a claim has three trials and one paper filed as a study in animals
- **THEN** the page states three records in people and one in animals

#### Scenario: Claim with no such record
- **WHEN** a claim has no trial and no paper filed either way
- **THEN** the page shows no such count

### Requirement: Papers are worded without a verdict
The site SHALL word each paper fact code itself and SHALL fail the build on a code it has no wording for. It SHALL NOT say that a paper supports, confirms, proves or refutes a claim, and SHALL NOT rank papers by quality. The papers section SHALL say that a paper is not a trial record and does not set the status.

#### Scenario: Kind code without site wording
- **WHEN** the export carries a publication kind the site has no wording for
- **THEN** the site build fails and names the code

#### Scenario: Randomised trial report
- **WHEN** a paper's first kind is randomised trial
- **THEN** its entry reads that it is a report of a randomised trial, and says nothing of what the trial found

### Requirement: A retracted paper is marked where it is listed
A paper whose facts state that it is retracted SHALL be marked as retracted in its entry, in words.

#### Scenario: Retracted follow-up paper
- **WHEN** a claim page lists a follow-up paper marked retracted
- **THEN** its entry says the paper has been retracted

### Requirement: Paper facts show when their record was read
Each paper's entry SHALL show the date its index record was read, and the papers section SHALL name the index the facts come from.

#### Scenario: Record read on 3 October 2026
- **WHEN** a paper's facts were read from a record fetched on 3 October 2026
- **THEN** the paper's entry shows that date
