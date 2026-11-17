# Spec Delta

## ADDED Requirements

### Requirement: A term in "At a glance" is one line that opens
On a claim page each term of "At a glance" SHALL be drawn as one line holding its label and its value, on one baseline at the top of the row at every width, with the value's other names under it. The line SHALL open, on a press and from the keyboard, to the source's definition whole and in quotation marks, the term's match, where the claim's term is filed when it differs, and the card's credit and reasons. With no script, and on paper, every row SHALL be open. A link to a term from elsewhere on the page SHALL open it. The claim's own facts SHALL be rows of the same list.

#### Scenario: Reading the list
- **WHEN** a reader opens a claim with four terms at 1400 pixels wide
- **THEN** each term is one line with its label and its value, and the three facts follow as rows of the same list

#### Scenario: From the band
- **WHEN** the reader follows "Kind of molecule" from the band
- **THEN** that term's row is open and in view

### Requirement: A term's score is said where its row opens, unless it is below the high band
A term's score in the high band, and how a term was found where it has no percentage, SHALL be shown where the row opens, as the page's score chip at the head of that term's "Why it matched", ahead of the reasons. A term's score below the high band SHALL be shown on the closed row, in sight with nothing to press. This is an exception, for term matches in "At a glance" only, to the requirement that every score is in sight.

#### Scenario: A strong match
- **WHEN** a condition is matched to a vocabulary term at 0.98
- **THEN** the closed row shows the label and the value only, and the opened row shows a chip reading "High, 98%" under "Why it matched", followed by the reasons

#### Scenario: A weaker match
- **WHEN** a condition is matched to a vocabulary term at 0.62
- **THEN** the closed row shows a chip reading "Medium, 62%" beside the value

### Requirement: The source's words end in a pill that opens the source
Where a row opens to a source's words, the words SHALL be shown without a label, and SHALL be followed by a pill that names the source and is a link to the term's page at that source, or to the source itself where the words are another source's. The link SHALL open in a new tab and SHALL say so to a screen reader, with whose words they are. A term with no words of its source's SHALL show the pill beside the label "Source".

#### Scenario: A definition from a vocabulary
- **WHEN** a reader opens "Claimed for"
- **THEN** the definition is followed by a pill reading "MeSH", and pressing it opens the term's page at the vocabulary in a new tab

### Requirement: An opened row is marked and its parts are labelled
An opened row SHALL be marked as open across the list's width. After the source's words, each part SHALL carry its own label: where the term is filed, naming the source; the term as its source names it with its credit; and why it matched. What the row's value already says SHALL NOT be repeated in the opened row. The source's words SHALL be the most prominent part and the credit the least.

#### Scenario: Reading an opened term
- **WHEN** a reader opens "Claimed for"
- **THEN** the row is tinted, the definition is the largest text under it, and "Filed in MeSH as", the term with its credit and "Why it matched" follow, each smaller and each with its label
