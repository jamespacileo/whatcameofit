# reader-follow-up Specification

## Purpose
How a reader follows a claim and is invited back when its record changes, with what the site keeps for this held only in the reader's own browser.

## Requirements

### Requirement: Follow a claim on the site
A claim page SHALL let a reader follow and stop following the claim, where the browser lets the page keep a list. The list SHALL hold, per claim, its headline, its status in words when the reader last opened its page, and the day they began following; it SHALL be kept in the reader's browser only and SHALL NOT be sent to the site. The home page SHALL list followed claims above its other lists, those whose status differs from the one kept first, each naming the earlier status and the status now. Opening a followed claim's page SHALL bring the kept status up to date. A followed claim the site no longer lists SHALL be named as no longer listed. The list SHALL end with "Kept in this browser only." and each row SHALL offer to stop following.

#### Scenario: A followed claim has changed status
- **WHEN** a reader follows a claim at "Phase 2 trial" and its status is now "Approved"
- **THEN** the home page lists it first with "Was: Phase 2 trial. Now: Approved."

#### Scenario: The reader sees the change
- **WHEN** the reader opens that claim's page and returns to the home page
- **THEN** the claim is listed with its status now and no note of a change

#### Scenario: Storage is refused
- **WHEN** the browser does not let the page keep anything
- **THEN** no Follow control is shown

### Requirement: The privacy page says what the site keeps in the browser
The privacy page SHALL say that the day of the last visit and the followed claims are kept in the reader's browser, are not sent to the site, and how to remove them.

#### Scenario: Reader checks what is kept
- **WHEN** a reader opens the privacy page
- **THEN** it names the last-visit day and the followed claims, and says they stay in the browser

### Requirement: Follow is explained and confirmed in sight
Where a claim page offers to follow, it SHALL say, beside the Follow control that stands with the page's reminders, what following does and that the list is kept in the reader's browser only. The page SHALL NOT repeat a Follow control with its words directly under the status, where the status's own Follow control already stands. Once the reader follows, the page SHALL say so in sight after the status, with a link to the list on the home page and that the list is kept in the reader's browser only, and the place beside the reminders SHALL say the same. Every Follow control on the page SHALL show the same state.

#### Scenario: Following from a claim page
- **WHEN** a reader presses Follow beside the status
- **THEN** every Follow control reads "Following", and a sentence after the status says the claim is listed on the home page, with a link there, and is kept in this browser only

#### Scenario: Before following
- **WHEN** a reader who does not follow the claim opens its page
- **THEN** the only Follow controls are the one beside the status and the one beside the reminders, and what following does is said beside the second

### Requirement: A change is said on the claim page
When a reader who follows a claim opens its page and its status differs from the one kept, the page SHALL say once, after the status, the earlier status and the status now, and SHALL then bring the kept status up to date.

#### Scenario: A followed claim has changed status
- **WHEN** a reader who followed a claim at "Phase 2 trial" opens its page and the status is "Approved"
- **THEN** the page reads "Changed. When you last looked: Phase 2 trial. Now: Approved."

### Requirement: The home page says how to keep up
Under its lists the home page SHALL link the feed of status changes by a plain name. To a reader who follows no claim, where the browser can keep a list, it SHALL say what following is, that the day of a visit is noted, and that both are kept in the browser only. The method page SHALL list the ways to keep up: following, the since line, reminders, feeds and showing a status on another page.

#### Scenario: Ways to keep up
- **WHEN** a reader opens the method page
- **THEN** it names each way to keep up and says none needs an account

### Requirement: Reminder as a calendar file
A claim page SHALL offer a calendar file for a moment the reader chooses from: the date the latest dated promise falls due (offered only when the claim has one), six months from today, one year from today, and the next anniversary of the first report. The file SHALL be made in the reader's browser, SHALL hold one event whose text names the claim and links to its page, and SHALL send nothing to the site.

#### Scenario: Claim with a dated promise
- **WHEN** the reader opens the reminder choices on a claim whose latest promise names a year
- **THEN** the first choice is the date that promise falls due, and choosing it saves a calendar file with one event on that date linking to the claim page

#### Scenario: Claim with no dated promise
- **WHEN** the reader opens the reminder choices on a claim with no dated promise
- **THEN** the promise choice is absent and the other three are offered

#### Scenario: Nothing is sent
- **WHEN** the reader saves a calendar file
- **THEN** no request leaves the browser

### Requirement: Reminder for a report with no record
When the home page's lookup answers a linked report the site does not track, it SHALL offer a calendar file for six months or one year from today. The event SHALL link to the report and say where to paste it to look again. The file SHALL be made in the reader's browser and SHALL send nothing to the site.

