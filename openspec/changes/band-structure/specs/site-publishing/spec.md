# Spec Delta

## ADDED Requirements

### Requirement: A record page sets its title and section headings in the heading face
A claim page and a topic page SHALL set the title in their band and their section headings in the heading face, a serif served from the site itself. The status label, the records and every other role SHALL stay in the page's face. A page that is not a claim or a topic page SHALL NOT load the heading face ahead of need.

#### Scenario: A claim page
- **WHEN** a reader opens a claim page
- **THEN** the title and the section headings are in the heading face, the status label is in the page's face, and no font is fetched from another site

#### Scenario: A long headline
- **WHEN** a claim's headline is longer than 110 characters and the page is 1400 pixels wide
- **THEN** the title is set at the smallest of its three sizes and stays beside the status card

### Requirement: A claim's band names its topic as a path and carries the summary
On a claim page the band SHALL show the topic as a path of two links, the topics and the claim's topic, ahead of the title. From 40rem wide the band SHALL show the claim's summary under the title, held to five lines with a control to show the rest, and the sheet SHALL NOT show it. Below 40rem the sheet SHALL open with the summary and the band SHALL NOT show it. The summary SHALL never be drawn twice.

#### Scenario: Wide screen
- **WHEN** a claim page is read at 1400 pixels wide
- **THEN** the summary stands under the title in the band and the sheet starts with what follows it

#### Scenario: Phone
- **WHEN** the page is read at 375 pixels wide
- **THEN** the band holds the path, the title, the facts and the status card, and the summary is in the sheet

### Requirement: The status card's heading is in sight
The status card on a claim's band SHALL show its heading, "Where it stands", in sight as part of the card. Each record line in the card SHALL carry a mark beside its words; the mark SHALL NOT carry meaning the words do not.

#### Scenario: Reading the card
- **WHEN** a reader looks at the status card
- **THEN** "Where it stands" is readable on the card, above the status label
