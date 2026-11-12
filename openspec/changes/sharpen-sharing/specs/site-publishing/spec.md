# Spec Delta

## ADDED Requirements

### Requirement: A tracked article is answered with its status
When a reader pastes the address of an article the site tracks, the home page SHALL show, for each claim the article reports, the status in words, its place on the path when the status is on the path, the no-signal note when it applies, what the status means, the date first reported, and a link to the claim's records. The status SHALL NOT be conveyed by the path alone. Close matches to an untracked article SHALL keep the plain list, so a guess never looks like an answer.

#### Scenario: Tracked article
- **WHEN** a reader pastes the address of an article reporting a claim whose status is a Phase 2 trial
- **THEN** the answer shows "Phase 2 trial", the fourth of six places marked, what that status means, and a link to the records

#### Scenario: Untracked article with close claims
- **WHEN** a reader pastes an address the site does not track and two tracked claims share words with it
- **THEN** the claims are listed as a guess, without the status panel

### Requirement: Approvals are counted, not characterised
The approved-claims page SHALL state how many tracked claims have an approval on record out of all tracked claims. Each year page SHALL state the same for the claims first reported in that year. The statement SHALL be a count and SHALL NOT carry an adjective, a percentage or a comparison.

#### Scenario: One approval among three claims
- **WHEN** three claims are published and one has an approval on record
- **THEN** the approved-claims page says "Approvals on record: 1 of 3 tracked claims."

### Requirement: A pasted address stays out of the page's address
The home page SHALL NOT write a pasted article address into its own address, so that reloading or sharing the page sends no article address to the site's host. Typed search words MAY be kept in the page's address.

#### Scenario: Reader pastes an article address
- **WHEN** a reader pastes an article's address into the main box and the answer is shown
- **THEN** the page's address carries no part of the pasted address

#### Scenario: Reader types search words
- **WHEN** a reader searches for "tooth"
- **THEN** the page's address carries the words, so the search can be reloaded

### Requirement: The promise is beside the status on the claim page
A claim page for a claim with a dated promise SHALL show the year promised by in the status panel, on the site's pale amber, linked to that year in the timetable. A claim with no dated promise SHALL show no such line.

#### Scenario: Claim with a dated promise
- **WHEN** a claim's latest promise names 2025
- **THEN** the status panel shows "Promised by 2025" and the year leads to the 2025 row
