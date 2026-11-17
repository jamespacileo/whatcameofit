# Spec Delta

## ADDED Requirements

### Requirement: An article lead is carried into the lead path once
Each stored article lead's address SHALL be stored as a link lead, once per address as the site compares addresses, with the reason that the news search returned it for its trial. The article lead SHALL be kept as it is. An address that is already a link lead SHALL gain the reason and no second record, and an address that is already a source article SHALL be counted as tracked and carried as nothing. Carrying SHALL send no request and call no model, and running it again SHALL add nothing.

#### Scenario: An article found for two trials
- **WHEN** two article leads hold one address, each for its own trial
- **THEN** one link lead holds the address with both reasons

#### Scenario: Carried twice
- **WHEN** the carry is run a second time with no new article lead
- **THEN** no link lead is added

### Requirement: A carried lead is read only as any lead is
A link lead carried from an article lead SHALL go through screening, triage, the page reader, the same-claim decision, drafting or joining, `thenwhat prepare --pending` and the audit hold by the same rules as any link lead, and SHALL be read only when triage passed it or held it. The trial it was found for SHALL be handed to preparation as a candidate and SHALL NOT be approved for having led to it.

#### Scenario: Export after the carry
- **WHEN** every article lead has been carried and nothing has been read
- **THEN** the export is identical to the one produced before
