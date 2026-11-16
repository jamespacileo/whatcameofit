# Spec Delta

## MODIFIED Requirements

### Requirement: A report row sets the report beside the record
A news report's row SHALL lead with the outlet and the date, then the outlet's title in quotation marks leading to the claim page, then the claim's intervention and indication. In a column on the right on a wide screen, and under the claim on a phone, the row SHALL show the claim's status now in words with its place on the path, its no-signal note and its counts. That column SHALL be one control that opens the row's detail: the evidence stage when the claim was first reported, the status's gloss and meaning, the path with each place named, why the claim stands there, and the claim's latest promise, marked as a promise. Without scripting, and in print, the detail SHALL be shown. Reports of one claim dated the same day SHALL share one row that names each outlet. The site SHALL add no wording of its own about a title.

#### Scenario: A report of an animal study
- **WHEN** a claim first reported from an animal study stands at preclinical only and has a report dated 11 November 2026
- **THEN** the row shows the quoted title with its outlet and date and "Preclinical only" with the first place on the path marked, and its detail gives "Animal study" as the evidence when first reported and "No trial in people on record"

#### Scenario: Opening the detail
- **WHEN** a reader presses the status of a row, by pointer, touch or keyboard
- **THEN** the detail opens under the row, the control says it is expanded, and pressing it again closes the detail

#### Scenario: Two outlets on one day
- **WHEN** two outlets report the same claim on 6 October 2026
- **THEN** the list has one row for that claim that day, with the first title quoted and both outlets named

#### Scenario: One claim reported on two days
- **WHEN** a claim has reports dated 6 October and 13 October 2026
- **THEN** it has a row under each date

### Requirement: A registry row names the report it belongs to
A registry record's row SHALL lead with the claim's newest news report: its title quoted, leading to the claim page, with its outlet and date, and "First reported N years ago" when the claim was first reported in an earlier year than the record. It SHALL name the intervention and indication, and show what was recorded as one dated item: the registry's identifier leading to the record at its source, what was recorded, and its date. The claim's status SHALL stand in the same column, and open the same detail, as on a report row. Registry rows SHALL be listed for records dated in the ninety days up to the last check. An event with a confidence below 1 SHALL show it in the words the claim page uses.

#### Scenario: A trial registered last week
- **WHEN** a trial for a published claim was registered on 2 November 2026
- **THEN** its row quotes the claim's newest report with its outlet and date, gives the trial's identifier as a link to the registry with "Trial registered" and the date, and shows the claim's status now

#### Scenario: A record for a story from an earlier year
- **WHEN** a trial dated 12 November 2026 belongs to a claim first reported in March 2022
- **THEN** its row says "First reported 4 years ago" above the quoted title

#### Scenario: A follow-up paper scored 0.6
- **WHEN** a follow-up paper with a confidence of 0.6 is dated 26 October 2026
- **THEN** its row shows "Medium match · 60%"

#### Scenario: A record from last year
- **WHEN** a trial for a published claim was completed in 2024
- **THEN** it has no row on the home page and is listed on the claim page as before

### Requirement: A registry row says when a status changed
A row for a registry record dated on a day the claim's status changed SHALL say "Changed" in its status column, with the status before that day and the status from it, in the words the list of status changes uses. Where several of the claim's records are dated that day, only the first listed SHALL say so. Any other registry row SHALL show the claim's status now, as a report row does.

#### Scenario: An approval that changed the status
- **WHEN** a regulator's approval dated 20 October 2026 moved a claim from Phase 3 trial to Approved
- **THEN** the row's status column says "Changed", then "Was: Phase 3 trial. Now: Approved.", with the last place on the path marked

#### Scenario: A record that changed nothing
- **WHEN** a further trial is registered for a claim already at Phase 3 trial
- **THEN** the row's status column shows "On record now" with Phase 3 trial and does not say "Changed"

## ADDED Requirements

### Requirement: A status off the path is drawn as off it
Where a row draws a status's place on the path and the status is not on it (no trial record found, failed, terminated, retracted), the row SHALL draw the path with no place marked and a square after it, with the status in words beside it, and its text alternative SHALL say the status is not a place on the path. No status SHALL have a colour of its own.

#### Scenario: Trials ended early
- **WHEN** a claim stands at "Trials ended early"
- **THEN** its row shows those words, the path with no place marked and a square after it

### Requirement: Search results set the status on the right
In search results, each match SHALL show its headline, its intervention and indication and what the words were found in on the left, and its status, place on the path and first-report date in a column on the right on a wide screen.

#### Scenario: A search on a wide screen
- **WHEN** a reader searches "cancer" on a laptop
- **THEN** each match's headline starts at the left edge of the list and its status stands in a column on the right
