# Spec Delta

## MODIFIED Requirements

### Requirement: Registry trial record
A registry trial SHALL be stored once per registry and registry identifier, with its title, conditions, interventions with their types and other names, phases, overall status, start date, lead sponsor class, the raw payload as the registry returned it, the time it was fetched, and the coded terms worked out from that payload by rule (`identity-records`). A claim's match of a registry trial SHALL point to the stored trial when the trial is stored, as well as naming it by registry and identifier.

#### Scenario: A trial is loaded
- **WHEN** a trial is loaded from the registry
- **THEN** it is stored with its identifier, the fields above, its raw payload, its fetch time and its coded terms

#### Scenario: A trial is loaded again
- **WHEN** a trial already stored is loaded again
- **THEN** its record is updated in place and no second record is created

#### Scenario: A claim matches a stored trial
- **WHEN** preparation stores a candidate match for a trial that is in the stored corpus
- **THEN** the match points to that stored trial

#### Scenario: A claim matches a trial not yet stored
- **WHEN** preparation stores a candidate match for a trial that is not in the stored corpus
- **THEN** the match names the trial by registry and identifier, and points to the stored trial once a load stores it
