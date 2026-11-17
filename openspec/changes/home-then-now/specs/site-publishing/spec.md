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
Where scripts run, the head of the home page's day-by-day list SHALL carry one control, on the line of the list's name, that opens a panel holding every choice that narrows the list: the kind of row, the span of time, the status now and, where more than one topic is listed, the topic. Each choice SHALL be a field with its name written before it. While no field narrows the list the control SHALL say "Filter"; while one or more do, it SHALL say those picks in the fields' own words and be marked as narrowing, and the panel SHALL offer to clear them all at once. Each pick SHALL narrow the lists and be kept in the page's address exactly as before. Without scripts neither the control nor the fields SHALL be shown, and the whole list SHALL be.

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

### Requirement: A row's headline is set in the heading face
In the home page's day-by-day list, the list's name and each row's reported headline SHALL be set in the site's heading face. A day's heading, a row's labels and its status SHALL stay in the text face.

#### Scenario: A report row
- **WHEN** a report row is drawn
- **THEN** its headline, in quotation marks, is in the heading face and the outlet, the claim and the status are in the text face
