# Spec Delta

## ADDED Requirements

### Requirement: The home page lists what is dated, day by day
Under the lookup, the home page SHALL show one list of what is dated for published claims, newest first: news reports by their publication date, registry records by their event date, and dated promises by the date promised. Rows SHALL stand under dated headings: one per day for the fourteen days up to the day the registries were last checked, one per week for the rest of that year, one per year before it. A heading SHALL say how many rows of each kind it holds.

#### Scenario: A day in the last fortnight
- **WHEN** the registries were last checked on 14 November 2026 and two news reports and one registry record are dated 9 November 2026
- **THEN** the list has a heading for Monday 9 November that says "2 reports, 1 registry record", with those three rows under it, the reports first

#### Scenario: Earlier in the year
- **WHEN** a news report is dated 28 October 2026
- **THEN** its row stands under the heading "Week of 26 October"

#### Scenario: An earlier year
- **WHEN** a news report is dated 9 January 2017
- **THEN** its row stands under the heading "2017"

#### Scenario: Unpublished claims
- **WHEN** a claim has not been published
- **THEN** none of its reports, records or promises has a row

### Requirement: The day-by-day list is dated by the last check
Above the list the home page SHALL name the day the registries were last checked and SHALL show the seven days up to it, each with its number of news reports and each leading to that day's heading. No heading SHALL be dated later than the last check. A day in those seven with nothing dated SHALL keep its heading and say that nothing is dated. A heading SHALL be worded "Today" or "Yesterday" only when that is so on the reader's own date.

#### Scenario: Checked on the reader's own date
- **WHEN** the registries were last checked on 14 November 2026 and a reader opens the page that day
- **THEN** the page names Saturday 14 November 2026, the seven days run from 8 to 14 November, and the first heading reads "Today, Saturday 14 November"

#### Scenario: A page built before the reader's date
- **WHEN** the registries were last checked on 13 November 2026 and a reader opens the page on 15 November
- **THEN** the page names 13 November as the day of the last check, its first heading is Friday 13 November, and no heading says "Today" or "Yesterday"

#### Scenario: A day with nothing dated
- **WHEN** no report, record or promise is dated 10 November 2026 and that day is among the seven
- **THEN** the list has a heading for 10 November that says nothing is dated, and the day in the row of seven leads to it

#### Scenario: An export with no day of last check
- **WHEN** the export does not say when the registries were last checked
- **THEN** the home page shows neither the dated head nor the day-by-day list, the four tabbed lists follow the lookup, and no other day stands in for the missing one

### Requirement: Rows are of three kinds, and each kind can be shown alone
Each row of the day-by-day list SHALL say its kind in words: a news report, a registry record or a promised date. Above the list, one control per kind SHALL show that kind's ground and its number of rows and SHALL narrow the list to that kind; one more SHALL show every kind. While a kind is picked, a heading with no row of it SHALL NOT be shown. The pick SHALL be recorded in the page's address. Pale amber SHALL be the ground of promised dates only.

#### Scenario: Picking a kind
- **WHEN** a reader picks the control for registry records
- **THEN** only registry rows are listed, under the headings that hold one, and the address names the pick

#### Scenario: The controls as a key
- **WHEN** a reader opens the home page
- **THEN** the three controls show a white, a pale blue and a pale amber mark beside "Reported", "Recorded" and "Promised", each with its count

#### Scenario: A kind read aloud
- **WHEN** a screen reader reads a registry row
- **THEN** it is told the row is a registry record without relying on the row's ground

### Requirement: A report row sets the report beside the record
A news report's row SHALL show the outlet's title in quotation marks with the outlet and the date, the title leading to the claim page; the evidence stage when the claim was first reported; the claim's status now with its gloss, its place on the path and its no-signal note; and the claim's latest promise, marked as a promise. Reports of one claim dated the same day SHALL share one row that names each outlet. The site SHALL add no wording of its own about a title.

