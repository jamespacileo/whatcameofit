# Spec Delta

## ADDED Requirements

### Requirement: A summary and a section's note are held short, with the rest on request
On a claim page, where a script runs, the summary SHALL be drawn in at most three lines and the note of "At a glance", trials, registry records, papers and organisations in one line, each followed by a control reading "More" only when text is cut, which shows the whole text and then reads "Less". The whole text SHALL remain in the page for a screen reader and for search, and SHALL be drawn whole with no script and on paper. The notes of "The record in brief" and of the reported statements SHALL NOT be cut.

#### Scenario: A long summary
- **WHEN** a claim's summary runs to five lines at the reader's width
- **THEN** three lines are drawn, "More" follows, and pressing it draws all five and reads "Less"

#### Scenario: A summary that fits
- **WHEN** a claim's summary is one line
- **THEN** no control is drawn

#### Scenario: Paper
- **WHEN** the page is printed
- **THEN** every summary and note is whole and no control is printed

### Requirement: Sections a reader acts from start folded
"Pass it on" and "Check again later" SHALL start folded at every width. The registry records section SHALL start folded when it holds no matched record. A link into a folded section SHALL open it.

#### Scenario: Only possible records
- **WHEN** a claim page lists one possible registry record and no matched one
- **THEN** the section starts folded with "1 possible" beside its heading, and the status card's "1 possible" link opens it

### Requirement: The band's side column holds the topic's drawing
Where the section list stands beside the sheet, the band's side column SHALL hold the topic's drawing, hidden from a screen reader. It SHALL NOT be drawn at narrower widths or on paper.

#### Scenario: Wide screen
- **WHEN** a claim in a topic drawn as a tooth is opened at 1400 pixels wide
- **THEN** the tooth is drawn large at the left of the title, and the topic chip still names the topic