#### Scenario: Untracked report
- **WHEN** a reader looks up a link the site does not track and the answer arrives
- **THEN** "Check again later" offers six months and a year, and choosing one saves a file with one event linking to the report

#### Scenario: Tracked report
- **WHEN** the lookup finds the report already tracked
- **THEN** no reminder is offered beside the answer; the claim page offers its own

### Requirement: Reminder in the extension
The extension SHALL offer the same reminder choices for a claim it shows, SHALL keep the reminder in the browser, and SHALL show one notification when the moment comes. The notification SHALL name the claim and its current status label, and SHALL open the claim page when pressed.

#### Scenario: Reminder falls due
- **WHEN** a reminder's moment arrives
- **THEN** one notification names the claim and its status label as last fetched, and pressing it opens the claim page

#### Scenario: Reader removes a reminder
- **WHEN** the reader removes a reminder before it falls due
- **THEN** no notification is shown for it

### Requirement: Follow a claim
The extension SHALL let the reader follow and unfollow a published claim and SHALL keep the followed list in the browser only. When the lookup file gives a followed claim a status or place different from the one last seen, the popup SHALL say how many followed claims have changed and SHALL mark the claim as changed, naming the earlier status label and the new one, until the reader opens it.

#### Scenario: Followed claim changes status
- **WHEN** the reader opens the popup and a followed claim has moved from "Trial registered" to "Phase 1 trial"
- **THEN** the popup says one followed claim has changed, and the following list names the claim and both labels

#### Scenario: Followed claim is unchanged
- **WHEN** the reader opens the popup and no followed claim has changed
- **THEN** nothing is marked as changed

#### Scenario: Reader sees the change
- **WHEN** the reader opens a changed claim from the list, or opens the popup on one of its tracked reports
- **THEN** the change is shown once and the claim is no longer marked

### Requirement: Notification of a change
When a followed claim's status or place changes while the popup is closed, the extension SHALL show one notification naming the claim, the earlier status label and the new one.

#### Scenario: Change while the popup is closed
- **WHEN** the extension refreshes the lookup file in the background and a followed claim has changed
- **THEN** one notification names the claim and both labels

#### Scenario: Followed claim leaves the lookup file
- **WHEN** a followed claim is no longer in the lookup file
- **THEN** the popup says the claim is no longer published and offers to stop following it, and no status is shown

### Requirement: The reader's recently checked list
The extension SHALL keep, in the browser only, the ten pages the reader most recently checked: the page's title, the outlet's name, the date checked and the answer shown. An entry with one matching claim SHALL open that claim page, an entry with several SHALL open the list of candidates, and every entry SHALL offer to open the original page. The list SHALL have a control that clears it. An entry whose answer came from an automatic registry search SHALL stay marked as unreviewed.

#### Scenario: Entry with one claim
- **WHEN** the reader presses an entry whose check found one tracked claim
- **THEN** that claim page opens

#### Scenario: Entry with several candidates
- **WHEN** the reader presses an entry whose check found three candidates
- **THEN** the three candidates are listed, each with its own control

#### Scenario: Entry with no record
- **WHEN** the list shows an entry whose check found no record
- **THEN** the entry says so and leads to the original page, where the reader can check it again

#### Scenario: Reader clears the list
- **WHEN** the reader presses the clear control
- **THEN** the list is empty and nothing about earlier checks remains in the browser's storage

#### Scenario: Nothing leaves the browser
- **WHEN** the reader opens the list
- **THEN** no page address, title or outlet is sent anywhere

### Requirement: Status changes feed
The site SHALL publish a feed of status changes across all published claims and a feed for each claim. Each entry SHALL carry the claim's headline, the earlier and new status labels in the site's wording, the date of the evidence event that produced the change and a link to the claim page. An entry SHALL NOT carry verdict wording or advice.

#### Scenario: Claim reaches a new status
- **WHEN** a published claim's status changes in a new export
- **THEN** both feeds gain one entry dated by the evidence event, naming both labels and linking to the claim page

#### Scenario: Export made before the history existed
- **WHEN** the site is built from an export whose claims carry no status history
- **THEN** both feeds are valid and have no entries, and the claim page does not link to them

#### Scenario: Claim with one status so far
- **WHEN** a published claim has had one status only
- **THEN** its own feed has one entry for that first status

### Requirement: The privacy page says what the extension keeps
The privacy page SHALL say that followed claims, reminders and the recently checked list are kept in the reader's browser, are never sent to the site, and can be cleared from the extension.

#### Scenario: Reader asks what is kept
- **WHEN** a reader opens the privacy page
- **THEN** they can read what the extension keeps, that it stays in their browser, and how to clear it