#### Scenario: A report of an animal study
- **WHEN** a claim first reported from an animal study stands at preclinical only and has a report dated 11 November 2026
- **THEN** the row shows the quoted title with its outlet and date, "Animal study" as the evidence when first reported, and "Preclinical only" with "No trial in people on record" and the first place on the path marked

#### Scenario: Two outlets on one day
- **WHEN** two outlets report the same claim on 6 October 2026
- **THEN** the list has one row for that claim that day, with the first title quoted and both outlets named

#### Scenario: One claim reported on two days
- **WHEN** a claim has reports dated 6 October and 13 October 2026
- **THEN** it has a row under each date

### Requirement: A report row says what the records add
Under the status, a report row SHALL carry at most two sentences built by fixed rules from the claim's records: the first two that apply, in one fixed order of preference. Each SHALL state a count, a date or a kind only. A sentence whose count the export does not hold SHALL be left out, never estimated.

#### Scenario: The order of preference
- **WHEN** more than two sentences apply to a claim
- **THEN** the row carries the first two of: a regulator's decision with its date; the year of the first registered trial, when it is two or more calendar years before the report; how many trials are on record, how many are completed and how many have posted results; that no registry record is dated since the report, with the no-signal years; the kind of study the report was of

#### Scenario: A trial registered long before the report
- **WHEN** a claim reported in 2026 has five trials on record, the first registered in 2012, three completed and two with results posted
- **THEN** the row says the first trial was registered in 2012, 14 years before the report, and that 5 trials are on record, 3 completed, 2 with results posted

#### Scenario: Nothing since the report
- **WHEN** a claim reported in 2017 from laboratory work has no trial and carries "No signal for 9 years"
- **THEN** the row says no registry record is dated in the 9 years since the report, and that the report was of laboratory work

#### Scenario: An approval
- **WHEN** a claim has a regulator's approval dated 3 September 2026
- **THEN** the first sentence is the approval as recorded, with that date

### Requirement: Row sentences describe records and nothing else
A sentence the site writes on a home page row SHALL pass the site's checks for verdict wording and for wording about how a trial turned out. It SHALL NOT say that a promise was kept, missed or late, SHALL NOT characterise the time between a report and a record, and SHALL NOT present a trial as open to join. A build SHALL fail when the wording of such a sentence breaks one of these rules.

#### Scenario: A promised date that has passed
- **WHEN** a claim's report promised trials for 2020 and no trial is on record
- **THEN** the row shows the promise with its year and the status now, and no sentence says the date passed or the promise was missed

#### Scenario: Wording that judges
- **WHEN** a sentence's wording is changed to include "still" or "only" before a count
- **THEN** the site's build fails and names the sentence

### Requirement: A registry row names the report it belongs to
A registry record's row SHALL show what was recorded, the registry's identifier leading to the record at its source, the intervention and indication leading to the claim page, the claim's status with its place on the path, and the title, outlet and date of the claim's newest news report. Registry rows SHALL be listed for records dated in the ninety days up to the last check. An event with a confidence below 1 SHALL show it in the words the claim page uses.

#### Scenario: A trial registered last week
- **WHEN** a trial for a published claim was registered on 2 November 2026
- **THEN** its row reads "Trial registered", gives the trial's identifier as a link to the registry, names the claim and its status now, and quotes the claim's newest report with its outlet and date

#### Scenario: A follow-up paper scored 0.6
- **WHEN** a follow-up paper with a confidence of 0.6 is dated 26 October 2026
- **THEN** its row shows "Medium match · 60%"

#### Scenario: A record from last year
- **WHEN** a trial for a published claim was completed in 2024
- **THEN** it has no row on the home page and is listed on the claim page as before

### Requirement: A registry row says when a status changed
A row for a registry record dated on a day the claim's status changed SHALL say "Changed", with the status before that day and the status from it, in the words the list of status changes uses. Where several of the claim's records are dated that day, only the first listed SHALL say so. Any other registry row SHALL show the claim's status now.

