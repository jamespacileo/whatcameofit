# Spec Delta

## ADDED Requirements

### Requirement: A claim page is titled by its intervention
The main heading of a claim page SHALL be the claim's intervention name. The claim's full headline SHALL appear directly under the heading.

#### Scenario: Page of a named intervention
- **WHEN** a reader opens the page of a claim whose intervention is "Trontinemab"
- **THEN** the page's main heading reads "Trontinemab" and the claim's full headline is shown under it

#### Scenario: Search result for a claim
- **WHEN** a reader searches the site by intervention name
- **THEN** the claim is found and its result is titled as it was before this requirement

### Requirement: Every claim page carries a provenance line
Every claim page SHALL show, in one line near its heading, that the page was put together from the public records it links to, whether a person has checked it, and the date the registries were last checked. The line SHALL have the same place and visual weight whether or not a person has checked the page.

#### Scenario: Claim no person has checked
- **WHEN** a reader opens a claim that is marked as not checked by a person
- **THEN** the provenance line says it has not yet been checked by a person and gives the date the registries were last checked

#### Scenario: Claim a person has checked
- **WHEN** a reader opens a claim that is marked as checked by a person
- **THEN** the provenance line says a person has checked it and gives the date the registries were last checked

#### Scenario: Export with no check date
- **WHEN** the export carries no date for the last registry check
- **THEN** the provenance line omits the date and still states the other two facts
