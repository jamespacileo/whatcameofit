## ADDED Requirements

### Requirement: The home page's first screen leads with the lookup
The home page's opening band SHALL hold the title, one sentence saying what the site does, and the lookup box as the largest control on the page. Under the box, on a screen wider than a phone, it SHALL offer the three listed topics with the most claims as words to try, each looking its words up when pressed, and SHALL say how many claims are tracked in how many topics, as numbers only. The words to try SHALL be shown only where scripting can run them. The box SHALL keep its label for a screen reader wherever the label is not drawn.

#### Scenario: A word to try
- **WHEN** a reader presses a topic offered under the box
- **THEN** the box holds that topic's name and the page answers as if the reader had typed it

#### Scenario: Scripting off
- **WHEN** the home page is opened with scripting off
- **THEN** no words to try are shown

#### Scenario: A phone
- **WHEN** the home page is opened at 375 by 812 pixels
- **THEN** neither the words to try nor the count line is drawn, and the box's label is

### Requirement: The home page says beside its list how it is made
On a wide screen the home page SHALL show, beside the day-by-day list, how a status is set in at most three steps with a link to the method page, a link to the feed of status changes, and that the site gives no medical advice and that a registered trial is not a treatment option. It SHALL add no verdict wording and no count.

#### Scenario: A wide screen
- **WHEN** the home page is opened on a screen at least 72rem wide
- **THEN** the three parts stand at the right of the list, each with one link

#### Scenario: A narrower screen
- **WHEN** the home page is opened on a narrower screen
- **THEN** the parts are not drawn, and the page's footer still carries the notices

## MODIFIED Requirements

### Requirement: The home page's lists can be narrowed by status and by topic
Above the day-by-day list, the home page SHALL offer one field that names each status with how many published claims are at it, in the order of the path a topic page shows, and SHALL let a reader pick one status; a status with no claim SHALL NOT be pickable. Where more than one topic is listed, it SHALL also let a reader choose one topic: from a list beside the day-by-day list on a wide screen, and from a field on a narrower one. A pick SHALL narrow the day-by-day list and all tabbed lists at once to rows whose claim has that status now and is filed under that topic; both picks together SHALL narrow to rows that meet both. Each tabbed list's count SHALL be the rows left, and a list left with none SHALL say so in place of an empty table. In the day-by-day list a heading SHALL count the rows left under it, a heading left with none SHALL NOT be shown, and a list left with none SHALL say so. With a topic chosen, the counts in the status field SHALL be that topic's. The picks SHALL be recorded in the page's address. The counts SHALL be stated as numbers only: the page SHALL NOT rank topics or characterise the spread.

#### Scenario: Counts on the path
- **WHEN** three published claims stand at preclinical only, phase 2 and approved
- **THEN** the status field shows one at each of those and none at the others, and a status with none cannot be picked

#### Scenario: Picking a status
- **WHEN** a reader picks phase 3
- **THEN** each list shows only rows of claims now in phase 3, and each list's count is the number of those rows

#### Scenario: Narrowing to a topic
- **WHEN** a reader chooses a topic with seven claims
- **THEN** every list shows only that topic's rows and the status field shows where those seven stand

#### Scenario: A list left empty
- **WHEN** no claim in the chosen topic carries the no-signal overlay
- **THEN** the No signal list shows a count of none and says nothing is in the list for that choice

#### Scenario: One topic
- **WHEN** only one topic is listed
- **THEN** no topic choice is shown

#### Scenario: Narrowing the day-by-day list
- **WHEN** a reader picks phase 3 and one day's heading holds two reports of claims now in phase 3 and one of a claim at preclinical only
- **THEN** that heading says "2 reports" and lists those two rows, and a heading whose claims are all at other statuses is not shown

#### Scenario: A status and a kind together
- **WHEN** a reader picks approved and chooses registry records
- **THEN** the day-by-day list shows only registry rows of claims now approved

### Requirement: The day-by-day list is dated by the last check
Above the list the home page SHALL name the day the registries were last checked. No heading SHALL be dated later than the last check. With scripting on, a heading with nothing under it SHALL NOT be shown; as built, a day in the seven up to the last check with nothing dated keeps its heading and says that nothing is dated. A heading SHALL be worded "Today" or "Yesterday" only when that is so on the reader's own date.

#### Scenario: Checked on the reader's own date
- **WHEN** the registries were last checked on 14 November 2026, a report is dated that day and a reader opens the page that day
- **THEN** the page names Saturday 14 November 2026 as the day of the last check and the first heading reads "Today, Saturday 14 November"

#### Scenario: A page built before the reader's date
- **WHEN** the registries were last checked on 13 November 2026 and a reader opens the page on 15 November
- **THEN** the page names 13 November as the day of the last check and no heading says "Today" or "Yesterday"

