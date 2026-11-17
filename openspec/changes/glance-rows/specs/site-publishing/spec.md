# Spec Delta

## ADDED Requirements

### Requirement: A term in "At a glance" is one line that opens
On a claim page each term of "At a glance" SHALL be drawn as one line holding its label, its value, its score or how it was found, and the name of the source whose term it is. The line SHALL open, on a press and from the keyboard, to whose words they are, the source's definition whole, where the claim's term is filed when it differs, and the card's credit and reasons. The source's name SHALL be in sight while the row is closed. With no script, and on paper, every row SHALL be open. A link to a term from elsewhere on the page SHALL open it. The claim's own facts SHALL be rows of the same list.

#### Scenario: Reading the list
- **WHEN** a reader opens a claim with four terms at 1400 pixels wide
- **THEN** each term is one line with its value, its score and its source's name, and the three facts follow as rows of the same list

#### Scenario: Opening a term
- **WHEN** the reader presses a term's line
- **THEN** the source's definition is shown whole with whose words they are and why the term matched, and pressing the score opens the score's own panel and not the row

#### Scenario: From the band
- **WHEN** the reader follows "Kind of molecule" from the band
- **THEN** that term's row is open and in view

### Requirement: A row of "At a glance" is read label to value, and opens to labelled parts
The label and the value of a row SHALL share a line at the top of the row, at every width. The score, how a term was found and the source's name SHALL be drawn quieter than the label and the value, and a lower-band reading SHALL keep its words in the page's ink. An opened row SHALL be marked as open across the list's width, and what it opens to SHALL be a set of parts, each with its own label: the source's words, where the term is filed, the term as its source names it with its credit, and why it matched. The source's words SHALL be the most prominent part and the credit the least.

#### Scenario: Reading an opened term
- **WHEN** a reader opens "Claimed for"
- **THEN** the row is tinted, the definition is the largest text under it beside "In MeSH’s words", and "Why it matched" and the credit follow, each smaller and each with its label

### Requirement: "At a glance" is in two named groups
The terms of "At a glance" SHALL stand in a group named "The claim" and the claim's own facts in a group named "On record", each name beside its rows on a wide screen and over them on a phone. On a wide screen the labels and the values of "At a glance" SHALL stand in the same columns as the questions and the answers of "The record in brief".

#### Scenario: The two sections together
- **WHEN** a reader looks at "At a glance" above "The record in brief" at 1400 pixels wide
- **THEN** each has its group names in the left column, and the values of the first stand directly over the answers of the second

