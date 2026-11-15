# Spec Delta

## ADDED Requirements

### Requirement: Claim and topic pages open with a band
A claim page and a topic page SHALL open, directly under the masthead, with a full-width band in the site's navy. On a claim page the band SHALL hold the breadcrumb, the title, the reports followed and the status panel. On a topic page it SHALL hold the breadcrumb, the title, the summary sentence and the number of claims at each status. On a screen wide enough for two columns the status panel SHALL start level with the title.

#### Scenario: Claim page on a wide screen
- **WHEN** a reader opens a claim page at 1280 pixels wide
- **THEN** the status label is in the band, beside the title, and starts within the first 200 pixels of the page

#### Scenario: Topic with one claim at each of two statuses
- **WHEN** a reader opens a topic whose two claims stand at Preclinical only and Phase 3 trial
- **THEN** the band shows the topic's name and a count of one at each of those statuses, each named in words

### Requirement: The band stays short on a phone
Below the site's phone breakpoint the band of a claim page SHALL hold only the breadcrumb, the title, the link to the method and the status panel. The reports followed SHALL open the content below the band, and the follow and share controls SHALL close the band, under the status panel. When a claim follows more than one report, the first SHALL be shown there and the rest SHALL be reached by one link to the timetable.

#### Scenario: Claim page on a phone
- **WHEN** a claim page is opened at 375 by 812 pixels
- **THEN** the status label starts within the first screen and the content below the band starts within 1,000 pixels of the top

#### Scenario: Claim that follows three reports
- **WHEN** a claim with three source articles is opened at 375 pixels wide
- **THEN** one report is shown under the band with a link reading that two more are on the timetable

### Requirement: A claim page lists its sections
A claim page SHALL list its sections by name, each with the count it holds where it has one, and SHALL mark the section in view. On a wide screen the list SHALL stay in view beside the content. On a narrow screen it SHALL be one row that stays at the top, SHALL keep the marked section in view, and SHALL show at either end that more lies beyond it. A section the page does not have SHALL NOT be listed.

#### Scenario: Reader scrolls to the trials
- **WHEN** a reader scrolls a claim page until the trials section is at the top
- **THEN** the list marks "Trials on record" and no other section

#### Scenario: Claim with no papers
- **WHEN** a claim has no matched paper
- **THEN** the list has no entry for papers

#### Scenario: Narrow screen, section far along the row
- **WHEN** a reader on a phone scrolls to the last section
- **THEN** the row has moved so that the last section's name is in view and marked

### Requirement: Sections of a claim page fold
Each section of a claim page SHALL fold and unfold from its heading. The heading SHALL remain a heading, and the control SHALL say whether the section is open. Papers, organisations and background SHALL start folded. Below the phone breakpoint only the record in brief and the timetable SHALL start open. A link to a folded section, or to something inside one, SHALL open it. With scripting off every section SHALL be open.

#### Scenario: Wide screen, first view
- **WHEN** a claim page with papers and organisations is opened at 1280 pixels wide
- **THEN** the papers and organisations sections are folded, with their counts on the heading line, and the timetable and trials are open

#### Scenario: Phone, first view
- **WHEN** the same page is opened at 375 pixels wide
- **THEN** only the record in brief and the timetable are open

#### Scenario: Link into a folded section
- **WHEN** a reader presses a trial identifier in the timetable while the trials section is folded
- **THEN** the trials section opens and the reader arrives at it

#### Scenario: Scripting off
- **WHEN** a claim page is opened with scripting off
- **THEN** every section is open

### Requirement: The timetable reads newest first
The claim page's timetable SHALL list its years newest first and, within a year, its entries newest first. A year for which a promise was made SHALL show what was promised for it beside what was recorded in it, including a year still to come. A run of years with neither a promise nor a record SHALL be shown as one gap that names the years. Each entry SHALL state its kind in words as well as by its mark.

#### Scenario: Records from 2021 to 2026 with none in 2024 and 2025
- **WHEN** a claim has records in 2021, 2022, 2023 and 2026
- **THEN** the timetable starts with 2026, ends with 2021, and shows one gap reading "2024 to 2025" with no record

#### Scenario: Promise for a year still to come
- **WHEN** a claim reported in 2026 carries a promise for 2029 and nothing is recorded for 2029
- **THEN** the timetable starts with 2029, showing the promise beside "Not yet reached"

### Requirement: The timetable can be narrowed to one kind of entry
With scripting on, a timetable holding more than one kind of entry SHALL let a reader show promises, registry records or news reports alone, and all of them again. A year left with no entry SHALL be hidden, and a year's stated count SHALL be the entries left. The choice SHALL be announced to a screen reader. With scripting off, and in print, every entry SHALL be shown.

#### Scenario: Registry records only
- **WHEN** a reader picks registry records on a claim whose 2026 holds three news reports and one registry record
- **THEN** 2026 shows one entry and states one record, and promises with and without a date are hidden

