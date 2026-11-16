# Spec Delta

## MODIFIED Requirements

### Requirement: A reading is checked by rule before it is stored
A reading SHALL be stored only when its words appear, character for character, in the named field of the trial's stored record, its kind and value are in the fixed lists, and a number with a unit can be found in its words. A follow-up SHALL NOT turn an explicit offset after a numbered or final treatment cycle, a later dose/infusion/session, or treatment completion into a duration from the start. The check SHALL inspect the full time-frame field so a short quote cannot discard that anchor. A reading that fails any check SHALL NOT be stored, and the reason SHALL be recorded. The checks SHALL be pure: no database, network or clock. These explicit boundaries do not constitute a general time-frame parser.

#### Scenario: Words not in the record
- **WHEN** the model returns a reading whose words are not in the record's field
- **THEN** the reading is not stored and the refusal names the reason

#### Scenario: Number the words do not give
- **WHEN** the model returns 12 weeks for a time frame that reads "Baseline and week 4"
- **THEN** the reading is not stored

#### Scenario: Code outside the list
- **WHEN** the model returns a kind of measure that is not in the fixed list
- **THEN** the reading is not stored

#### Scenario: Offset after a later cycle
- **WHEN** the time frame says "within 6 days after 3rd cycle" and the proposed follow-up quotes only "within 6 days"
- **THEN** the six-day reading is refused with the reason `later_event_offset`
- **AND** no total is calculated from the cycle schedule

#### Scenario: First dose or surgery as the start
- **WHEN** the time frame gives a duration after the first dose or surgery
- **THEN** the later-event rule does not refuse that duration solely because it has an anchor

### Requirement: Readings are exported with their trial
The export SHALL carry each trial's stored readings that still pass the current pure checks and that the model gave at least `READING_ACCEPT_ABOVE` confidence (0.8 by default): kind, value, the field and words read, how sure the reading is, and the date the record was read. A reading that fails either gate SHALL NOT be exported, so the page and the data file give the registry's own words for that answer, with no looser reading in its place. A trial with no reading SHALL carry an empty list. The export SHALL be buildable with no network. Rechecking a stored reading SHALL NOT rewrite its provenance, ask a model or change the trial's facts or the claim's status.

#### Scenario: Trial with two readings
- **WHEN** a published claim's trial has a follow-up reading and a measure reading, both at or above the bar
- **THEN** the exported trial carries both, each with its words and how sure it is

#### Scenario: Reading below the bar
- **WHEN** a trial's follow-up reading was given 0.79 and its measure reading 0.9
- **THEN** the exported trial carries the measure reading only, and the page gives the registry's own time frame

#### Scenario: Export with no network
- **WHEN** the export is built on a machine with the database and no network
- **THEN** every stored reading at or above the bar that passes the current checks is present

#### Scenario: Older reading loses its later-cycle anchor
- **WHEN** an earlier read stored a six-day duration for an outcome assessed six days after the third cycle
- **THEN** export omits that duration and retains the full registry time frame
- **AND** the stored original reading remains unchanged and no model is asked
