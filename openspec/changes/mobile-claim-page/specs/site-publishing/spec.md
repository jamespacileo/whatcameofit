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

### Requirement: Ways back sit beside the answer
A claim page's status panel SHALL link to the page's reminders where they can be offered. The home page SHALL link the feed of status changes in the open, and each topic page SHALL link a feed of that topic's status changes and offer to share the page. A claim page SHALL end with a link to look up another headline, and the home page SHALL end with the link to suggest a headline when a suggestion address is configured. Where a claim page says it has not been checked by a person is set by "Unchecked claims are marked".

#### Scenario: Following from a claim page
- **WHEN** a reader opens a claim page
- **THEN** the status panel holds a link to "Check again later", and the page's last section leads to the lookup

#### Scenario: A topic's status changes as a feed
- **WHEN** a topic has a claim whose status has changed twice
- **THEN** the topic page links a feed holding those changes, newest first

### Requirement: The digest counts the trials' states under a status that names a phase
When a claim's status is not Trial registered and it has trials on record, the digest panel SHALL say, after what the status means, how many trials are on record and how many are under way, finished and stopped early, leaving out a state no trial has. Where no trial is in one of those three states, it SHALL count every state instead, so the count never stands bare. Where any trial on record is a Phase 4 trial, the panel that names the path's places SHALL say how many and that the path counts phases up to Phase 3; the digest SHALL NOT. The sentence SHALL be a count of records and SHALL NOT say what the counts mean.

#### Scenario: Most trials stopped early
- **WHEN** a reader opens a claim whose status is Phase 3 trial and which has 9 trials on record, 3 finished and 6 stopped early
- **THEN** the digest says "9 trials on record: 3 finished, 6 stopped early."

#### Scenario: Forty-nine trials in six states
- **WHEN** a claim has 49 trials on record: 5 under way, 1 not started, 32 finished, 3 stopped early and 8 in other states
- **THEN** the digest says "49 trials on record: 5 under way, 32 finished, 3 stopped early."

#### Scenario: Phase 4 trials on record
- **WHEN** a claim whose status is Phase 3 trial has 47 trials on record, 24 of them Phase 4
- **THEN** the panel that opens from the status says, under the path's places, that 24 trials on record are Phase 4 trials and that the path counts phases up to Phase 3

## ADDED Requirements

### Requirement: A link in a row that opens can be pressed
In a fact row that opens, a link under the row's value SHALL be pressed for itself and SHALL NOT be covered by the row's own press. On a phone it, a moment of the record, the line that opens the rest of a list and a marked word of the record in brief SHALL each be at least as tall as a fingertip, or lie in running text.

#### Scenario: "See the posted results"
- **WHEN** a reader presses "See the posted results" under an answer of the record in brief
- **THEN** the page goes to the trials on record and the row does not open

### Requirement: A heading's note says only what is true of what is in sight
The note beside the timetable's heading SHALL give the counts of promises and records and SHALL NOT name an order: the moments under it run oldest first and the full record newest first.

#### Scenario: A claim with 163 records and one promise
- **WHEN** a reader reads the timetable's heading
- **THEN** the note reads "1 promise · 163 records"


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
