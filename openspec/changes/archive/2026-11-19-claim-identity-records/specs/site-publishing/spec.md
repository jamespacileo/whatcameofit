# Spec Delta

## ADDED Requirements

### Requirement: Each intervention has a page
Each shared intervention record with at least one published claim SHALL have a page at `/intervention/{slug}`. An intervention with no published claim SHALL have no page and no link SHALL lead to one.

#### Scenario: A drug with claims for two conditions
- **WHEN** an intervention record has published claims for two conditions
- **THEN** it has one page, and both claims link to it

#### Scenario: An intervention with no published claim
- **WHEN** an intervention record's only claim is awaiting audit
- **THEN** it has no page

### Requirement: What an intervention page shows
An intervention page SHALL show the intervention's name, its other names and development codes, its card as `knowledge-cards` makes it when it has one, and each of its published claims with its condition, its status and the number of its approved trials. It SHALL list the approved trials of those claims once each, with the condition each was approved for.

#### Scenario: Two claims share a trial
- **WHEN** one trial is approved for two claims of the same intervention
- **THEN** the trial is listed once, with both conditions

#### Scenario: A drug with no card
- **WHEN** the intervention has no approved term and no drug record
- **THEN** the page shows its names and claims and no card or placeholder

### Requirement: An intervention page gives no verdict or advice
An intervention page SHALL NOT say whether the intervention works, whether it is available, or who it is for, and SHALL NOT present a registered trial as an option for the reader. The build's wording check SHALL cover the page.

#### Scenario: A verdict word on the page
- **WHEN** an intervention page's wording holds a verdict word or a word that offers the treatment to a reader
- **THEN** the site build fails

### Requirement: A condition's page is its clinical category page
For each condition record that is a published claim's condition, the clinical category page of its descriptor SHALL be the condition's page. In addition to what the clinical category page shows, it SHALL show the condition's card as `knowledge-cards` makes it when it has one, and SHALL list the interventions with a published claim for exactly that condition, each linking to its intervention page with that claim's status. A condition SHALL NOT have a second page at another address.

#### Scenario: Three drugs for one condition
- **WHEN** three intervention records have published claims for the condition record for breast neoplasms
- **THEN** the page for that descriptor lists the three interventions, each with its claim's status and a link to its page

#### Scenario: A condition with no descriptor
- **WHEN** a published claim's condition has no condition record
- **THEN** the claim page links to no condition page

### Requirement: A claim page links to its intervention and condition
A claim page SHALL link its intervention's name to the intervention's page and its indication to its condition's page when the claim has a condition record.

#### Scenario: Claim with both records
- **WHEN** a reader opens a published claim that has an intervention record and a condition record
- **THEN** the intervention's name links to `/intervention/{slug}` and the indication links to `/clinical/{descriptor identifier}`

### Requirement: An intervention page keeps its address
An intervention page's slug SHALL be made once from the intervention's name and SHALL NOT change when the record gains a name, a key or a synonym. When two intervention records are merged, the slug of the one not kept SHALL lead to the page of the one kept. The sitemap SHALL list every intervention page.

#### Scenario: A drug gains a brand name
- **WHEN** an intervention record with the slug `lecanemab` gains a brand name as a synonym
- **THEN** its page stays at `/intervention/lecanemab`

#### Scenario: Two records merged
- **WHEN** two intervention records are found to be one treatment and merged
- **THEN** the merged record's old address leads to the kept record's page
