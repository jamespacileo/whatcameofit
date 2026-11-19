# Spec Delta

## ADDED Requirements

### Requirement: Named sets of trials
A bulk load SHALL accept the name of a set of trials in place of a condition, and SHALL refuse a name it does not know, listing the sets it has. A condition and a set together SHALL be refused. The sets SHALL be: `phase-3`, drug or biological trials in phase 3; `active-phase-2-3`, drug or biological trials in phase 2 or 3 that are recruiting, not yet recruiting, enrolling by invitation, or active and no longer recruiting; and `interventional`, every interventional study the registry holds, of any phase, state and kind of intervention. Observational studies and expanded access records SHALL NOT be in any set. A set says only which trials are stored and nothing of how any of them turned out.

#### Scenario: Every trial the registry holds
- **WHEN** the operator loads the set `interventional`
- **THEN** the registry is asked for every interventional study, a page per request within its allowance, and each is stored once whether or not an earlier, narrower load already stored it

#### Scenario: A set the load does not know
- **WHEN** the operator asks for a set named `successful`
- **THEN** nothing is asked of the registry and the command lists the sets it has
