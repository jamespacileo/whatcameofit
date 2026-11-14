## ADDED Requirements

### Requirement: The latest lookup owns the answer
The home page SHALL ignore the success or failure of an article lookup after the reader submits a newer search, including an empty search. An ordinary current lookup SHALL still display its result.

#### Scenario: Old lookup finishes after a new submission
- **WHEN** an earlier article lookup resolves or fails after the reader submits a shortened link or clears the search
- **THEN** the newer answer or cleared result remains visible

### Requirement: Live candidates show their confidence
Each live trial candidate SHALL show its own match confidence or explicitly say it is unavailable. Its supporting explanation and the confidence limitation SHALL be available in a collapsed disclosure. The label SHALL not imply treatment effectiveness or trial quality. Titles and disclosures SHALL fit a 320-pixel viewport.

#### Scenario: Mixed confidence availability
- **WHEN** one candidate has a valid confidence and another does not
- **THEN** their separate disclosures show the valid score and unavailable label respectively, without copying a score between records

### Requirement: Reminders do not contradict results
The check-again reminder SHALL invite another check without asserting that no record exists.

#### Scenario: Live candidates found
- **WHEN** live lookup finds trial candidates for an untracked article
- **THEN** the reminder does not claim that nothing is on record
