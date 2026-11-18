# lead-triage Specification

## Purpose
Scores, from a link lead's title alone, whether the article reports a specific treatment for a specific condition, so that articles are fetched and read only where that is likely.

## Requirements

### Requirement: Triage decision
The triage step SHALL apply to leads that screening left in scope. The standard rule SHALL request a decision with the options: reports a specific treatment for a specific condition, about health but not that, and not about health. The probability of the first option SHALL be stored as the lead's score, with the version of the step that produced it.

#### Scenario: A headline about a trial result
- **WHEN** a lead in scope is triaged
- **THEN** it has a score between 0 and 1 and a decision log entry for the triage step

#### Scenario: A lead out of scope
- **WHEN** a lead's screening outcome is unlisted outlet or already tracked
- **THEN** it is never triaged and no spend is recorded for it

### Requirement: What the decision is shown
The standard decision SHALL be shown the lead's title, its outlet and the year it was first shared, and nothing else. No article SHALL be fetched for triage.

#### Scenario: Triage of ten thousand leads
- **WHEN** the triage step runs over ten thousand leads
- **THEN** no outlet receives a request

### Requirement: The score decides nothing by itself
A lead's score SHALL NOT create or change a claim, a source article, a match or a status. Whether a lead is passed, held or rejected SHALL be worked out from its score and the thresholds each time it is asked: passed at or above the pass threshold, rejected below the reject threshold, held between them. Neither threshold for the standard rule SHALL have a default.

#### Scenario: Thresholds not set
- **WHEN** leads are scored and no threshold is configured
- **THEN** every scored lead is undecided, and none is passed

#### Scenario: A threshold is changed
- **WHEN** the operator lowers the pass threshold
- **THEN** more leads are passed and no lead is triaged again

#### Scenario: A rejected lead
- **WHEN** a lead's score is below the reject threshold
- **THEN** the lead and its score are kept, and it is never read

### Requirement: Calibrated treatment-headline triage
When the operator enables `LEAD_EVIDENCE_TRIAGE`, triage SHALL run the three calibrated treatment-headline questions with the headline as their only input. The score SHALL be the mean probability of the relevant answer across those questions. The rule SHALL have a separate triage version and SHALL apply 0.7883 to both thresholds.

#### Scenario: Reading after switching rules
- **WHEN** the calibrated rule is enabled
- **THEN** the reader requires a score and the evaluation gate for the calibrated version

### Requirement: No answer is no score
A lead for which the backend gives no usable answer SHALL have no score and SHALL stay due. No score SHALL be substituted.

#### Scenario: The backend declines a question
- **WHEN** the backend returns a refusal for one lead of a batch
- **THEN** that lead has no score, its failure is recorded, and the other leads of the batch are scored

### Requirement: Triage stops at the spend ceiling
The triage step SHALL stop when the month's recorded model cost has reached the ceiling. Leads not yet scored SHALL stay due, and none SHALL count a failed attempt for it.

#### Scenario: Ceiling reached part way
- **WHEN** the ceiling is reached after 30,000 of 80,000 leads
- **THEN** the run stops, says why, and reports 50,000 still due

### Requirement: A new version scores again
Raising the triage step's version SHALL make every lead in scope due for triage. A lead's earlier scores SHALL stay in the decision log.

#### Scenario: The question is reworded
- **WHEN** the triage question is changed and the step's version is raised
- **THEN** every lead in scope is scored again and its stored score is the new one

### Requirement: Topic leads are scored first
Among the leads due for triage, those whose title names one of the operator's topics SHALL be scored first. The order SHALL change which lead is scored when, and never what a lead scores.

#### Scenario: A topic lead among older leads
- **WHEN** twenty-five older leads and one lead that names a topic are due
- **THEN** the lead that names the topic is in the first call
