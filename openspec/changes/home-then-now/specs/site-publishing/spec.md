# Spec Delta

## ADDED Requirements

### Requirement: The home page draws one claim, reported and on record
Under its box the home page SHALL draw one published claim, chosen by the site's rule for its example and never by hand: the earliest report's title as a quotation with its outlet and its day, the number of whole years between that day and the day the registries were last checked, and the claim's status as the site labels it, with its place on the path and the day of its latest record. The card SHALL lead to the claim's page. The years SHALL NOT be stated for a report under a year old. The card SHALL NOT be drawn below 40rem. The home page's title and section headings SHALL be set in the heading face.

#### Scenario: A report of five years ago
- **WHEN** the example claim was first reported on 31 March 2021 and the registries were last checked on 17 November 2026
- **THEN** the card says "5 years on" between the outlet's title and the claim's status

#### Scenario: On a phone
- **WHEN** the home page is read at 375 pixels wide
- **THEN** the card is not drawn and a row of the list starts on the first screen

### Requirement: The home page's card is drawn once, in the order it is read
When the home page opens, the card's arrow SHALL be drawn from the report to the record and the marker SHALL then land on the claim's place with one ring, once. Every word of the card SHALL be readable from the first paint. With reduced motion asked for, with no script and on paper the card SHALL be shown in its finished state and nothing SHALL move.

#### Scenario: Reduced motion
- **WHEN** a reader who has asked for reduced motion opens the home page
- **THEN** the arrow and the marker are drawn whole and nothing moves

### Requirement: The day-by-day list is narrowed from one control
Where scripts run, the head of the home page's day-by-day list SHALL carry one control, on the line of the list's name, that opens, by a press and not by pointing, a panel holding every choice that narrows the list: the kind of row, the span of time, the status now and, where more than one topic is listed, the topic. Each choice SHALL be a field with its name written before it. While no field narrows the list the control SHALL say "Filter"; while one or more do, it SHALL say those picks in the fields' own words and be marked as narrowing, and the panel SHALL offer to clear them all at once. Each pick SHALL narrow the lists and be kept in the page's address exactly as before. Without scripts neither the control nor the fields SHALL be shown, and the whole list SHALL be.

#### Scenario: Nothing picked
- **WHEN** a reader opens the home page with no pick in its address
- **THEN** the control says "Filter" and the list shows the past week

#### Scenario: Two picks
- **WHEN** a reader picks news reports and phase 3 in the panel
- **THEN** the control says "News reports · Phase 3 trial", the list shows only reports of claims now in phase 3, and the address keeps both picks

#### Scenario: Clearing
- **WHEN** a reader presses "Clear filters"
- **THEN** every field returns to its first choice, the control says "Filter", and the address keeps no pick

#### Scenario: On a phone
- **WHEN** the home page is read at 375 pixels wide
- **THEN** the list's name and the control share one line, the control is 44 pixels tall, and the open panel stands inside the screen

### Requirement: A row's headline is set in the heading face and is read first
In the home page's day-by-day list, the list's name and each row's reported headline SHALL be set in the site's heading face, as SHALL a report's title in a search's answer, which stands in the list's place, and a row's headline SHALL be the largest text in the list after its name. A day's heading SHALL be drawn as a label smaller and quieter than a headline. A day's heading, a row's labels and its status SHALL stay in the text face.

#### Scenario: A report row
- **WHEN** a report row is drawn
- **THEN** its headline is in the heading face and the outlet, the claim and the status are in the text face

#### Scenario: A day's heading
- **WHEN** a day with two reports is drawn
- **THEN** the day and "2 reports" are in grey at the size of a label, and each report's headline is larger than both

### Requirement: An outlet's title keeps its marks, drawn softer and hung
Wherever the home page's day-by-day list, its card or a search's answer quotes an outlet's title on a line of its own, the title SHALL stand between quotation marks that are part of the text. The marks SHALL be drawn softer than the words, and the opening mark SHALL hang outside the column so that the title's first letter stands on the same edge as the lines above and below it.

#### Scenario: Aligned with its row
- **WHEN** a report row is drawn with the outlet above its headline and the claim below
- **THEN** the headline's first letter, the outlet and the claim start on the same edge, and the opening mark stands to the left of it

