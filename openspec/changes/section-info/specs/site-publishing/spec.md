# Spec Delta

## ADDED Requirements

### Requirement: A section may say what it holds from an info mark beside its heading
A section of a claim page MAY carry an info mark beside its heading in place of an opening paragraph. The mark SHALL open the section's note in a panel on hover with a pointer, on a press and from the keyboard, and the panel SHALL close on Escape. The mark SHALL be named after its section for a screen reader. On paper the note SHALL be printed whole under its heading. A note that says the page is not advice SHALL NOT be moved into a panel.

#### Scenario: Reading a section
- **WHEN** a reader looks at "Trials on record"
- **THEN** the heading is followed by the trials, and an info mark beside the heading opens what the section holds

#### Scenario: A note that says "not advice"
- **WHEN** a reader looks at "The record in brief"
- **THEN** its note is in sight under the heading, whole, with no mark in its place
