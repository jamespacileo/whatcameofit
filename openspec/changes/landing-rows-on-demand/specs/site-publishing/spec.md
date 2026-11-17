# Spec Delta

## ADDED Requirements

### Requirement: The home page holds what a reader sees on arrival
The home page as built SHALL hold the first ten rows of each of its tabbed lists and the rows under its day-by-day list's day headings, and SHALL NOT hold the other rows of those lists. The number each tab shows, each pager's line and the line about the reader's last visit SHALL state the whole list's numbers all the same.

#### Scenario: Opening the home page
- **WHEN** published claims have 1,597 source articles between them and the home page is opened
- **THEN** the page holds ten rows of the Headlines list, its tab says 1,597, its pager says "1–10 of 1597 headlines", and no other row of the list has been fetched

#### Scenario: A list that fits one page
- **WHEN** the No signal list has four rows
- **THEN** all four are in the page

### Requirement: The rest of a list is fetched when a reader asks for it
The rest of each home page list SHALL be published as a file of rows, drawn as the rows in the page are drawn. The page SHALL fetch a list's file once, the first time a reader asks for something that needs rows that are not in the page. Once fetched, the rows SHALL be narrowed, counted and paged as the rows in the page are.

#### Scenario: Stepping to the next page
- **WHEN** a reader presses "Next" under the Headlines list for the first time
- **THEN** the rest of its rows are fetched, and the eleventh to the twentieth headline are shown

#### Scenario: Narrowing by status
- **WHEN** a reader picks the status "Approved" on the home page
- **THEN** the rest of each tabbed list is fetched, and each tab shows how many of its rows, among all of them, are of claims at that status

#### Scenario: A count pressed on the line about the last visit
- **WHEN** a reader presses "82 of 1597 news reports" on the line about their last visit
- **THEN** the rest of the Headlines list is fetched and the list shows the 82 reports dated since

#### Scenario: An address naming a later page
- **WHEN** the home page is opened at an address that names the third page of the Headlines list
- **THEN** the rest of the Headlines list is fetched and the twenty-first to the thirtieth headline are shown

#### Scenario: A list that is whole in the page
- **WHEN** the No signal list has four rows
- **THEN** no file of rows is published for it

### Requirement: A file of rows is not a page
A file of rows SHALL hold rows only, and search engines SHALL be asked not to index it.

#### Scenario: A file of rows asked for by its address
- **WHEN** the file of the Headlines list's rows is requested
- **THEN** it is served as text with a header that asks search engines not to index it

### Requirement: A list says when its rows are not all in the page
While a list's rows are being fetched the list SHALL say so in words and SHALL be marked busy. If they do not arrive, the list SHALL say that the rest of it did not load and SHALL offer a control to ask again. A list whose rows are not all in the page SHALL NOT say that nothing matches a choice, that a span has been read to its end, or how many earlier rows remain.

#### Scenario: Rows on their way
- **WHEN** a reader presses "Next" under a list whose rows are not yet fetched
- **THEN** the list says "Loading the rest of this list." until the rows arrive

#### Scenario: Rows that do not arrive
- **WHEN** a list's file of rows cannot be fetched
- **THEN** the list says "The rest of this list did not load." with a control to try again, keeps showing its first rows, and does not say that nothing matches

## MODIFIED Requirements

### Requirement: Long lists are read a page at a time
Each of the home page's four tabbed lists SHALL show ten rows at a time; its day-by-day list is opened as its own requirement says. Every other list of claims SHALL show 25 rows at a time. A list longer than one page SHALL have, directly under it, a control to step to the next and the previous page and a line saying which rows are shown and how many there are. A list that fits one page SHALL show no such control. Where a list can be narrowed by status, the narrowing SHALL apply to the whole list and SHALL return the reader to its first page.

Every row of every other list of claims SHALL be in the page as built: with scripting off, and in print, the whole list SHALL be shown. The home page's tabbed lists hold their first ten rows as built. With scripting off, and in print while the rest are not in the page, each SHALL show those rows and SHALL say how many of its rows are shown and that every claim is also listed under its topic, with a link to the topics. The page in view SHALL be recorded in the page's address, and an address naming a page that does not exist SHALL show the nearest page that does.

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
- **WHEN** the home page is opened with scripting off and its Headlines list has 104 rows
- **THEN** the ten newest headlines are listed, and the list says that the first 10 of 104 headlines are shown and links to the topics, where every claim is listed

#### Scenario: Scripting off on a topic page
- **WHEN** a topic page with 60 claims is opened with scripting off
- **THEN** all 60 claims are listed

### Requirement: The day-by-day list opens on its day headings
With scripting on, the day-by-day list SHALL first show its day headings, and SHALL show earlier headings a batch at a time from one control directly under the list that says how many rows remain. The rows under its day headings SHALL be in the page as built. The earlier headings and the promised dates still to come SHALL be fetched the first time a reader asks for a span wider than the past week, for promised dates, or for an address that names an earlier heading. With scripting off, and in print while they are not in the page, the list SHALL show its day headings and SHALL say how many earlier rows and how many promised dates still to come are not shown, and that every claim is also listed under its topic, with a link to the topics. An address that names a heading SHALL show the list opened as far as that heading.

#### Scenario: Opening the home page
- **WHEN** the list holds a fortnight of day headings and thirty earlier headings
- **THEN** the day headings are shown, and the earlier headings are not in the page

#### Scenario: Widening the span
- **WHEN** a reader asks for the past month
- **THEN** the earlier headings are fetched, the headings dated in the past month are shown, and a control under them says how many rows are earlier and shows the next headings when pressed

#### Scenario: An address naming an earlier week
- **WHEN** the home page is opened at an address that names the heading "Week of 5 October"
- **THEN** the earlier headings are fetched, the list is opened as far as that heading and the page is at it

#### Scenario: Scripting off
- **WHEN** the home page is opened with scripting off
- **THEN** every day heading and its rows are shown, and the list says how many earlier rows are not shown and links to the topics
