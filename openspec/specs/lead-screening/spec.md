# lead-screening Specification

## Purpose
Decides by rule, from stored data alone, whether a link lead goes on to triage, and records which claims, registry trials and article leads the database already holds for it, so that later steps spend nothing on what is already known.

## Requirements

### Requirement: A lead is screened again when its outlet's listing changes
The kind of a lead's outlet, as the checked-in list gives it, SHALL be part of what screening reads from the lead. A lead whose outlet is added to the list, removed from it or moved to another kind SHALL be due for screening again, and no other lead SHALL be. A lead that screening then finds in scope SHALL be due for triage as any lead is.

#### Scenario: An outlet is added to the list
- **WHEN** an outlet with 434 leads screened as unlisted is added to the list
- **THEN** those 434 leads are due for screening, and after it they are in scope and due for triage

#### Scenario: The list did not change for an outlet
- **WHEN** the list changes for one outlet
- **THEN** the leads of every other outlet keep their screening and are not due

#### Scenario: Bounded rescreening reaches the last lead

- **WHEN** three previously screened leads share a reclassified outlet and each ordinary run is limited to two
- **THEN** the first two are screened once and the next run reaches the third. A further unchanged run has none of the three due

#### Scenario: Planning sees the same newly eligible leads as screening

- **WHEN** the operator plans screening immediately after an outlet changes classification with three affected leads
- **THEN** the plan reports three eligible records without modifying them, matching the ensuing screening run

### Requirement: Screening uses stored data only
The screening step SHALL send no request and make no model call. Its result for a lead SHALL be one outcome, with any links to stored records, saved together with its ledger entry.

#### Scenario: Screening a million leads
- **WHEN** the screening step runs over every loaded lead
- **THEN** no request is sent, no model is called and no spend is recorded

### Requirement: Outlet rule
A lead SHALL go on only when its outlet kind is general news, health or clinical trade press, or press release. A lead whose outlet is on no list SHALL get the outcome unlisted outlet, SHALL be kept, and SHALL go no further. No model decides an outlet's kind.

#### Scenario: A link to a listed outlet
- **WHEN** a lead's address is on an outlet listed as general news
- **THEN** its outcome is in scope

#### Scenario: A link to a code repository
- **WHEN** a lead's address is on a domain that is on no list
- **THEN** its outcome is unlisted outlet, and it is never scored or read

#### Scenario: A domain is added to the list
- **WHEN** a domain is added to the outlet list and screening runs again
- **THEN** the leads on that domain become in scope, and no other lead's outcome changes

### Requirement: Articles already tracked
A lead whose address is the address of a source article SHALL get the outcome already tracked, with a link to that claim. It SHALL never be scored or read.

#### Scenario: A shared article that a claim already has
- **WHEN** a lead's address equals the address of a claim's source article, compared as the site compares addresses
- **THEN** its outcome is already tracked and it is linked to that claim

### Requirement: Links to stored records
For a lead in scope, screening SHALL record a link, with the reason found, to each of:

- a registry trial for which an article lead with the same address is stored;
- a claim whose intervention's name or other name appears in the lead's title;
- a registry trial whose search name appears in the lead's title together with a word of its indication that is not also a word of the name.

#### Scenario: An address the news search already found
- **WHEN** a lead's address is stored as an article lead for a registry trial
- **THEN** the lead is linked to that trial with the reason that the news search found the address for it

#### Scenario: A title that names a tracked intervention
- **WHEN** a lead's title holds the name of a claim's intervention
- **THEN** the lead is linked to that claim with the reason that its title names the intervention

### Requirement: A link is a candidate
A name SHALL match a title only as whole words. At most the configured number of links SHALL be kept for one lead. A link SHALL approve nothing and SHALL change no claim, match or status.

#### Scenario: A name inside a longer word
- **WHEN** a trial's search name is "Iron" and a lead's title holds "Ironman" and no other use of the name
- **THEN** no link is recorded

#### Scenario: A name that is also the indication
- **WHEN** a trial's search name is "Diphtheria", its indication is diphtheria, and a lead's title reports an outbreak of diphtheria
- **THEN** the lead is not linked to that trial

#### Scenario: A common name without the indication
- **WHEN** a lead's title holds a trial's search name and no word of that trial's indication
- **THEN** the lead is not linked to that trial

### Requirement: Screening report
`thenwhat backfill links` SHALL report, by platform and community, how many leads were loaded, how many are in scope by outlet kind, how many are already tracked, how many are linked to a claim and how many to a registry trial. It SHALL list the unlisted domains with the most leads.

#### Scenario: After a load and a screening run
- **WHEN** 50,000 leads are loaded and screened
- **THEN** the report gives the counts for each platform and community, and the twenty unlisted domains with the most leads

#### Scenario: Nothing screened yet
- **WHEN** no lead has been screened
- **THEN** the report says so and gives no percentages
