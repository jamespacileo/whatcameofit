# Spec Delta

## ADDED Requirements

### Requirement: Archive
An operator SHALL be able to archive a published claim or source page by its slug, giving a reason, and to unarchive it. Archiving SHALL keep every record in the database. The next export SHALL leave an archived item out of every public file and SHALL list its slug and the date it was archived. The reason SHALL NOT be exported.

#### Scenario: Operator takes a claim down
- **WHEN** an operator archives a published claim with the reason "wrong trial"
- **THEN** the claim and its events stay in the database, and the next export lists its slug and date and holds nothing else about it

#### Scenario: Unknown slug
- **WHEN** an operator archives a slug that no claim or source has
- **THEN** the command is refused and names the slug

#### Scenario: Putting it back
- **WHEN** an operator unarchives an archived claim
- **THEN** the next export contains the claim again

## MODIFIED Requirements

### Requirement: Review states
Every draft claim, entity match and evidence event SHALL be in exactly one review state: pending, approved or rejected. Each decision SHALL record when it was made and whether a human, a rule, the seed loader or an assistant made it. An item approved by rule SHALL be published without waiting for a person.

#### Scenario: Operator approves a match
- **WHEN** an operator approves a pending entity match
- **THEN** the match is approved, with the decision time and a human decider recorded

#### Scenario: Rule approves a match
- **WHEN** a rule approves an entity match
- **THEN** the match is approved, recorded as decided by a rule, and counts toward the claim's status in the next export