#### Scenario: A day with nothing dated
- **WHEN** no report, record or promise is dated 10 November 2026 and a reader opens the page with scripting on
- **THEN** the list shows no heading for 10 November

#### Scenario: An export with no day of last check
- **WHEN** the export does not say when the registries were last checked
- **THEN** the home page shows neither the dated head nor the day-by-day list, the tabbed lists follow the lookup, and no other day stands in for the missing one

### Requirement: Rows are of three kinds, and each kind can be shown alone
Each row of the day-by-day list SHALL say its kind in words: a news report, a registry record or a promised date. Above the list, one field SHALL name every kind that has a row and SHALL narrow the list to the kind chosen, or show every kind. While a kind is chosen, a heading with no row of it SHALL NOT be shown. The pick SHALL be recorded in the page's address. Pale amber SHALL be the ground of promised dates only.

#### Scenario: Picking a kind
- **WHEN** a reader chooses registry records
- **THEN** only registry rows are listed, under the headings that hold one, and the address names the pick

#### Scenario: The controls as a key
- **WHEN** a reader opens the home page's kind field
- **THEN** it offers "Everything", "News reports", "Registry records" and "Promised dates", leaving out a kind with no row

#### Scenario: A kind read aloud
- **WHEN** a screen reader reads a registry row
- **THEN** it is told the row is a registry record without relying on the row's ground

### Requirement: Promised dates to come are offered with the list
Dated promises whose date is later than the last check SHALL be offered with the day-by-day list when the reader chooses promised dates, apart from its dated headings and earliest first, behind one line that says how many there are and gives the next date; the line SHALL open them in place. With scripting off the line SHALL stand above the list.

#### Scenario: Promises still to come
- **WHEN** nine published claims have a promised date after the last check, the earliest is 31 December 2026, and a reader chooses promised dates
- **THEN** the line says there are 9 promised dates to come and that the next is 31 Dec 2026, and pressing it lists the nine, earliest first

#### Scenario: Every kind shown
- **WHEN** a reader has chosen no kind
- **THEN** the line is not shown

#### Scenario: Nothing promised to come
- **WHEN** no published claim has a promised date after the last check
- **THEN** the line is not shown

### Requirement: The day of the last check shows one older claim
Under the day-by-day list, under a heading of its own, the home page SHALL show one report row for a claim first reported in a year before the last check, chosen by a fixed rule from that day's date so that it differs from one day to the next and is the same for every reader. The heading SHALL say it was picked by the date. It SHALL be shown in every span of time, and SHALL be left out by a kind, status or topic it does not meet. When no published claim was first reported in an earlier year, no such row SHALL be shown.

#### Scenario: A day with nothing dated
- **WHEN** nothing is dated on the day of the last check and published claims include some first reported before that year
- **THEN** one older claim's row stands after every dated heading, under a heading that says it was picked by the date

#### Scenario: Two readers on one day
- **WHEN** two readers open the home page built from the same export
- **THEN** both see the same older claim

#### Scenario: The next day
- **WHEN** the registries are checked again the next day and the site is rebuilt
- **THEN** the older claim shown is a different one, as long as more than one qualifies

### Requirement: The day-by-day list opens on its day headings
With scripting on, the day-by-day list SHALL first show what is dated in the seven days up to the last check, and SHALL let a reader choose the span it keeps to from one field: the past week, the past month, the past year or all time, each counted back from the day of the last check. The pick SHALL be recorded in the page's address. Within a span, headings earlier than the day headings SHALL be shown a batch at a time from one control directly under the list that says how many rows remain. Where a span narrower than all time has been read to its end, the page SHALL say so, or that nothing is dated in it, and SHALL offer the next wider span with one press. Every row SHALL be in the page as built: with scripting off, and in print, the whole list SHALL be shown. An address that names a heading SHALL show the list opened as far as that heading, widened to all time when the heading is outside the span.

#### Scenario: Opening the home page
- **WHEN** nine reports are dated in the seven days up to the last check
- **THEN** those nine rows are shown under their day headings, and under them the page says that is everything dated in the past week and offers the past month

#### Scenario: A wider span
- **WHEN** a reader chooses the past year
- **THEN** the day headings are shown, and a control under them says how many rows are earlier and shows the next headings when pressed

#### Scenario: Nothing in the span
- **WHEN** nothing is dated in the seven days up to the last check
- **THEN** the page says nothing is dated in the past week and offers the past month

#### Scenario: An address naming an earlier week
- **WHEN** the home page is opened at an address that names the heading "Week of 5 October"
- **THEN** the list is widened to all time, opened as far as that heading, and the page is at it

#### Scenario: Scripting off
- **WHEN** the home page is opened with scripting off
- **THEN** every heading and every row of the list is shown
