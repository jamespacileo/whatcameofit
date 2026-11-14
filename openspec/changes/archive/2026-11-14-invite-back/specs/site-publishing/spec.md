## ADDED Requirements

### Requirement: Counts in the since line stand beside their totals and narrow their lists
Each count in the home page's since line SHALL be given with the total of the list it belongs to. When any row is dated in the span and no status change is, the line SHALL say none of the status changes are. Pressing a count SHALL show its list narrowed to the rows dated in the span, and pressing it again, or "Show all", SHALL show the whole list. When a followed claim's status differs from the one kept, the line SHALL say how many have changed and link to the list.

#### Scenario: What is dated since the last visit
- **WHEN** 12 of 104 reports and 1 of 38 status changes are dated since the reader's last visit
- **THEN** the line reads "12 of 104 news reports, 1 of 38 status changes"

#### Scenario: No status change since the last visit
- **WHEN** 14 reports and no status change are dated since the reader's last visit
- **THEN** the line reads "14 of 104 news reports, none of 38 status changes"

#### Scenario: Pressing a count
- **WHEN** the reader presses "14 of 104 news reports"
- **THEN** the Headlines list shows those 14 rows and "Show all" brings back the rest

### Requirement: A headline starts on a phone's first screen
At 375 by 812 pixels, with scripting on and nothing followed, the first row of the home page's first list SHALL start within the first screen, and all four tabs SHALL be in view. The order a keyboard moves in SHALL be the page's own.

#### Scenario: A phone, first visit
- **WHEN** the home page is opened at 375 by 812 pixels
- **THEN** the first headline row starts above 812 pixels and the four tabs sit in one row

### Requirement: Topic pages end on a next step
A topic page SHALL end with a link to look up another headline and, when a suggestion address is configured, the link to suggest one. Rows of a claim list first reported since the reader's last visit to the home page SHALL carry the word "New". A pager step that leads nowhere SHALL be passed over by the Tab key.

#### Scenario: A topic's status changes as a feed
- **WHEN** a reader reaches the end of a topic page
- **THEN** it offers to look up another headline