#### Scenario: Copied
- **WHEN** a reader copies a headline from the list
- **THEN** what is copied begins and ends with its quotation marks

### Requirement: The list's head is one line
The head of the home page's day-by-day list SHALL be one line on a wide screen: the list's name, a mark that opens the sentence saying what each row's right column is, the day the registries were last checked, and the control that narrows the list. The sentence SHALL be in the page as built and reachable without scripts. On a phone the day checked SHALL take the line under the others.

#### Scenario: What the column says
- **WHEN** a reader presses or points at the mark beside "Latest"
- **THEN** a panel says "With each report and record: where its claim stands on record now. Press it for why."

### Requirement: A registry row leads with what was recorded
In the home page's day-by-day list, a registry record's row SHALL lead with the record: a mark of what happened, its kind in words and the record's identifier leading to the record at its source, then what was recorded, in the record's own words, as the row's title leading to the claim page, then the claim. Where the registry gives a trial's phase, the title SHALL name it. The claim's newest news report SHALL follow these, set smaller than the row's title and joined to the row as what the record belongs to: named "Newest report", with its outlet and date, how long ago the claim was first reported when that is a year or more, and its title quoted. A registry row SHALL NOT set a news report's title as its own title.

#### Scenario: A phase 3 trial registered last week
- **WHEN** a phase 3 trial for a published claim was registered on 2 November 2026
- **THEN** the row's title reads "Phase 3 trial registered", and the claim's newest report is quoted under it, smaller, after "Newest report"

#### Scenario: A trial with no phase given
- **WHEN** the registry gives no phase for a trial whose results were posted
- **THEN** the row's title reads "Trial results posted"

#### Scenario: A report and a record of one claim on one day
- **WHEN** a claim was reported and a trial for it was registered on the same day
- **THEN** the report's row has the outlet's title as its title, and the record's row has what was recorded as its title

#### Scenario: Read aloud
- **WHEN** a screen reader lists the page's links
- **THEN** a registry row's title is read with its treatment, as what was recorded, a colon and the treatment's name

### Requirement: A row's status stands in a named panel
In the home page's day-by-day list, a report's and a registry record's row SHALL show the claim's status in a panel at the row's right: the status, its place on the path, a no-signal note where there is one, and the counts. The panel SHALL be named "Status now", so that it is not read as what the report or the record beside it says: once for each day, at the right of the day's heading, where the panels stand in a column; on the panel's own first line where the panel stands under the claim. The panel SHALL be no taller than what it holds while its detail is closed. A row for a record dated on a day the claim's status changed SHALL say "Changed" and the status before in place of "Status now". The panel SHALL be the control that opens the row's detail, and while the detail is open the two SHALL be drawn as one shape. The phase in a registry row's title is the trial's; the status in the panel is the claim's.

#### Scenario: An early trial of a claim that is further on
- **WHEN** a phase 2 trial is registered for a claim that stands at phase 3
- **THEN** the row's title reads "Phase 2 trial registered" and its panel, under "Status now", reads "Phase 3 trial"

#### Scenario: A day of three rows on a wide screen
- **WHEN** a day lists two reports and a registry record
- **THEN** the day's heading says "Status now" once, over the three panels, and no panel says it

#### Scenario: On a phone
- **WHEN** the list is read at 375 pixels wide
- **THEN** each panel says "Status now" on its first line and no heading does

#### Scenario: A record that changed the status
- **WHEN** a record dated today moved a claim from phase 2 to phase 3
- **THEN** the panel says "Changed" and the status before, and does not say "Status now"

#### Scenario: Opened
- **WHEN** a reader presses a row's panel
- **THEN** the detail opens under the row with nothing between it and the panel, on the same ground

### Requirement: A record's mark is coloured by which way the record moved
A registry row SHALL carry one mark for what its record did, hidden from a screen reader. The mark's colour SHALL say which way the record moved and nothing else: one colour where something began or a regulator approved (a trial registered, a trial started, a regulatory approval), another where something was halted, taken back or refused (a trial suspended, terminated or withdrawn, a regulatory refusal, a retraction), and the site's blue for every other record. A completed trial and posted results SHALL keep the blue. No mark SHALL be a tick or a cross, and colour SHALL never be the only thing that tells two marks apart: each has its own drawing and the row says what happened in words. No status and no place on the path SHALL take these colours.

