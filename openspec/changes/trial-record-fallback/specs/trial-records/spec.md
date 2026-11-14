# Trial records

## Purpose

Let readers inspect publicly cited trial records on this site when the registry's browser interface is unavailable, without losing provenance or confusing a trial with a treatment recommendation.

## ADDED Requirements

### Requirement: Local alternative beside official records
ClinicalTrials.gov links in claim timelines and matched records SHALL retain their official destinations and offer a local readable alternative. Other sources SHALL be unchanged.

#### Scenario: Baxdrostat records
- **WHEN** the baxdrostat claim is displayed
- **THEN** each of its nine registry-link placements offers the corresponding local trial page, covering three distinct records

### Requirement: Readable registry details
A local trial page SHALL show the registry identifier, title, available summary, study status, phase, conditions, interventions, sponsor, enrolment and study dates. It SHALL label missing fields honestly, distinguish estimated dates, link to the official record and citing claims, and preserve the site's notices and reading layout.

#### Scenario: Record has partial fields
- **WHEN** the registry omits enrolment or supplies only a month for a date
- **THEN** the page neither invents enrolment nor a day of the month

### Requirement: Cookie-independent delivery
The local page SHALL deliver readable HTML without client-side registry requests, registry cookies or JavaScript. The server SHALL use the public API with a configured contact identity and SHALL NOT forward reader cookies or credentials. It SHALL make no model calls.

#### Scenario: Safari has no registry session
- **WHEN** a reader opens the local page in Safari without ClinicalTrials.gov cookies
- **THEN** the study details are readable and the browser sends no request to ClinicalTrials.gov

### Requirement: Provenance and one day of reuse
The page SHALL identify ClinicalTrials.gov as the source, describe its fields as a formatted selection, and show retrieval and registry-update dates separately. A record read within the last 24 hours SHALL be reused with its original retrieval date. A record older than that SHALL NOT be shown: the registry SHALL be read again, and when it cannot be read the page SHALL show an unavailable state with the official record's link and a way to try again. No older copy is shown in place of a live read.

#### Scenario: Record read today
- **WHEN** a validated record was read three hours ago
- **THEN** the reader sees it with its retrieval date and the registry is not asked again

#### Scenario: Registry unavailable
- **WHEN** the registry is unavailable and the only saved record is two days old
- **THEN** the page shows an unavailable state with the official link, and the old record is not shown

### Requirement: Safe and bounded record access
Only well-formed ClinicalTrials.gov identifiers cited by the published export SHALL be fetched. Returned and cached identifiers MUST match the requested record. External text SHALL be rendered safely. Upstream reads SHALL have a finite timeout and a dedicated request limit. Errors SHALL not expose internal exception details.

#### Scenario: Unknown or malformed identifier
- **WHEN** a request names an uncited record or malformed identifier
- **THEN** the site returns a not-found page without an upstream request

#### Scenario: Wrong record returned
- **WHEN** the registry returns a different trial identifier
- **THEN** the response is rejected and never cached or presented as the requested trial

### Requirement: Useful unavailable states
A missing registry record SHALL produce a 404. A temporary failure without usable cached data SHALL produce a 503 with a retry link, the official source link and a path back to citing claims. Error pages SHALL not be cached as successful records.

#### Scenario: Registry unavailable
- **WHEN** the registry times out and no usable cached record exists
- **THEN** the reader sees a plain explanation and recovery links, without an empty study page
