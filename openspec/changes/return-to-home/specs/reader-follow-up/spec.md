## ADDED Requirements

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
