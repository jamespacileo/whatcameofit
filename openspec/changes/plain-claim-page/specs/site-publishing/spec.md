# Spec Delta

## ADDED Requirements

### Requirement: A claim page is titled by its intervention
The main heading of a claim page SHALL be the claim's intervention name. The claim's full headline SHALL appear directly under the heading.

#### Scenario: Page of a named intervention
- **WHEN** a reader opens the page of a claim whose intervention is "Trontinemab"
- **THEN** the page's main heading reads "Trontinemab" and the claim's full headline is shown under it

#### Scenario: Search result for a claim
- **WHEN** a reader searches the site by intervention name
- **THEN** the claim is found and its result is titled as it was before this requirement

### Requirement: Every claim page carries a provenance line
Every claim page SHALL show, in one line near its heading, that the page was put together from the public records it links to, whether a person has checked it, and the date the registries were last checked. The line SHALL have the same place and visual weight whether or not a person has checked the page.

#### Scenario: Claim no person has checked
- **WHEN** a reader opens a claim that is marked as not checked by a person
- **THEN** the provenance line says it has not yet been checked by a person and gives the date the registries were last checked

#### Scenario: Claim a person has checked
- **WHEN** a reader opens a claim that is marked as checked by a person
- **THEN** the provenance line says a person has checked it and gives the date the registries were last checked

#### Scenario: Export with no check date
- **WHEN** the export carries no date for the last registry check
- **THEN** the provenance line omits the date and still states the other two facts

### Requirement: A claim page answers three fixed questions by rule
A claim page SHALL answer, in plain words, whether the claim has been tested in people, whether it is approved, and what the next record on the path would be. Each answer SHALL be fixed wording chosen by the claim's status code alone. An answer SHALL NOT predict an outcome or a date, SHALL NOT present a trial or an approval as a treatment option, and SHALL NOT use verdict wording.

#### Scenario: Claim with no trial on record
- **WHEN** a reader opens a claim whose status is Preclinical only
- **THEN** the answers say no trial in people is on record, no approval is on record, and the next record on the path would be a registered trial in people

#### Scenario: Claim in a mid-stage trial
- **WHEN** a reader opens a claim whose status is Phase 2 trial
- **THEN** the answers say it has been tested in people, no approval is on record, and the next record on the path would be a large late-stage trial starting

#### Scenario: Approved claim
- **WHEN** a reader opens a claim whose status is Approved
- **THEN** the answers say a regulator has recorded an approval and that an approval is not advice to take a treatment

#### Scenario: Next step is not a prediction
- **WHEN** a claim page names the next record on the path
- **THEN** it also says the site does not predict whether or when that will happen

#### Scenario: Claim whose trials ended early
- **WHEN** a reader opens a claim whose status is Trials ended early
- **THEN** the answers say its trials were stopped early or withdrawn and use no verdict wording

#### Scenario: Status code without answers
- **WHEN** the site is built and a status code lacks an answer to any of the three questions
- **THEN** the build fails and names the code

#### Scenario: Answer with verdict wording
- **WHEN** the site is built and an answer contains the word "abandoned"
- **THEN** the build fails and quotes the answer
