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
Where a claim page offers to follow, it SHALL say in sight, beside a Follow control placed after the status, what following does and that the list is kept in the reader's browser only. Once the reader follows, the same place SHALL say so and SHALL link to the list on the home page. Every Follow control on the page SHALL show the same state.

#### Scenario: Following from a claim page
- **WHEN** a reader presses Follow under the status
- **THEN** every Follow control reads "Following", and the sentence beside it says the claim is listed on the home page, with a link there

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
