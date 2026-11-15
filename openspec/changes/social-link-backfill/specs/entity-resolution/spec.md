## ADDED Requirements

### Requirement: A rule's trial approvals can be scored again
On request, resolving a claim SHALL score again, with the question as it is asked now, each trial match a rule approved that the registry search still returns, and SHALL let the rule decide it again. A match a person or an assistant decided SHALL be left as it is. A match the rule no longer approves SHALL wait for review, or be rejected by the rule when it scores under the rejection threshold; the events read from it SHALL be rejected by the rule and the claim's status SHALL be derived again. Nothing SHALL be decided until every match is scored, so a scoring that fails leaves every approval as it was.

#### Scenario: A rule's approval no longer stands
- **WHEN** a trial a rule approved is scored again and is read as the intervention studied for something else
- **THEN** the match waits for review, the events read from it are rejected by the rule, and the claim's status no longer rests on that trial

#### Scenario: A rule's approval stands
- **WHEN** a trial a rule approved is scored again at or above the approval threshold for the claim's indication
- **THEN** the match stays approved by the rule and its events are unchanged

#### Scenario: A decision by a person or an assistant
- **WHEN** a claim's trial match was approved by a person or an assistant
- **THEN** it is not scored again and its events are unchanged
