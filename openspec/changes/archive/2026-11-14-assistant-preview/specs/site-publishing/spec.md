# Spec Delta

## ADDED Requirements

### Requirement: Every claim says whether a person checked it
Every exported claim SHALL state whether a person checked it. A claim SHALL count as checked only when a person approved it and no decision made by the assistant still stands on the claim, on one of its matches or on one of its events. A claim approved by rule, loaded from a seed file or decided by the assistant SHALL state that no person checked it, and SHALL be published like any other approved claim. The pipeline SHALL NOT write an export that calls itself a preview.

#### Scenario: Claim approved by the assistant
- **WHEN** a claim was approved by the assistant and the export is written
- **THEN** the export contains the claim, says no person checked it, and does not call itself a preview

#### Scenario: Operator's claim with an assistant's event
- **WHEN** an operator-approved claim has an event approved by the assistant
- **THEN** the export says no person checked the claim until the operator decides that event

#### Scenario: Operator takes over every decision
- **WHEN** the operator repeats, without the assistant flag, each decision the assistant made on a claim
- **THEN** the export says a person checked the claim

### Requirement: Unchecked claims are marked
A claim page, and the extension's view of a claim, SHALL say when no person has checked the claim, and SHALL say nothing of the kind for a claim a person checked. A site built from an older export that calls itself a preview SHALL show on every page that it is a preview and not for publication, and SHALL ask search engines not to index any page.

#### Scenario: Unchecked claim page
- **WHEN** a reader opens the page of a claim no person checked
- **THEN** the page says it has not yet been checked by a person

#### Scenario: Checked claim in the extension
- **WHEN** the extension shows a claim a person checked
- **THEN** it carries no unchecked note

#### Scenario: Older preview export
- **WHEN** the site is built from an export that calls itself a preview
- **THEN** every page carries the preview note and a noindex tag
