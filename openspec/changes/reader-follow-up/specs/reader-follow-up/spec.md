# Spec Delta

## Purpose

Lets a reader come back to a claim at the right moment and learn when its status changes, without the site learning anything about the reader.

## ADDED Requirements

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

#### Scenario: Claim with one status so far
- **WHEN** a published claim has had one status only
- **THEN** its own feed has one entry for that first status

### Requirement: The privacy page says what the extension keeps
The privacy page SHALL say that followed claims, reminders and the recently checked list are kept in the reader's browser, are never sent to the site, and can be cleared from the extension.

#### Scenario: Reader asks what is kept
- **WHEN** a reader opens the privacy page
- **THEN** they can read what the extension keeps, that it stays in their browser, and how to clear it