#### Scenario: An approval that changed the status
- **WHEN** a regulator's approval dated 20 October 2026 moved a claim from Phase 3 trial to Approved
- **THEN** the row says "Changed", then "Was: Phase 3 trial. Now: Approved.", with the last place on the path marked

#### Scenario: A record that changed nothing
- **WHEN** a further trial is registered for a claim already at Phase 3 trial
- **THEN** the row shows "Status now" with Phase 3 trial and does not say "Changed"

### Requirement: Promised dates to come are offered with the list
Dated promises whose date is later than the last check SHALL be offered with the day-by-day list, apart from its dated headings and earliest first, behind one line that says how many there are and gives the next date; the line SHALL open them in place.

#### Scenario: Promises still to come
- **WHEN** nine published claims have a promised date after the last check and the earliest is 31 December 2026
- **THEN** the line says there are 9 promised dates to come and that the next is 31 Dec 2026, and pressing it lists the nine, earliest first

#### Scenario: Nothing promised to come
- **WHEN** no published claim has a promised date after the last check
- **THEN** the line is not shown

### Requirement: A promise row shows the promise beside the status now
A promised date's row SHALL show the claim's latest dated promise on pale amber with its year, the report it came from and the claim's status now. A promise dated on or before the last check SHALL be listed under that date's heading. The page SHALL add no wording about a date having passed.

#### Scenario: A promise for a past year
- **WHEN** a claim's latest promise is dated 2020 and the claim stands at preclinical only
- **THEN** its row stands under the heading "2020", shows the promise with 2020 in bold on pale amber and "Preclinical only", and says nothing about the date

### Requirement: The day of the last check shows one older claim
After its own rows, the heading for the day of the last check SHALL be followed by one report row for a claim first reported in an earlier year, chosen by a fixed rule from that day's date so that it differs from one day to the next and is the same for every reader. The row SHALL say it was picked by the date. When no published claim was first reported in an earlier year, no such row SHALL be shown.

#### Scenario: A day with nothing dated
- **WHEN** nothing is dated on the day of the last check and published claims include some first reported before that year
- **THEN** that day's heading says nothing is dated and is followed by one older claim's row, said to be picked by the date

#### Scenario: Two readers on one day
- **WHEN** two readers open the home page built from the same export
- **THEN** both see the same older claim

#### Scenario: The next day
- **WHEN** the registries are checked again the next day and the site is rebuilt
- **THEN** the older claim shown is a different one, as long as more than one qualifies

### Requirement: The day-by-day list marks a reader's last visit
For a reader with scripting on whose browser keeps the day of an earlier visit, the day-by-day list SHALL draw one line between the rows dated from that day on and the rows dated before it, naming that day: the span the since line counts. On a first visit, where the browser keeps nothing, or when nothing is dated in the span, no line SHALL be drawn. Rows of this list SHALL NOT carry "New". The day SHALL be the one the since line uses, kept in the reader's browser only.

#### Scenario: A later visit
- **WHEN** a reader last opened the home page on 7 November and opens it on 14 November, and ten reports are dated from 7 November on
- **THEN** one line naming 7 Nov 2026 stands under the rows of 7 November and above the heading for 6 November

#### Scenario: A first visit
- **WHEN** a reader opens the home page with nothing kept in their browser
- **THEN** no line is drawn

#### Scenario: One kind shown
- **WHEN** the reader picks registry records and none is dated from their last visit on
- **THEN** no line is drawn

### Requirement: The day-by-day list opens on its day headings
With scripting on, the day-by-day list SHALL first show its day headings, and SHALL show earlier headings a batch at a time from one control directly under the list that says how many rows remain. Every row SHALL be in the page as built: with scripting off, and in print, the whole list SHALL be shown. An address that names a heading SHALL show the list opened as far as that heading.

#### Scenario: Opening the home page
- **WHEN** the list holds a fortnight of day headings and thirty earlier headings
- **THEN** the day headings are shown, and a control under them says how many rows are earlier and shows the next headings when pressed

