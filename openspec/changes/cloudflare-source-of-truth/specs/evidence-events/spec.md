## MODIFIED Requirements

### Requirement: Event record
An evidence event SHALL have a type, an event date, a source name, a source URL, a summary, a confidence between 0 and 1, the raw payload it was built from, the time that payload was fetched, and a review state. The type SHALL be one of: follow-up paper, trial registered, trial status change, trial results posted, grant awarded, company event, retraction, regulatory decision. A payload that is a registry's record of a trial SHALL be kept without the people it names: its officials and contacts, each site's contacts, the investigator a responsible party is, a sponsor or collaborator who is a person, the results' point of contact, and every email address and telephone number. Nothing else SHALL be removed from it. A literature record's authors, its published byline, SHALL be kept. No stored record or payload SHALL hold a paper's abstract or body text, whichever table holds it (`docs/adr/0011`); its links SHALL be kept.

#### Scenario: Event without a source link
- **WHEN** an event is created without a source URL
- **THEN** the event is refused

#### Scenario: Event built from a registry record
- **WHEN** an event is created from a fetched trial record
- **THEN** the event stores that record's payload, without the people it names, and its fetch time

#### Scenario: A record that names people
- **WHEN** a fetched trial record names an official, a site's contact and a sponsor-investigator
- **THEN** the stored payload names none of them, and the trial's facts read from it are the same as from the record as fetched

#### Scenario: A follow-up paper's record
- **WHEN** a citing paper whose record carries its authors and its abstract is stored as a follow-up event
- **THEN** the event's payload keeps the authors and holds no abstract, and the paper's facts read from it are the same as from the record as fetched
