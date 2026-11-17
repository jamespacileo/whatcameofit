# Spec Delta

## MODIFIED Requirements

### Requirement: Readable registry details
A local trial page SHALL show the registry identifier, title, the trial's state, phase, conditions, interventions, sponsor, enrolment and study dates. The state SHALL be one of not started, under way, completed, suspended, terminated, withdrawn or unknown, by the mapping `trial-facts` defines and in the site's fixed phrases; the registry's own status word SHALL NOT be shown where it says whether a trial is recruiting. The page SHALL label missing fields honestly, distinguish estimated dates, link to the official record and citing claims, and preserve the site's notices and reading layout. The page of a trial a published claim cites SHALL also show the record's summary, and SHALL lead with the claims citing it, above the trial's facts. The page of a trial no claim cites is the plain page `trial-pages` defines and shows no summary.

#### Scenario: Record has partial fields
- **WHEN** the registry omits enrolment or supplies only a month for a date
- **THEN** the page neither invents enrolment nor a day of the month

#### Scenario: A recruiting trial
- **WHEN** the registry gives a trial's overall status as recruiting
- **THEN** the page shows the state as under way and the word "recruiting" is not on the page

### Requirement: Provenance and one day of reuse
The page SHALL identify ClinicalTrials.gov as the source, describe its fields as a formatted selection, and show retrieval and registry-update dates separately. While trial pages are answered by reading the registry, a record read within the last 24 hours SHALL be reused with its original retrieval date; a record older than that SHALL NOT be shown: the registry SHALL be read again, and when it cannot be read the page SHALL show an unavailable state with the official record's link and a way to try again. Once trial pages are answered from the store, a stored record SHALL be shown with the date it was read and the date the registry was last checked for changes, as long as the last completed change load is no older than the configured age; when it is older, the page SHALL be answered by reading the registry as above. No record older than these rules allow is shown in place of a current one.

#### Scenario: Record read today
- **WHEN** a validated record was read three hours ago
- **THEN** the reader sees it with its retrieval date and the registry is not asked again

#### Scenario: Registry unavailable
- **WHEN** the registry is unavailable and the only saved record is two days old
- **THEN** the page shows an unavailable state with the official link, and the old record is not shown

#### Scenario: A stored record, checked yesterday
- **WHEN** pages are answered from the store, a trial's record was read in March, and the change load last completed yesterday
- **THEN** the page shows the record with its March read date and yesterday's date as when the registry was last checked, and the registry is not asked

#### Scenario: The change load has not run for a week
- **WHEN** pages are answered from the store and the change load last completed seven days ago, past the configured age
- **THEN** the page is answered by reading the registry, and shows an unavailable state when it cannot be read

### Requirement: Safe and bounded record access
Only well-formed ClinicalTrials.gov identifiers that the published export cites or the site's trial listing holds SHALL be answered. While trial pages are answered by reading the registry, an identifier in neither SHALL get a not-found page without an upstream request, and the trial listing SHALL count for this only when the setting that opens uncited trial pages is on. The operator turned it on on 2026-11-17: it is on unless a build is given `LISTED_TRIAL_PAGES=0`, and a build with no trial listing beside its export opens no uncited trial page either way. The Worker SHALL check an identifier against the listing's identifiers alone, a file of the numbers built with the site, and SHALL NOT read the listing itself to answer a page. Once trial pages are answered from the store, an identifier of any stored trial SHALL be answered from the stored record with no upstream request. Returned and cached identifiers MUST match the requested record. External text SHALL be rendered safely. Upstream reads SHALL have a finite timeout and a dedicated request limit. Errors SHALL not expose internal exception details.

#### Scenario: Unknown or malformed identifier
- **WHEN** a request names a malformed identifier, or one that is neither cited nor listed
- **THEN** the site returns a not-found page without an upstream request

#### Scenario: Wrong record returned
- **WHEN** the registry returns a different trial identifier
- **THEN** the response is rejected and never cached or presented as the requested trial

#### Scenario: A listed trial while the setting is off
- **WHEN** a request names a trial that the listing holds and no claim cites, and uncited trial pages are not opened
- **THEN** the site returns a not-found page without an upstream request

#### Scenario: A listed trial while the setting is on
- **WHEN** a request names a trial that the listing holds and no claim cites, and uncited trial pages are opened
- **THEN** the trial's page is shown, marked not to be indexed, and reads that no news report is linked yet

#### Scenario: Any stored trial, answered from the store
- **WHEN** trial pages are answered from the store and a request names a stored trial outside every listing
- **THEN** the page is shown from the stored record and the registry is not asked

## ADDED Requirements

### Requirement: No person of a registry record is saved or shown
The site's Worker SHALL remove every person from a registry record before the record is saved, shown, compared or sent to a model: central contacts, overall officials, each site's contacts, the responsible party's investigator name, title and affiliation, the name of a lead sponsor who is a person (classed as an individual by the registry, or a sponsor-investigator), the name of a collaborator classed as an individual, the results' point of contact, and every email address and phone number. The rule SHALL be the pipeline's. A trial page SHALL ask the registry only for the fields it shows. A saved copy made before this rule, or one that names a person, SHALL NOT be shown: the registry SHALL be read again and the copy replaced. What says that a sponsor is a person (the class, the responsible party's type) and where a site is (facility, city, country) are not people and MAY be kept.

#### Scenario: A record that names people
- **WHEN** the registry answers a trial page's read with a record holding contacts, officials, site contacts, an investigator and a person as sponsor
- **THEN** neither the page nor the saved copy holds any of their names, email addresses or phone numbers

#### Scenario: A copy saved before people were removed
- **WHEN** a trial page is opened and the saved copy is the registry's whole record
- **THEN** the copy is not shown, the registry is read again, and the saved copy is replaced by one without people

#### Scenario: A search answered for a lookup
- **WHEN** a lookup's registry search returns a trial whose lead sponsor is a person
- **THEN** the answer kept for reuse and the record handed to the lookup do not hold that sponsor's name

