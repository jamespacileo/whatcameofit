# Spec Delta

## ADDED Requirements

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
