# article-leads Specification

## Purpose
Records news articles that a search found for a registry trial's intervention and indication, as unreviewed leads kept apart from source articles, claims and evidence.

## Requirements

### Requirement: News search step
The news search step SHALL apply to registry trials that name an intervention and a condition. For each, it SHALL ask the news index for articles that name the intervention and the indication, and store what it finds as article leads.

#### Scenario: A trial with coverage
- **WHEN** the step runs for a trial whose intervention and indication appear in indexed news articles
- **THEN** an article lead is stored for each article found, up to the configured number per trial, and the ledger entry's outcome is done

#### Scenario: A trial with no coverage
- **WHEN** the news index returns no article for a trial
- **THEN** no lead is stored and the ledger entry's outcome is nothing found

### Requirement: Intervention name used for the search
The step SHALL search by the name of the intervention under test, without dose, form or route, and SHALL NOT search by a placebo, a comparator or a description that is not a name.

#### Scenario: Dose and form in the registry name
- **WHEN** a trial lists its intervention as a name followed by a dose and a form
- **THEN** the search uses the name alone

#### Scenario: Only a placebo or a description
- **WHEN** a trial's interventions are a placebo and a description that is not a name
- **THEN** the trial is out of the step's scope and no request is sent for it

### Requirement: Article lead record
An article lead SHALL store the article's address, outlet, title and the date the index gives, the registry trial it was found for, the search that found it, the raw result as the index returned it, and the fetch time. It SHALL be stored once per trial and address.

#### Scenario: The same article found twice
- **WHEN** a later search for the same trial returns an article already stored as a lead
- **THEN** no second lead is created

#### Scenario: One article, two trials
- **WHEN** the same article is found for two trials
- **THEN** each trial has its own lead with that address

### Requirement: No article text
An article lead SHALL NOT hold the article's text, an excerpt, or a summary supplied by the index. Any such field in the index's result SHALL be removed before the raw result is stored, logged or written to a fixture.

#### Scenario: The index returns an excerpt
- **WHEN** the index's result for an article includes an excerpt of its text
- **THEN** the stored raw result does not contain the excerpt

### Requirement: Outlet kind
Each lead SHALL carry the kind of its outlet: general news, health or clinical trade press, press release, or unknown. The kind SHALL be set by rule from the outlet's domain, and no model decides it.

#### Scenario: A newswire copy
- **WHEN** a lead's address is on a press release wire
- **THEN** its outlet kind is press release

#### Scenario: An outlet not yet listed
- **WHEN** a lead's outlet is on no list
- **THEN** its outlet kind is unknown

### Requirement: Leads are not published
An article lead SHALL NOT be a source article, SHALL NOT create or change a claim, a match, an evidence event or a status, and SHALL NOT appear in the export or on the site.

#### Scenario: Export after a search
- **WHEN** the news search stores leads for 1,000 trials and the export is produced
- **THEN** the export is identical to the one produced before the search

### Requirement: Hit rate report
`thenwhat backfill leads` SHALL report, for the trials the step has processed, how many have at least one lead, and how many have at least one lead of each outlet kind, as counts and percentages.

#### Scenario: After a sample run
- **WHEN** the step has processed 200 trials and 60 of them have a lead
- **THEN** the report shows 60 of 200 (30%) with a lead, and the same split by outlet kind
