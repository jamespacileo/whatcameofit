# Delta for site-publishing

## ADDED Requirements

### Requirement: The box offers rows for what is typed
While two or more letters of words stand in the search box, and scripts run, the box SHALL offer rows under it that hold every typed word at the start of a word. The rows SHALL be of five kinds, each under its name and always in this order: topics, treatments, conditions, reports, trials on record. A kind with no row SHALL be left out, and a kind SHALL show two rows at most. With no row to offer, nothing SHALL be shown. A pasted or typed address SHALL offer nothing.

#### Scenario: Five kinds
- **WHEN** a reader types "lung" and the site holds a topic, treatments, conditions, reports and trials with a word that starts so
- **THEN** rows are offered under "Topics", "Treatments", "Conditions", "Reports" and "Trials on record", in that order, two at most under each

#### Scenario: One letter
- **WHEN** a reader types one letter
- **THEN** nothing is offered

#### Scenario: An address
- **WHEN** a reader pastes the address of an article
- **THEN** nothing is offered and the address is looked up as before

#### Scenario: A complete trial number is typed before detail arrives

- **WHEN** a reader types NCT04510194 before search details load and leaves the field focused with the same input
- **THEN** the matching trial appears when its detail arrives without another keystroke. Dismissed suggestions stay dismissed

### Requirement: A suggested row says what it is and what is behind it
A row SHALL show what it names with the typed words marked where they start a word, and beside it: for a topic and a condition, how many claims; for a treatment, what it is for and its claim's status in the site's words; for a report, its outlet and date; for a trial, its identifier first, then its title and its phase. A report's title SHALL stand between quotation marks. A trial SHALL be listed as a record and never worded as a treatment to take. A condition SHALL be one row however many claims are for it.

#### Scenario: A treatment
- **WHEN** a treatment's name starts with what is typed
- **THEN** its row gives the name, what it is for, and where its claim stands, and opens the claim's page

#### Scenario: A condition with three claims
- **WHEN** three claims are for "Lung cancer"
- **THEN** one row says "Lung cancer" and "3 claims", and taking it searches for "Lung cancer"

### Requirement: The order of suggested rows is by rules a reader could check
No model and no score SHALL order the rows. Topics SHALL come by whether the title begins with the first typed word, then by claims. A treatment whose name begins with the word SHALL come before one that holds it later, the shorter name first. The condition most claims are for SHALL come first. Reports SHALL be newest first, each title once. A trial found by the start of its identifier SHALL come before one found by its title, and after that the newest identifier first.

#### Scenario: Two reports
- **WHEN** two reports hold the typed word, dated 15 November and 17 August
- **THEN** the one of 15 November is the first row

### Requirement: The rows are worked by keys and by a press
The down key SHALL choose the first row and then the next, the up key the one before; past either end the box itself SHALL be chosen again. Enter SHALL take the chosen row; with no row chosen it SHALL search for the words as typed, as before. Escape SHALL close the rows and keep the words. A last row SHALL send the words as typed. The box SHALL say to a screen reader that it has rows, how they are grouped, and which is chosen. Without scripts the box SHALL work as before.

#### Scenario: Enter with nothing chosen
- **WHEN** a reader types "lung" and presses Enter without choosing a row
- **THEN** the site searches for "lung" as it did before this change

#### Scenario: Escape
- **WHEN** rows are shown and the reader presses Escape
- **THEN** the rows close and "lung" stays in the box

#### Scenario: The keyboard selection survives a detail refresh

- **WHEN** a reader types lung and selects the first suggestion with Down before detail data arrives
- **THEN** if that suggestion still exists it stays selected by identity and Enter opens it, even if its row position changed
