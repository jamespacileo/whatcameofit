# Spec Delta

## MODIFIED Requirements

### Requirement: Unchecked claims are marked
A claim page, and the extension's view of a claim, SHALL say when no person has checked the claim, and SHALL say nothing of the kind for a claim a person checked. A claim page SHALL say it once, in a line under the title and above the status card, with the words leading to the guide entry on what "checked by a person" means; the same line SHALL give the day the registries were last checked. A site built from an older export that calls itself a preview SHALL show on every page that it is a preview and not for publication, and SHALL ask search engines not to index any page.

#### Scenario: Unchecked claim page
- **WHEN** a reader opens the page of a claim no person checked
- **THEN** the line under the title says the page was put together by software and is not yet checked by a person, and gives the day the registries were last checked

#### Scenario: Said once
- **WHEN** a reader reads the page of a claim no person checked from top to bottom
- **THEN** the page says it is not yet checked by a person in one place only

#### Scenario: Checked claim page
- **WHEN** a reader opens the page of a claim a person checked
- **THEN** the line under the title gives the day the registries were last checked and says nothing about who checked it

#### Scenario: Checked claim in the extension
- **WHEN** the extension shows a claim a person checked
- **THEN** it carries no unchecked note

#### Scenario: Older preview export
- **WHEN** the site is built from an export that calls itself a preview
- **THEN** every page carries the preview note and a noindex tag

## ADDED Requirements

### Requirement: A Phase 3 status with no approval says approvals are not read
When a claim's status is Phase 3 trial and no approval is among its records, the status card SHALL say, after what the status means, that no approval is listed and that the site does not read regulators' records, so one can exist and not be listed. Whether the sentence is shown SHALL be decided by the status code and the claim's records alone, never by the wording of a news report. The sentence SHALL hold no verdict and no link.

#### Scenario: Reported as approved, status Phase 3 trial
- **WHEN** a claim whose news reports say it was approved has a Phase 3 trial status and no approval record
- **THEN** the status card says no approval is listed here and that the site does not read regulators' records

#### Scenario: An earlier place on the path
- **WHEN** a claim's status is Phase 2 trial
- **THEN** the status card says nothing about approvals

### Requirement: The status panel names the latest records and can be closed
The panel that opens from the status SHALL name at most the three latest records the status rests on, each leading to its record on the page. When the status rests on more, the panel SHALL say how many and lead to the timetable, which marks every one. A panel of the status card SHALL end with a control that closes it, in reach without scrolling the panel.

#### Scenario: A status that rests on 44 records
- **WHEN** a reader opens the panel of a status that rests on 44 records
- **THEN** it names the three latest, says they are the 3 latest of 44, and leads to the timetable

#### Scenario: A status that rests on two records
- **WHEN** a reader opens the panel of a status that rests on two records
- **THEN** it names both and says nothing of a count

#### Scenario: Closing the panel on a phone
- **WHEN** a reader on a phone has opened the panel
- **THEN** a "Close" control is in sight at its foot and closes it
