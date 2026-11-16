# Spec Delta

## Purpose

Says how stored link leads are linked to stored registry trials with no request and no model, which links are strong enough to change what is read, in what order sets of trials are worked, and that a read on this route is an ordinary read.

## ADDED Requirements

### Requirement: A telling name
A trial's name SHALL be telling only when it is a development code among the trial's intervention names and other names, or a name of a drug or biological intervention that the substance registry lists as one substance and that fewer than the configured share of stored lead titles hold. The share SHALL have no default. A study's acronym, a class of treatments, a behaviour, a food and any name the substance registry has not been asked about SHALL NOT be telling.

#### Scenario: A development code
- **WHEN** a trial's intervention is named "TARA-002"
- **THEN** that name is telling

#### Scenario: A substance most headlines could hold
- **WHEN** a trial's intervention is "Insulin", the substance registry lists it, and more than the configured share of stored titles hold the word
- **THEN** the name is not telling

#### Scenario: A study's acronym
- **WHEN** a trial's intervention is named "LIFE" after the study
- **THEN** the name is not telling

#### Scenario: The share is not set
- **WHEN** strong links are asked for and the share is not configured
- **THEN** nothing is linked and the command names the missing setting

### Requirement: A strong link
A link from a link lead to a registry trial SHALL be strong only when the lead's title holds, as whole words, a telling name of the trial and a word of the trial's conditions that is not a word of that name. Every intervention name and other name of the trial SHALL be tried. A strong link SHALL be recorded with the name and the condition word it was made on. Linking SHALL send no request, call no model and record no spend.

#### Scenario: A code and its condition
- **WHEN** a lead's title holds "TARA-002" and "bladder", and a stored trial of TARA-002 lists bladder cancer
- **THEN** the lead is strongly linked to that trial, and the link records "TARA-002" and "bladder"

#### Scenario: A brand name
- **WHEN** a lead's title holds a trial's other name for its drug and a word of its condition, and that name is telling
- **THEN** the lead is strongly linked to the trial

#### Scenario: A telling name without the condition
- **WHEN** a lead's title holds a trial's telling name and no word of its conditions
- **THEN** no strong link is recorded

#### Scenario: Linking a million leads
- **WHEN** strong links are made over every stored lead
- **THEN** no request is sent, no model is called and no usage is recorded

### Requirement: A strong link is to a name and a condition
A lead that is strongly linked on a name and a condition SHALL be linked to every stored trial that carries both, and the linking SHALL NOT choose one of them as the trial reported. The count of trials a lead is linked to SHALL NOT be capped for a strong link; the trials SHALL be found from the name and condition when needed and need not each be stored as a row.

#### Scenario: Nine trials of one drug for one condition
- **WHEN** a lead's title names a drug and a condition that nine stored trials carry
- **THEN** the lead is strongly linked to all nine and none is marked as the one reported

### Requirement: The present link is kept as a candidate
The link screening records when a title holds a trial's search name and a word of its indication SHALL be kept as it is and SHALL NOT be treated as strong. It SHALL NOT be described, in any report or on any page, as a report of the trial.

#### Scenario: A common name with its indication
- **WHEN** a lead's title holds "protein" and "diabetes" and a stored trial has that search name and indication
- **THEN** the lead has a candidate link to the trial and no strong link

### Requirement: What a strong link changes
A strong link SHALL change only which leads are read and in what order. A lead triage held SHALL be read when it is strongly linked to a trial in the set being worked. A lead triage rejected SHALL NOT be read on any link. Due leads SHALL be read in this order: those naming one of the operator's topics; those strongly linked to a trial in the set being worked; those strongly linked to any other trial; those with a candidate link; then by shares.

#### Scenario: A held lead with a strong link
- **WHEN** a lead's score is between the two thresholds and it is strongly linked to a trial in the set being worked
- **THEN** it is read

#### Scenario: A rejected lead with a strong link
- **WHEN** triage rejected a lead and it is strongly linked to a trial under way in phase 3
- **THEN** it is not read