#### Scenario: An address naming an earlier week
- **WHEN** the home page is opened at an address that names the heading "Week of 5 October"
- **THEN** the list is opened as far as that heading and the page is at it

#### Scenario: Scripting off
- **WHEN** the home page is opened with scripting off
- **THEN** every heading and every row of the list is shown

## MODIFIED Requirements

### Requirement: Long lists are read a page at a time
Each of the home page's four tabbed lists SHALL show ten rows at a time; its day-by-day list is opened as its own requirement says. Every other list of claims SHALL show 25 rows at a time. A list longer than one page SHALL have, directly under it, a control to step to the next and the previous page and a line saying which rows are shown and how many there are. A list that fits one page SHALL show no such control. Where a list can be narrowed by status, the narrowing SHALL apply to the whole list and SHALL return the reader to its first page.

Every row SHALL be in the page as built: with scripting off, and in print, the whole list SHALL be shown. The page in view SHALL be recorded in the page's address, and an address naming a page that does not exist SHALL show the nearest page that does.

#### Scenario: More rows than one page
- **WHEN** published claims have 104 source articles between them
- **THEN** the home page's Headlines list shows the ten newest, says "1–10 of 104 headlines", and the next step shows the eleventh to the twentieth

#### Scenario: A list that fits one page
- **WHEN** a topic has four published claims
- **THEN** all four are shown and no paging control is shown

#### Scenario: A page that does not exist
- **WHEN** the address names page 99 of a list with eleven pages
- **THEN** the eleventh page is shown

#### Scenario: Narrowing by status
- **WHEN** a reader on the second page of a year's claims picks a status
- **THEN** the claims at that status across the whole year are listed from their first page

#### Scenario: Scripting off
- **WHEN** the home page is opened with scripting off
- **THEN** every headline and every claim is listed

### Requirement: The home page offers the claims in four orders
Under the day-by-day list, under a heading of their own, the home page SHALL offer these lists of published claims, in this order, and SHALL show one at a time, the first unless the address names another:

1. Headlines: every source article, newest first.
2. Status changes: every change from one status to another, newest first, each with the day, the status from that day and the status before it. A claim's first status is not a change.
3. Promises: every claim with a dated promise, in order of its latest promised date, earliest first, with the promise beside the status now.
4. No signal: every claim carrying the no-signal overlay, the most years first.

A list with no rows SHALL NOT be offered, except Headlines. Each list SHALL show how many rows it has. Every order SHALL be a date or a count from the record: the page SHALL NOT rank or grade claims, and SHALL NOT word a promise as kept, missed or late. The list in view SHALL be recorded in the page's address. With scripting off, every list SHALL be shown, one under the other.

#### Scenario: Lists on the home page
- **WHEN** one published claim has changed status twice, and another has a dated promise and the no-signal overlay
- **THEN** the home page offers Headlines, Status changes with two rows, Promises with one row and No signal with one row

#### Scenario: A first status is not a change
- **WHEN** a claim's history holds only its first status
- **THEN** the claim has no row under Status changes

#### Scenario: A promise whose date has passed
- **WHEN** a claim's promised date is earlier than today
- **THEN** it is listed first under Promises with its status now, and the page adds no wording about the date having passed

#### Scenario: Nothing has gone quiet
- **WHEN** no published claim carries the no-signal overlay
- **THEN** the No signal list is not offered

#### Scenario: A list named in the address
- **WHEN** the home page is opened at an address naming the Status changes list
- **THEN** that list is the one shown

#### Scenario: Where the four lists stand
- **WHEN** a reader opens the home page
- **THEN** the day-by-day list comes first under the lookup, and the four lists follow it under their own heading