#### Scenario: One kind only
- **WHEN** a claim's timetable holds only registry records
- **THEN** no control to narrow it is shown

### Requirement: Promises and records are counted apart
Wherever a claim page states how many entries its timetable holds, it SHALL give the number of promises and the number of records as two numbers and SHALL NOT add them into one. Every place that states them SHALL give the same two numbers. A promise with no date SHALL count as a promise.

#### Scenario: Four promises and seventeen records
- **WHEN** a claim has two dated promises, two promises with no date and seventeen records
- **THEN** the section list, the section heading and the controls that narrow the timetable all give 4 promises and 17 records, and none gives 21

### Requirement: Trials read across as a table
The trials section SHALL show its trials as rows of one table with columns for the trial, what it was compared with, its design, its state and its results. A row SHALL open to show the rest of what the export carries for that trial, its match and its record. Below the phone breakpoint each value SHALL carry its column's name. The control that opens a row SHALL say whether it is open.

#### Scenario: Three finished trials
- **WHEN** a reader opens a claim with three finished trials on a wide screen
- **THEN** the three are rows under one row of column names, and opening the first shows its registry title, main measure, match and record link

#### Scenario: The same table on a phone
- **WHEN** the table is read at 375 pixels wide
- **THEN** each trial's state reads with the word "State" beside it and the page does not scroll sideways

### Requirement: A match score reads as a note about the match
On a claim page the score of a paper's, a background term's or a trial's match SHALL be shown in the entry's notes, worded as a match to the claim with its band and percentage. It SHALL NOT be set apart beside the entry's title or given more weight than the notes around it.

#### Scenario: Paper matched at 100%
- **WHEN** a claim page lists a paper whose match is scored 1.0
- **THEN** the paper's notes end "Match to this claim: high, 100%" and nothing but the title stands on the title's line

### Requirement: A topic's claims can be narrowed by a word
Where a topic's claims can be narrowed by status, they SHALL also be narrowed by a typed word, matched against each claim's name and headline, and both together. The page SHALL state how many claims are shown out of how many, SHALL announce that count, and SHALL offer one control that removes every narrowing. When nothing matches, the page SHALL say so in place of the table, name what was typed, and offer the same control.

#### Scenario: A word that matches one claim
- **WHEN** a reader types "gene" on a topic of seven claims, one of which names a gene therapy
- **THEN** one row is shown and the page reads "1 of 7 claims"

#### Scenario: Nothing matches
- **WHEN** a reader types a word no claim holds
- **THEN** the table is replaced by "No claim matches", the word typed, and a control that shows all seven again

### Requirement: A topic page lists the other topics
A topic page SHALL list the other topics that have published claims, each with its number of claims, with the topic being read marked. On a wide screen the list SHALL sit beside the claims; on a narrow screen it SHALL be one row above them with the topic being read in view.

#### Scenario: Topic among ten
- **WHEN** a reader opens one of ten topics with published claims
- **THEN** all ten are listed with their counts and the one being read is marked

### Requirement: Actions come before the content for a keyboard
On a claim page the follow, share, check-again and report-an-error controls SHALL be reached by the Tab key before the first control inside the content. Every page SHALL start with a link that skips to its content. A control on a white surface inside the band SHALL show its focus ring in the site's blue.

#### Scenario: Tabbing into a claim page
- **WHEN** a keyboard reader presses Tab from the top of a claim page
- **THEN** the first stop is the skip link, and "Follow" is reached before any link inside the record in brief

#### Scenario: Focus inside the status panel
- **WHEN** a link in the status panel takes keyboard focus
- **THEN** its ring is visible against the panel

### Requirement: A printed claim page is whole
When a claim page is printed, every section SHALL be open, every entry of the timetable SHALL be shown whatever was narrowed on screen, each link to a source outside the site SHALL be followed by its address, and the masthead's links, the breadcrumb, the section list and the action controls SHALL be left out. The basis mark and the marked place on the path SHALL print without background colours. Sections SHALL print open when scripting is off.

#### Scenario: Printing with papers folded and the timetable narrowed
- **WHEN** a reader prints a claim page whose papers section is folded and whose timetable shows news reports only
- **THEN** the print shows the papers and every timetable entry, and the screen returns to how it was

#### Scenario: Source link on paper
- **WHEN** the printed page lists a trial's registry record
- **THEN** the record's address is printed after its link

## MODIFIED Requirements

### Requirement: Status explanation on the page
A claim page SHALL identify the evidence events that produced the current status, and SHALL mark only those events.

#### Scenario: Status produced by one trial
- **WHEN** a claim's status is Phase 2 because of one trial
- **THEN** the page marks that trial's registered and started events as the reason for the status, and does not mark its completed or results-posted events

#### Scenario: Trial registered with three trials
- **WHEN** a claim's status is Trial registered and three standing trials have thirteen events between them
- **THEN** the page marks the three registered events and no other