#### Scenario: A trial registered
- **WHEN** a trial is recorded as registered
- **THEN** its mark is a plus in the colour of a record that moved forward

#### Scenario: A terminated trial
- **WHEN** a trial is recorded as terminated
- **THEN** its mark is a square in the colour of a record that stopped, and the row says "terminated" in words

#### Scenario: A completed trial
- **WHEN** a trial is recorded as completed, whatever its results
- **THEN** its mark keeps the blue

#### Scenario: Results posted
- **WHEN** a trial's results are posted
- **THEN** its mark keeps the blue

### Requirement: A row does not repeat its day
Under a heading that names one day, a report's or a registry record's row of the day-by-day list SHALL NOT draw its date again. A promised date's row SHALL keep the date of the report that made the promise, which is not the day it is listed under. Under a heading that names a week or a year, each row SHALL draw its date. Every row's date SHALL remain in the page as built.

#### Scenario: Under a day
- **WHEN** two reports are listed under "Sunday 15 November"
- **THEN** neither row draws "15 Nov 2026"

#### Scenario: Under a week
- **WHEN** a report dated 21 October is listed under "Week of 19 October"
- **THEN** its row draws "21 Oct 2026"

### Requirement: A record matched to several claims is drawn once
Where one registry record is listed in a day for more than one claim, the day-by-day list SHALL draw the record in full for the first of those claims and SHALL list each further claim straight after it, under one label that says they are the same record for other claims, as one line that names the treatment, leading to its claim page, and what it is for, with that claim's own status beside it. When a reader's choice leaves the first of those rows out, the first one left SHALL be drawn in full. The day's counts SHALL still count every row.

#### Scenario: One trial, five claims
- **WHEN** a trial registered on 12 November is matched to five published claims
- **THEN** the day shows the record once, with its identifier, then "The same record, for other claims" once, and four lines under it, each a treatment, what it is for and its status

#### Scenario: The leading claim is filtered out
- **WHEN** a reader narrows the list to a topic the first of those five claims is not filed under
- **THEN** the first claim left is drawn as the record, in full, and the rest follow it

### Requirement: The list reads as a feed on a phone
At 375 pixels wide, a row's status panel SHALL be one line of at least 44 pixels: the status, its place on the path and the control's mark; a change of status and a no-signal note SHALL keep a line of their own. The counts SHALL be said in the opened detail. The panel SHALL be named "Status now" to a screen reader. A day's heading SHALL stay in view while its rows are read. A link in an opened detail SHALL be at least 44 pixels to press. The first row and its status panel SHALL both be on the first screen of a phone 812 pixels tall.

#### Scenario: First screen
- **WHEN** the home page opens on a phone 375 by 812
- **THEN** the title, the box with its button beside it, three things to try, the list's head, and the first row with its status panel are all in view

#### Scenario: A long day
- **WHEN** a reader scrolls through a day of eleven rows
- **THEN** that day's heading stays at the top of the screen until the next day's replaces it

### Requirement: A long day is cut on a narrow list
Where the day-by-day list is narrow and scripts run, a day SHALL show its rows up to its fifth leading row, with the rows that follow that one, and SHALL offer the rest behind one control that says how many rows it brings back. A row that follows its record SHALL NOT be parted from it. A day SHALL be cut only when that leaves out at least two leading rows. Once a reader has asked for a day's rest, that day SHALL stay whole. A wide list, paper, and a page without scripts SHALL show every row, and a day's counts SHALL count every row.

#### Scenario: Seven leading rows on a phone
- **WHEN** a day lists three reports and four records, one of them matched to five claims
- **THEN** the day shows the three reports, the record with its four following lines and one more record, and "Show 2 more"

#### Scenario: Asked for
- **WHEN** the reader presses "Show 2 more"
- **THEN** every row of that day is shown, the control is gone, and narrowing the list afterwards does not cut that day again

#### Scenario: Six leading rows
- **WHEN** a day lists six leading rows
- **THEN** all six are shown and there is no control

