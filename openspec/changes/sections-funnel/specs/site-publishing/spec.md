## ADDED Requirements

### Requirement: Every section of a claim page follows one funnel
Each section of a claim page below "At a glance" SHALL show, in sight, a label and its value, with a number or a shape where it can stand for words; SHALL give what the value means and where it is from at one press; and SHALL give why it is listed and how sure a reading is at a second press or in the same place. Nothing the page showed before SHALL be removed by this: it is moved down the funnel. A shape SHALL be grey in every state and SHALL stand beside words or a number.

#### Scenario: Opening an answer twice
- **WHEN** a reader opens "Compared with a placebo?" and then "Where this is read from"
- **THEN** the first press shows what a placebo is and how many records name none, and the second shows which registry records the answer was read from and when

### Requirement: The record in brief opens on one sentence
"The record in brief" SHALL open on one plain sentence that gives every answer the section holds, in the order of its rows, with each answer's figure a link to its row. Under it each answer SHALL be a row holding its question and its answer, and, where the answer is so many of the claim's trials, a bar that shows the share and names it in words for a screen reader. The sentence SHALL say nothing the rows do not.

#### Scenario: A claim with seven trials
- **WHEN** a reader opens a claim with seven trials, one of which names a placebo and one of which has posted results
- **THEN** the sentence reads "Tested in 7 trials, the largest planned for 1,200 people. One record names a placebo. 1 of 7 has posted results, …", and "7 trials" leads to the row "Tested in people?"

### Requirement: Statements are grouped by who said them or by kind
Under its report a statement SHALL stand in a group named by who the report had saying it; where a claim's statements have more than one speaker and more than one kind, a reader SHALL be able to group them by kind instead. With no script the statements SHALL be grouped by who said them. Each statement SHALL carry a mark for how firmly the report put it, named in words once over the list, and SHALL keep its attribution in words for a screen reader. A statement's score SHALL be shown on its row when the check is less than very sure, and where the row opens otherwise.

#### Scenario: A statement the check is very sure of
- **WHEN** a statement's confidence is 0.93
- **THEN** its row shows its kind, its mark and its words, and opening it and then "How sure this reading is" shows "Very likely in the report · 93%"

#### Scenario: A statement the check is less sure of
- **WHEN** a statement's confidence is 0.62
- **THEN** its row shows "Likely in the report · 62%" without a press

### Requirement: Recorded opens on the record's moments
"Recorded" SHALL open on the record's moments in order of date: the first trial registered, the first trial started, the report, the first results posted, a regulator's decision, the latest record where none of these is it, and a promised date. Each SHALL be a shape, a name and a date, and SHALL lead to its year in the timetable. The timetable, with its strip and its filter, SHALL be one press under the moments, SHALL be open on paper, and SHALL open when a link leads to a record inside it.

#### Scenario: Following a moment
- **WHEN** a reader presses "First results posted"
- **THEN** the timetable opens and the year of that record is in view

### Requirement: The trials' spread is drawn over their table
Where a claim has four trials or more, the trials section SHALL show a mark for each trial under its phase, in the shape of its state and ringed where it has posted results, with a key in words. Each trial's row SHALL show its size as a bar against the claim's largest trial. The drawing SHALL be for the eye only: the table says the same in words.

#### Scenario: Forty-seven trials
- **WHEN** a reader opens a claim with 47 trials
- **THEN** the marks stand in columns by phase with the number of trials over each, and a mark leads to its trial

### Requirement: Organisations stand as names beside their part
The organisations section SHALL show one row for each part organisations play, with the names of that part beside its label in order of name; a sponsor's name SHALL carry how many of the claim's trials name it. A name SHALL open its parts, its trials, what an open registry says the organisation is, and whether a registry record was matched.

#### Scenario: A sponsor of three trials
- **WHEN** a reader presses the name of an organisation that sponsors three of the claim's trials
- **THEN** a panel names the three trials and says whether the name was matched to a registry record

### Requirement: Sharing and reminders are one section of labelled rows
A claim page SHALL offer sharing, reminders, following, its feed and its embed as rows of one section, each a label and its controls. The reminders' row SHALL be shown only where the browser can make and save the file, and a link to "Check again later" SHALL open the section and lead to that row.

#### Scenario: From the band
- **WHEN** a reader presses "Check again later" in the band
- **THEN** "Keep or pass on" opens and the row "Remind me" is in view

### Requirement: A trial's row is one line that opens
On a wide screen a trial's row SHALL hold, on one line, how many people it enrolled or plans to with a bar against the claim's largest trial, its phase, its state beside its shape, when it posted results, and its number. What it was compared with and its main measure SHALL be the first facts where the row opens. A trial that has the claim's treatment only as its comparison SHALL say so on the row.

#### Scenario: A finished trial with results
- **WHEN** a reader looks at a trial that finished and posted results
- **THEN** its row reads its size, its phase, "Finished" with its date beside a ringed full mark, the date results were posted and its number, and opening it gives what it was compared with and its main measure first

### Requirement: A folded year is drawn as its records
In the timetable a year that is folded SHALL show a shape for each of its records, oldest first, in the shapes the trials table uses, with a report as the report's mark, then how many records it holds. What the shapes stand for SHALL be said once over the timetable, and the kinds of record SHALL be said in words to a screen reader.

#### Scenario: A year of seventeen records
- **WHEN** a reader looks at a folded year that holds seventeen records
- **THEN** its row shows seventeen shapes and "17 records", and opening it lists the records

### Requirement: A registry record is one line that opens
A registry record that is not a trial on the page SHALL be a row of its title, what its record says of the trial or that it is not yet read, and its match, which stays in sight. A possible record SHALL be marked and named as possible before its title. Where to read the record, how it was read and what it names SHALL be where the row opens.

#### Scenario: A possible record not yet read
- **WHEN** a reader looks at a possible record whose details are not yet read
- **THEN** its row reads its registry number, "Details not read from the registry yet" and "Possible match: medium, 79%", and opening it gives the link to the registry