#### Scenario: Two due leads
- **WHEN** two leads are due, one with a candidate link and many shares, one with a strong link to the set being worked and few
- **THEN** the lead with the strong link is read first

### Requirement: What a strong link never does
A strong link SHALL NOT attach a lead to a trial, SHALL NOT be shown on any page, SHALL NOT be a match or a reason for one, SHALL NOT approve anything, SHALL NOT create or change a claim, and SHALL NOT be exported.

#### Scenario: Export after linking
- **WHEN** strong links are made over every lead and the export is produced
- **THEN** the export is identical to the one produced before the linking

### Requirement: Sets of trials
The operator SHALL be able to name the set of trials being worked. The sets SHALL be: `under-way-phase-3`, trials not started or under way in phase 3; `under-way-phase-2`, trials not started or under way in phase 2 and not in phase 3; and `completed-recently`, trials in phase 2 or 3 whose primary completion date is within the configured number of months. A set SHALL say only which trials' links are read first and nothing of how any trial turned out.

#### Scenario: A trial under way in phase 2 and 3
- **WHEN** a stored trial is under way and its phases are 2 and 3
- **THEN** it is in `under-way-phase-3` and not in `under-way-phase-2`

### Requirement: A set that cannot be worked is refused
A set name the command does not know SHALL be refused with the list of sets. `completed-recently` SHALL be refused while stored trials carry no completion date.

#### Scenario: A set the command does not know
- **WHEN** the operator asks for the set `successful`
- **THEN** nothing is read and the command lists the sets it has

#### Scenario: Recently completed before the wider load
- **WHEN** the operator names `completed-recently` and no stored trial has a completion date
- **THEN** the command refuses and says the wider load has not run

### Requirement: A plan before a set is worked
Before any lead of a set is read, the command SHALL print how many leads are strongly linked to the set, how many of those triage passed, held and rejected, how many are already read, how many would be read, what the reads are expected to cost, what has been spent this month against the route's share of the ceiling, and how many claims the reads are expected to send to audit. It SHALL read nothing when the expected cost would pass the route's share.

#### Scenario: A plan for the first set
- **WHEN** the operator asks for the plan of `under-way-phase-3`
- **THEN** the counts, the expected cost and the expected claims are printed and no article is fetched

#### Scenario: The share would be passed
- **WHEN** the reads of a set are expected to cost more than is left of the route's share for the month
- **THEN** nothing is read and the command says how much is left

### Requirement: A read on this route is an ordinary read
A lead read because of a strong link SHALL be read, drafted, prepared, approved and held awaiting audit by the same steps and rules as any link lead a backfill reads. No claim it drafts SHALL be published before `thenwhat audit clear` releases it.

#### Scenario: A read drafts a claim
- **WHEN** a strongly linked lead is read and its article reports one treatment for one condition that no claim holds
- **THEN** a claim is drafted, prepared, approved by rule and held awaiting audit, and no export publishes it until it is cleared

#### Scenario: The article is about no single treatment
- **WHEN** a strongly linked lead is read and extraction finds no one treatment for one condition
- **THEN** no claim is drafted, the lead's outcome says so, and the linked trials' pages are unchanged

### Requirement: Linked trials are candidates of the claim
The trials of a strong link SHALL be handed to preparation as candidates with the reason that the lead's title named them. Each SHALL be scored for the claim's indication and decided as any candidate is, and none SHALL be approved for having been linked.

#### Scenario: The linked trial tests something else
- **WHEN** a linked trial names the lead's drug only as a comparator for another treatment
- **THEN** the trial is a candidate of the claim, is scored for the claim's indication, and is not approved for having been linked

### Requirement: A trial has a report only through a published claim
A trial SHALL be said to have a linked report only when a published claim cites it. No other record SHALL mark a trial as reported.

#### Scenario: A set is finished
- **WHEN** every strongly linked lead of a set has been read and audited
- **THEN** the trials of the set that no published claim cites still read that no news report is linked yet
