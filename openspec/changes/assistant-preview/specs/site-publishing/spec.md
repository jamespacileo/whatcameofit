# Spec Delta

## ADDED Requirements

### Requirement: Assistant-decided claims stay out of the export
The export SHALL leave out every claim on which a decision made by the assistant still stands, whether on the claim, on one of its matches or on one of its events. A preview export, asked for explicitly, SHALL include those claims and SHALL state that it is a preview. Every exported claim SHALL state whether a person checked it; a claim loaded from a seed file or decided by the assistant SHALL state that no person did.

#### Scenario: Claim approved by the assistant
- **WHEN** a claim was approved by the assistant and a normal export is written
- **THEN** the export does not contain the claim and does not call itself a preview

#### Scenario: Preview export
- **WHEN** the same claim is exported with a preview asked for
- **THEN** the export contains the claim, says no person checked it, and calls itself a preview

#### Scenario: Operator's claim with an assistant's event
- **WHEN** an operator-approved claim has an event approved by the assistant
- **THEN** a normal export leaves the claim out until the operator decides that event

### Requirement: Preview builds are marked
A site built from a preview export SHALL show on every page that it is a preview and not for publication, and SHALL ask search engines not to index it. A claim page, and the extension's view of a claim, SHALL say when no person has checked the claim. A normal build SHALL show none of this for claims a person checked.

#### Scenario: Preview build
- **WHEN** the site is built from a preview export
- **THEN** every page carries the preview band and a noindex tag, and each unchecked claim page carries the unchecked note
