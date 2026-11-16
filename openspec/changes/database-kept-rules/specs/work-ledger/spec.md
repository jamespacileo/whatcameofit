# Work ledger: changes

## ADDED Requirements

### Requirement: Records a step wants first
A step MAY name a condition for the records it wants before every other. A run SHALL take the due records that meet it first and fill what is left of a pick with the other due records. Once fewer of them are due than a pick asks for, the run SHALL stop asking for them: a record that meets the condition later in the same run takes its turn among the rest. The condition SHALL change only when a record is processed, never whether.

#### Scenario: A topic lead among older leads
- **WHEN** twenty-five older leads and one newer lead that names a topic are due, and a pick takes twenty
- **THEN** the lead that names a topic is in the first pick

#### Scenario: Fewer topic leads than a call takes
- **WHEN** twenty-five older leads and two that name a topic are due, and a pick takes twenty
- **THEN** the first pick holds both topic leads and the eighteen oldest of the rest, the second holds the other seven, and each lead is processed once
