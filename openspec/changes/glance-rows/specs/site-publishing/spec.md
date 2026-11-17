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
