# Spec Delta

## ADDED Requirements

### Requirement: A stored trial carries the registry's activity and results fields
A registry trial SHALL be stored with, besides its listing fields, what the registry states of its activity and results: the date its record was last updated, its primary completion date and completion date with whether each is actual or anticipated, the date results were first posted, whether results are posted, its acronym, the other names of each intervention, and the references and links the registry lists for it. Each SHALL be stored as the registry gives it; a field the registry leaves empty SHALL be stored as empty and never inferred.

#### Scenario: A trial with posted results
- **WHEN** the registry's record of a trial has results posted on a date
- **THEN** the stored trial carries that date and that results are posted

#### Scenario: A field the registry leaves empty
- **WHEN** the registry gives no completion date for a trial
- **THEN** the stored trial has none, and no date is derived from its state or its start date

### Requirement: Sets of trials named by activity and results
Two further sets SHALL be selectable from the stored trials, by rule and without asking any source. `active-since-2025`: trials in phase 2 or 3 whose state is recruiting, not yet recruiting, enrolling by invitation, or active and no longer recruiting, and whose record the registry last updated on or after 1 January 2025. `completed-with-results-since-2025`: trials whose state is completed, whose completion date is actual and on or after 1 January 2025, and whose results are posted. A set SHALL say only which trials are in it. Neither set's name, nor anything shown of a trial in it, SHALL word an outcome: a trial in the second set is completed with results posted, and nothing more is said of how it turned out.

#### Scenario: Counting the sets
- **WHEN** every trial has been loaded with the wider record
- **THEN** the number of trials in each set can be given from the stored trials alone, with the day they were loaded

#### Scenario: A completed trial without results
- **WHEN** a trial completed in 2026 has no results posted
- **THEN** it is in neither set

### Requirement: The wider record is loaded for every stored trial
After the wider record is introduced, every stored trial SHALL be loaded again in full, within the registry's allowance, so that no stored trial lacks the new fields because it was loaded before them. A trial whose listing fields did not change SHALL NOT become due for any step because of this reload.

#### Scenario: The reload
- **WHEN** all trials are loaded again with the wider record
- **THEN** each has the new fields as the registry gives them, and no step that searches or reads for a trial has more records due than before
