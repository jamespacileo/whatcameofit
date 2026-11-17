# Spec Delta

## ADDED Requirements

### Requirement: A lead is screened again when its outlet's listing changes
The kind of a lead's outlet, as the checked-in list gives it, SHALL be part of what screening reads from the lead. A lead whose outlet is added to the list, removed from it or moved to another kind SHALL be due for screening again, and no other lead SHALL be. A lead that screening then finds in scope SHALL be due for triage as any lead is.

#### Scenario: An outlet is added to the list
- **WHEN** an outlet with 434 leads screened as unlisted is added to the list
- **THEN** those 434 leads are due for screening, and after it they are in scope and due for triage

#### Scenario: The list did not change for an outlet
- **WHEN** the list changes for one outlet
- **THEN** the leads of every other outlet keep their screening and are not due
