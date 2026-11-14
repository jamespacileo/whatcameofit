## ADDED Requirements

### Requirement: The home page says what is dated since a reader's last visit
Above its lists, the home page SHALL show a reader with scripting on one line counting the news reports, status changes and promised dates that are dated from the day of their last visit to today, each count opening the list that holds its rows. Rows of news reports and status changes dated in that span SHALL carry the word "New". On a first visit, or where the browser keeps nothing, the line SHALL cover the last thirty days and no row SHALL be marked. When nothing is dated in the span the line SHALL say so. The day of a visit SHALL be kept in the reader's browser only and SHALL NOT be sent to the site. The line SHALL state counts only.

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

### Requirement: Ways back sit beside the answer
A claim page's status panel SHALL link to the page's reminders where they can be offered. The notice that a page has not been checked by a person SHALL follow the status panel, never precede it. The home page SHALL link the feed of status changes in the open, and each topic page SHALL link a feed of that topic's status changes and offer to share the page. A claim page SHALL end with a link to look up another headline, and the home page SHALL end with the link to suggest a headline when a suggestion address is configured.

#### Scenario: Following from a claim page
- **WHEN** a reader opens a claim page
- **THEN** the status panel holds a link to "Check again later", and the page's last section leads to the lookup

#### Scenario: A topic's status changes as a feed
- **WHEN** a topic has a claim whose status has changed twice
- **THEN** the topic page links a feed holding those changes, newest first

### Requirement: The home page's controls fit a phone
Below the site's one breakpoint, with scripting on, the status counts and the topic choice SHALL be reached from one control and SHALL start open when the address already narrows the lists. The four lists' tabs SHALL all be in view without scrolling sideways. Every pressed thing SHALL be at least 44 pixels tall, except a link inside a sentence.

#### Scenario: A phone, first visit
- **WHEN** the home page is opened at 375 pixels wide
- **THEN** all four tabs are in view and the counts are behind "Narrow these lists"

#### Scenario: A narrowed address on a phone
- **WHEN** the home page is opened at an address that names a status
- **THEN** the counts are shown, with the named status picked
