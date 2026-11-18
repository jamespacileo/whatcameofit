## ADDED Requirements

### Requirement: An unconfirmed stage reading is marked on the claim page
When the export carries a stage reading for a claim, the claim page SHALL show, where a confirmed stage would be shown, the stage the reading chose, marked low confidence with its score as a percentage, a statement that it is not confirmed and does not decide the status, and the other stages the reading weighed with their percentages. The page SHALL word nothing else from the reading: lists, summaries, the claim's brief and the open data file SHALL use the confirmed stage only.

#### Scenario: Reading shown beside the claim's facts
- **WHEN** a claim page is built for a claim whose export carries a stage reading of early human at 0.7 with animal at 0.28
- **THEN** the page shows "Early human study" under "Evidence when first reported", with "Low confidence · 70%", that it is not confirmed and does not decide the status, and "animal study, 28%"

#### Scenario: No reading
- **WHEN** a claim page is built for a claim with no confirmed stage and no stage reading
- **THEN** the page shows no evidence stage
