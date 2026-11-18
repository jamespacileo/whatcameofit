# Spec Delta

## Purpose

Holds the shared records that a claim's identity is made of, one per condition and one per intervention, and the coded terms each stored trial is filed under, so that claims, trials and coverage are joined on keys rather than on words.

## ADDED Requirements

### Requirement: A condition is one vocabulary descriptor
The system SHALL hold at most one condition record per descriptor of the subject vocabulary the registry files trials under (MeSH), with the descriptor's identifier, its label and its tree numbers as the vocabulary's own record gives them. A condition record SHALL NOT be made for words that no descriptor holds.

#### Scenario: Two claims for one descriptor
- **WHEN** two claims' approved exact condition terms are the same descriptor
- **THEN** both point to one condition record

#### Scenario: A condition with no descriptor
- **WHEN** a claim's condition has no approved exact term
- **THEN** no condition record is made for it and the claim keeps its indication as text only

### Requirement: An intervention is one treatment, shared by its claims
The system SHALL hold one intervention record per treatment, keyed, in this order of preference, on the identifier of the one substance a substance registry lists it under, on its intervention descriptor, or on its name compared ignoring letter case and spacing. The record SHALL hold the treatment's name, synonyms, development codes and search phrases. Every claim about the treatment SHALL point to the same record.

#### Scenario: One drug in two claims
- **WHEN** two claims for different conditions are about the same substance
- **THEN** both point to one intervention record and share its synonyms

#### Scenario: A treatment with no substance or descriptor
- **WHEN** a treatment has neither a substance registry entry nor a descriptor
- **THEN** its record is keyed on its name, and a later key found for it is added to the same record

### Requirement: A trial's conditions are read from its record by rule
For each stored trial the system SHALL record the condition descriptors the registry lists for it, read from the raw payload it already holds, with no request and no model. A trial with no condition descriptor SHALL record none and carry that reason.

#### Scenario: A trial listing two condition descriptors
- **WHEN** the registry lists two condition descriptors for a trial
- **THEN** both are recorded for the trial

#### Scenario: Loaded again with nothing changed
- **WHEN** a trial whose payload has not changed is loaded again
- **THEN** its recorded conditions are unchanged

### Requirement: A trial's tested intervention is the one agent its experimental arm adds
For each stored trial the system SHALL record, by rule from the raw payload, the agent an experimental arm gives that no placebo, sham, active comparator or no-intervention arm gives, as the trial's tested intervention. When no agent or more than one is added, or the trial has no arms, the system SHALL record none and the trial SHALL carry the reason.

#### Scenario: A drug added to a chemotherapy backbone
- **WHEN** a trial's experimental arm gives drug X with chemotherapy and its comparator arm gives placebo with the same chemotherapy
- **THEN** X is recorded as the trial's tested intervention and the chemotherapy is not

#### Scenario: A single-arm trial
- **WHEN** a trial has one experimental arm giving drug X and no comparator arm
- **THEN** X is recorded as the trial's tested intervention

#### Scenario: Two agents added
- **WHEN** a trial's experimental arm adds drugs X and Y that no comparator arm gives
- **THEN** no tested intervention is recorded and the reason is "more than one agent added"

### Requirement: Coverage is answered from keys
The system SHALL report, for a named set of stored trials, how many are cited by a published claim, and for each that is not, one reason from a fixed list: no coded pair, a pair no claim holds, a pair whose claim has not approved the trial, or a pair whose claim is not published. The report SHALL make no request and write nothing.

#### Scenario: A trial whose pair a claim holds
- **WHEN** a stored trial's tested intervention and one of its conditions are the pair of a published claim that has not approved the trial
- **THEN** the trial is counted as not cited, with the reason that the claim has not approved it

#### Scenario: A trial with two agents added
- **WHEN** a stored trial has no tested intervention because two agents are added
- **THEN** it is counted as not cited, with the reason that it has no coded pair
