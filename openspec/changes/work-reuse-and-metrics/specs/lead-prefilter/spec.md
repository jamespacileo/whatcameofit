# Spec Delta

## Purpose

Settles a lead by cheaper means before the decision step is asked about it: rules that cost nothing, then a classifier that runs on the device, each held to a stated recall and checked as it runs.

## ADDED Requirements

### Requirement: Free signals are recorded for every lead
For each lead on a listed outlet, the load and screening SHALL record, at no cost and with no request: the outlet's rate of leads that passed triage, whether the address names a health or science section, whether the title names a topic word or a health word, and how many places shared it.

#### Scenario: A lead from an outlet that rarely passes
- **WHEN** a lead is on an outlet of whose 20,000 scored leads 100 passed
- **THEN** the lead carries that rate

#### Scenario: A new outlet
- **WHEN** an outlet has no scored leads yet
- **THEN** its leads carry no rate, and are treated as an outlet of average rate

### Requirement: Signals order work and do not drop it
The signals SHALL be used to decide which leads are scored and read first. A signal or a combination of signals SHALL NOT stop a lead from being scored unless it has been measured, on scores it was not chosen from, to let at least the required share of passed and held leads through.

#### Scenario: Health words in the title
- **WHEN** a rule keeps 88% of leads that passed triage
- **THEN** it is used to order leads and is not used to drop any

### Requirement: A classifier settles what is plainly not health
A lead whose headline a classifier trained on stored triage scores gives a probability below the settle threshold SHALL be marked as settled by the prefilter as not health, with the classifier's version and the probability, and SHALL NOT be sent to the decision step. Every other lead SHALL be sent as before. The classifier SHALL decide nothing else: it approves nothing, sets no status and is shown nowhere on the site.

#### Scenario: A headline about a merger
- **WHEN** the classifier gives a headline a probability below the threshold
- **THEN** the lead is settled as not health by the prefilter, no model call is made for it, and its record says which version settled it

#### Scenario: A headline it is unsure of
- **WHEN** the probability is at or above the threshold
- **THEN** the lead goes to the decision step as it does today

### Requirement: The threshold comes from a required recall
The share of passed and held leads that must still reach the decision step SHALL be a setting with no default. The settle threshold SHALL be the one that meets it on scores held out from training, and SHALL be stored with the classifier's version, the size of the training and held-out sets, and the share of leads it settles there. The prefilter SHALL settle nothing while the setting is empty or no classifier meets it.

#### Scenario: No recall set
- **WHEN** the required recall is not configured
- **THEN** every lead goes to the decision step and the prefilter says why it is off

#### Scenario: A classifier that cannot meet it
- **WHEN** no threshold meets the required recall on the held-out scores
- **THEN** the classifier is not used and the report says what recall it reached

### Requirement: What the prefilter settles is sampled
A set share of the leads the prefilter would settle SHALL be sent to the decision step all the same, and their scores kept. When the share of that sample that passes or is held is higher than the required recall allows, the prefilter SHALL stop settling, SHALL say so, and SHALL leave the leads it settled since the last good sample due for the decision step.

#### Scenario: Headlines change
- **WHEN** a new topic's headlines begin passing triage in the sample at a rate the recall does not allow
- **THEN** the prefilter stops settling, and the leads it settled since the last good sample are scored

#### Scenario: A steady week
- **WHEN** the sample's pass rate stays within what the recall allows
- **THEN** the prefilter goes on, and the report gives the sample's size and rate

### Requirement: The classifier is a versioned model
A classifier SHALL have a version, a record of the scores it was trained on and held out, and its figures on any independent labels there are. No name of a model or library version SHALL be written in code. A new classifier SHALL replace an old one only with its figures recorded beside the old one's.

#### Scenario: Retraining
- **WHEN** a classifier is trained on a later set of scores
- **THEN** it gets a new version, and the record shows both versions' recall and share settled on the same held-out set

### Requirement: A settled lead can be scored later
A lead the prefilter settled SHALL be kept with its outcome and SHALL be sent to the decision step when a new classifier version would not settle it, when the triage version rises and the operator asks for settled leads to be scored, or when the operator names it.

#### Scenario: A better classifier
- **WHEN** a new version gives a previously settled lead a probability above the threshold
- **THEN** the lead goes to the decision step

### Requirement: The decision step is asked without paying for its wording each time
The triage decision SHALL be asked in a shape whose input tokens for a headline are measured and recorded. A new shape SHALL replace the present one only when, on a fixed sample of stored leads, its scores agree with the present scores within a tolerance that is a setting with no default, and SHALL raise the triage version.

#### Scenario: A shape that scores differently
- **WHEN** a cheaper shape disagrees with present scores on the sample by more than the tolerance
- **THEN** it is not adopted, and its figures are recorded

#### Scenario: A shape that holds
- **WHEN** a cheaper shape agrees within the tolerance
- **THEN** it is adopted under a new triage version, with tokens for a headline before and after recorded
