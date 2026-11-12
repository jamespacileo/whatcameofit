# site-publishing Specification

## Purpose
Publishes reviewed claims as a static public site on which every status is shown with the sourced evidence that produced it.

## Requirements

### Requirement: Publication gate
The export that feeds the site SHALL contain only approved claims and, for each of them, only approved evidence events. Pending and rejected items SHALL NOT appear in the export in any form.

#### Scenario: Claim with mixed events
- **WHEN** an approved claim has three approved events and two pending events
- **THEN** the export contains the claim with three events

#### Scenario: Draft claim
- **WHEN** a claim is still a pending draft
- **THEN** the export does not contain it

### Requirement: Build from the export alone
The site SHALL be built from the export only, with no access to the database or to external services.

#### Scenario: Offline build
- **WHEN** the site is built on a machine that has the export and no network or database
- **THEN** the build succeeds

### Requirement: Claim page
Each published claim SHALL have a page at `/{slug}` that shows its headline, summary, status with any no-signal overlay, date first reported, promises next to what actually happened, and its evidence events. Each event SHALL show its date, summary and a link to its source.

#### Scenario: Reader opens a claim
- **WHEN** a reader opens the page of a claim with four approved events
- **THEN** the page shows the status and four dated events, each linking to its source

#### Scenario: Unknown slug
- **WHEN** a reader opens a slug that no published claim has
- **THEN** a not-found page is shown

### Requirement: Status explanation on the page
A claim page SHALL identify the evidence events that produced the current status.

#### Scenario: Status produced by one trial
- **WHEN** a claim's status is Phase 2 because of one trial
- **THEN** the page marks that trial's events as the reason for the status

### Requirement: Source articles are linked, not reproduced
A claim page SHALL list its source articles by outlet, title and date with a link to each. The site SHALL NOT display article text.

#### Scenario: Claim with two articles
- **WHEN** a claim has two source articles
- **THEN** the page lists both with links and shows no text from either

### Requirement: Topic index
Each vertical SHALL have an index page at `/topic/{vertical}` that lists its published claims with their statuses.

#### Scenario: Vertical with claims
- **WHEN** a reader opens the index of a vertical that has 30 published claims
- **THEN** 30 claims are listed with their statuses

### Requirement: Home page
The home page SHALL offer a search over published claims and SHALL list the claims whose status changed most recently.

#### Scenario: Search by intervention name
- **WHEN** a reader searches for a synonym of an intervention
- **THEN** the claim for that intervention is among the results

#### Scenario: Search with no result
- **WHEN** a reader searches for a term that matches no claim
- **THEN** the reader is told nothing was found

### Requirement: Approved claims page
The page at `/it-happened` SHALL list every published claim whose status is approved.

#### Scenario: No approved claims
- **WHEN** no published claim has the status approved
- **THEN** the page says that no tracked claim has reached approval yet

### Requirement: Status card image
Each published claim SHALL have a status card image that shows its headline, date first reported, latest promise as a date, and current status. The image SHALL be the claim page's link preview image and SHALL NOT show a count of days.

#### Scenario: Claim promised for 2025
- **WHEN** a claim's latest promise has the parsed date 31 December 2025
- **THEN** the card reads "promised by 2025" and shows no day count

#### Scenario: Claim with no promise
- **WHEN** a claim has no promises
- **THEN** the card omits the promise line

### Requirement: Footer notices
Every page SHALL carry a footer stating that the site gives no medical advice, that a registered trial is not a treatment option, which data sources are used, and when the data was last checked.

#### Scenario: Any page
- **WHEN** a reader opens any page of the site
- **THEN** the footer shows the two notices, the data sources and the last-checked date

### Requirement: Neutral wording
Status labels and overlay text SHALL describe evidence only. The site SHALL NOT describe a claim as dead, abandoned, a scam or any similar verdict.

#### Scenario: Long-quiet claim
- **WHEN** a preclinical-only claim has had no evidence event for six years
- **THEN** the page reads "no signal for 6 years" and uses no verdict wording

### Requirement: A page explains the method
The site SHALL have one page that explains, in plain words, how a claim's status is derived from approved evidence events by fixed rules, that no model and no editor decides a status, what each status means, what the no-signal note does and does not mean, what the site never says (verdicts, medical advice, that a registered trial is a treatment option), where the data comes from, and how to report an error. Every claim page SHALL link to it. The wording of each status's meaning SHALL be the same wording the claim pages use.

#### Scenario: Reader doubts a status
- **WHEN** a reader follows the method link from a claim page
- **THEN** they can read how that status is derived and what it does not mean

#### Scenario: Wording stays in step
- **WHEN** the wording of a status's meaning is changed
- **THEN** the method page and the claim pages show the new wording from the same source

### Requirement: A page for each year
For each year in which at least one published claim was first reported, the site SHALL have a page listing every published claim first reported in that year with its current status, and showing how those claims are spread across statuses. The page SHALL state counts only and SHALL NOT rank, grade or characterise the year, the claims or the outlets. A year with no published claim SHALL have no page and SHALL NOT be linked.

#### Scenario: Claims first reported in 2021
- **WHEN** three published claims were first reported in 2021
- **THEN** the page for 2021 lists the three with their current statuses and the number at each status

#### Scenario: A year with nothing
- **WHEN** no published claim was first reported in 2020
- **THEN** the site has no page for 2020 and no link to one

### Requirement: Pages can be found and cited
Every public page SHALL state its canonical address, built from the site's configured public address. Every claim page SHALL carry structured data that names the page, the date the claim was first reported, the date the registries were last checked and the site as publisher. The site SHALL NOT use fact-check, review or rating markup, because each states a verdict. The site SHALL publish a sitemap listing every public page except embed pages. A preview build SHALL ask search engines not to index any page and SHALL publish no sitemap.

#### Scenario: Claim page read by a search engine
- **WHEN** a search engine reads a claim page of a public build
- **THEN** it finds the canonical address, the first-reported and last-checked dates, and no rating or review markup

#### Scenario: Preview build
- **WHEN** the site is built as a preview
- **THEN** every page asks not to be indexed and no sitemap is published

#### Scenario: Public address not configured
- **WHEN** a public build is made while the configured address is a local one
- **THEN** the build stops and says that the public address must be set

### Requirement: Approach on the claim page
A claim page SHALL show the label of the claim's approach when it has one, in the site's own wording, and SHALL show nothing in its place when it has none. The label SHALL describe the kind of intervention only, and SHALL NOT suggest that the intervention works or is available.

#### Scenario: Claim with an approach
- **WHEN** a reader opens a claim whose approach is gene therapy
- **THEN** the page shows the label for gene therapy

#### Scenario: Claim without an approach
- **WHEN** a reader opens a claim with no approach
- **THEN** the page shows no approach label and no placeholder

#### Scenario: Approach code without site wording
- **WHEN** the export carries an approach code that the site has no label for
- **THEN** the site build fails and names the code

### Requirement: Topics page lists every group with claims
The topics page SHALL list each group that has at least one published claim, with that group's verticals that have published claims under it. A group or vertical with no published claim SHALL NOT be listed.

#### Scenario: Group with one listed vertical
- **WHEN** the group "Kidneys and bladder" has one published claim, filed under its general vertical
- **THEN** the topics page lists "Kidneys and bladder" with that one vertical

#### Scenario: Empty group
- **WHEN** no published claim is filed under "Pregnancy and fertility"
- **THEN** the topics page does not list that group

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