### Requirement: The home page's lists can be narrowed by status and by topic
Above the day-by-day list, the home page SHALL show how many published claims are at each status, on the same path a topic page shows, and SHALL let a reader pick one status. Where more than one topic is listed, it SHALL also let a reader choose one topic. A pick SHALL narrow the day-by-day list and all four tabbed lists at once to rows whose claim has that status now and is filed under that topic; both picks together SHALL narrow to rows that meet both. Each tabbed list's count SHALL be the rows left, and a list left with none SHALL say so in place of an empty table. In the day-by-day list a heading SHALL count the rows left under it, a heading left with none SHALL NOT be shown, and a list left with none SHALL say so. With a topic chosen, the counts on the path SHALL be that topic's. The picks SHALL be recorded in the page's address. The counts SHALL be stated as numbers only: the page SHALL NOT rank topics or characterise the spread.

#### Scenario: Counts on the path
- **WHEN** three published claims stand at preclinical only, phase 2 and approved
- **THEN** the home page shows one at each of those places and none at the others, and a place with none cannot be picked

#### Scenario: Picking a status
- **WHEN** a reader picks phase 3
- **THEN** each list shows only rows of claims now in phase 3, and each list's count is the number of those rows

#### Scenario: Narrowing to a topic
- **WHEN** a reader chooses a topic with seven claims
- **THEN** every list shows only that topic's rows and the path shows where those seven stand

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
- **WHEN** a reader picks approved and the control for registry records
- **THEN** the day-by-day list shows only registry rows of claims now approved

### Requirement: The home page says what is dated since a reader's last visit
Above its four tabbed lists, the home page SHALL show a reader with scripting on one line counting the news reports, status changes and promised dates that are dated from the day of their last visit to today, each count opening the list that holds its rows. Rows of news reports and status changes dated in that span SHALL carry the word "New". On a first visit, or where the browser keeps nothing, the line SHALL cover the last thirty days and no row SHALL be marked. When nothing is dated in the span the line SHALL say so. The day of a visit SHALL be kept in the reader's browser only and SHALL NOT be sent to the site. The line SHALL state counts only.

#### Scenario: A later visit
- **WHEN** a reader last opened the home page on 7 November and opens it on 14 November, and 12 reports and 1 status change are dated in between
- **THEN** the line reads "Since your last visit on 7 Nov 2026: 12 news reports, 1 status change." and those rows carry "New"

#### Scenario: A first visit
- **WHEN** a reader opens the home page with nothing kept in their browser
- **THEN** the line begins "In the last 30 days" and no row carries "New"

#### Scenario: A second look on the same day
- **WHEN** the reader reloads the home page later the same day
- **THEN** the line and the marked rows are the same as on the first look that day

#### Scenario: Storage holds something else
- **WHEN** the browser's kept value is not in the expected shape
- **THEN** the visit is treated as a first visit

### Requirement: The home page's controls fit a phone
Below the site's one breakpoint, with scripting on, the status counts and the topic choice SHALL be reached from one control and SHALL start open when the address already narrows the lists. The controls for the kinds of row SHALL all be in view without scrolling sideways, and so SHALL the four lists' tabs where they stand. Every pressed thing SHALL be at least 44 pixels tall, except a link inside a sentence.

#### Scenario: A phone, first visit
- **WHEN** the home page is opened at 375 pixels wide
- **THEN** the controls for the kinds of row are all in view, the counts are behind "Narrow these lists", and the four tabs sit in one row above their lists

#### Scenario: A narrowed address on a phone
- **WHEN** the home page is opened at an address that names a status
- **THEN** the counts are shown, with the named status picked

### Requirement: A headline starts on a phone's first screen
At 375 by 812 pixels, with scripting on and nothing followed, the first row of the home page's day-by-day list SHALL start within the first screen, and the controls for the kinds of row SHALL be in view. The order a keyboard moves in SHALL be the page's own.

#### Scenario: A phone, first visit
- **WHEN** the home page is opened at 375 by 812 pixels
- **THEN** the first row of the day-by-day list starts above 812 pixels and the controls for the kinds of row sit above it
