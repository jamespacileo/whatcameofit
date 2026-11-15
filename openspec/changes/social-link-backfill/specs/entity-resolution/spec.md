## ADDED Requirements

### Requirement: A rule's trial approvals can be scored again
On request, resolving a claim SHALL score again, with the question, thresholds and rule of a first resolution, each trial match a rule approved that the registry search still returns, and SHALL let the rule decide it again. A match a person or an assistant decided SHALL be left as it is. A match the rule no longer approves SHALL wait for review, or be rejected by the rule when it scores under the rejection threshold, and the claim's status SHALL be derived again. Nothing SHALL be decided until every match is scored.

#### Scenario: A rule's approval no longer stands
- **WHEN** a trial a rule approved is scored again and is read as the intervention studied for something else
- **THEN** the match waits for review, the events read from it are rejected by the rule, and the claim's status no longer rests on that trial

#### Scenario: A rule's approval stands
- **WHEN** a trial a rule approved is scored again at or above the approval threshold for the claim's indication
- **THEN** the match stays approved by the rule and its events are unchanged

#### Scenario: A decision by a person or an assistant
- **WHEN** a claim's trial match was approved by a person or an assistant
- **THEN** it is not scored again and its events are unchanged

#### Scenario: A scoring that fails
- **WHEN** the scoring of a claim's rule approvals fails part of the way
- **THEN** every approval and event is as it was

### Requirement: What a re-scoring withdraws and leaves is reported
For a match the rule no longer approves, the events read from it that a rule approved or that still wait SHALL be rejected by the rule; an event a person or an assistant decided SHALL be left and reported. A rule-approved trial the search no longer returns SHALL stay approved and be reported. The result SHALL name the trials now waiting, the trials rejected, the trials not returned and the events left.

#### Scenario: An event decided by a person or an assistant
- **WHEN** a match is no longer approved and one of its events was approved by an assistant
- **THEN** that event stays approved and the result names it

#### Scenario: An approved trial the search no longer returns
- **WHEN** a rule approved a trial for a claim and the registry search for the claim no longer returns it
- **THEN** the match stays approved, it is not scored, and the result names it
