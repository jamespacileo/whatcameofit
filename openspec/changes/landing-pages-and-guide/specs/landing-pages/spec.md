## ADDED Requirements

### Requirement: A landing page claims nothing the site cannot show
A landing page SHALL show the site at work on published claims taken from the export when the page is built, with the month the registries were checked. It SHALL NOT show a testimonial, a rating, a count of readers or installs, an outlet's or organisation's mark as an endorsement, or a comparison with a named site. Every count on it SHALL be computed from the export. The footer notices and the rule against verdict wording SHALL apply as on every page.

#### Scenario: A count on the about page
- **WHEN** the export holds 84 published claims in 25 topics
- **THEN** the about page states those numbers, and states no number the export does not hold

#### Scenario: The example claim changes status
- **WHEN** the claim a landing page shows moves to a new status and the site is rebuilt
- **THEN** the landing page shows the new status and the new checked month

### Requirement: The extension has a page once it can be installed
When the address of at least one store listing is configured, the site SHALL publish `/extension` with a control that opens each configured store listing. With scripting on, the control for the reader's own browser SHALL come first. When no store address is configured the page SHALL NOT be built and nothing SHALL link to it.

#### Scenario: One store is configured
- **WHEN** only the Chrome listing's address is set
- **THEN** the page is published with one install control, and says the Safari version is not yet available

#### Scenario: No store is configured
- **WHEN** neither address is set
- **THEN** no extension page is built and the footer, home page and claim pages hold no link to one

### Requirement: The extension page shows the popup's answers from the export
The extension page SHALL draw the popup's answers in the page from a published claim's record: its status; the registry records matched to it, as an automatic search lists them; and its latest change of status, as the followed list shows one. An answer SHALL be drawn only when the export holds what it shows. The page SHALL say that the search answer is drawn with the example claim's records, and SHALL date the status answer by the day the registries were checked.

#### Scenario: A claim with matched trials and a change of status
- **WHEN** the example claim has matched trial records and its status has changed once
- **THEN** the page draws three answers, the third reading "Was: X. Now: Y." with the claim's own statuses

#### Scenario: A claim with neither
- **WHEN** the example claim has no matched trial record and no change of status
- **THEN** the page draws the status answer alone

### Requirement: The extension page says what leaves the browser
The extension page SHALL say, in a table, what the extension reads, what it sends, when, to whom, and what it keeps and for how long. An answer given inside the browser and an automatic search that sends page content SHALL be separate rows, the second naming every service that receives it and the setting that turns it off. The page SHALL link the privacy page and SHALL state nothing about data that the privacy page does not.

#### Scenario: A reviewed match
- **WHEN** a reader reads the table's row for an article the site tracks
- **THEN** it says the answer is found inside the browser and the page's address is not sent

#### Scenario: A reader checks before installing
- **WHEN** a reader opens the extension page
- **THEN** they can read, without leaving it, that opening the popup on an untracked page may send page content to the site's service and to OpenAI, and how to turn that off

### Requirement: The extension page names each permission
The extension page SHALL list every permission and every host in the extension's manifest, each with what it is used for in plain words, and SHALL list no other. A site test SHALL compare the list with the manifest.

#### Scenario: Permissions are listed
- **WHEN** the manifest asks for the active tab, scripting, storage, alarms and notifications, and for this site's host and `t.co`
- **THEN** the page lists those, each with its use, and lists no other

#### Scenario: The manifest gains a permission
- **WHEN** a permission is added to the manifest and not to the page
- **THEN** the site's tests fail

### Requirement: A page says why the site exists and who runs it
`/about` SHALL state the gap between a reported breakthrough and its follow-up with a linked source for the finding it cites, what the site does, what it does not do (advice, verdicts, grades, ranking of outlets), who operates it, and where its data and method can be checked. It SHALL show one published claim as a headline beside its status now. It SHALL end with the lookup. It SHALL NOT restate how a status is set; it SHALL link the method page.

#### Scenario: A first-time reader
- **WHEN** a reader opens the about page from a link in a forum
- **THEN** the first screen shows an outlet's headline in quotation marks with its year and the claim's status now, and the page ends with the box that looks up a headline

### Requirement: A page for each audience opens on its tool
The site SHALL publish a page for journalists, one for clinicians and one for researchers. Each SHALL place a working tool in its first screen and SHALL state the limits that matter to that reader. The journalists' page SHALL say that outlets are never ranked or compared.

#### Scenario: A clinician looks up a headline
- **WHEN** a clinician pastes an article's address into the clinicians' page and the article is tracked
- **THEN** the answer shows the status and the dated sentence to copy

#### Scenario: A researcher takes the data
- **WHEN** a researcher opens the researchers' page
- **THEN** the first screen holds the download of the published claims, its licence and the day it was built

#### Scenario: A journalist picks a claim
- **WHEN** a journalist searches for a treatment's name and picks a claim
- **THEN** the page shows that claim's status box at the size it embeds at and the snippet that places it

#### Scenario: A search with no result
- **WHEN** the search finds no claim
- **THEN** the page says so and offers to suggest a headline, where a suggestion address is configured

### Requirement: The new pages are linked from the footer
The footer SHALL link the guide and the about page, the extension page when it is published, and the three audience pages. When the extension page is published, the home page SHALL name it once in a closing section before the link to suggest a headline, and a claim page and a topic page SHALL each name it once in their last section.

#### Scenario: The extension is installable
- **WHEN** a store address is configured
- **THEN** the footer, a closing section of the home page, and the last section of a claim page and of a topic page each link the extension page
