# Spec Delta

## Purpose

Says how stored link leads are linked to stored registry trials with no request and no model, which links are strong enough to change what is read, in what order sets of trials are worked, and that a read on this route is an ordinary read.

## ADDED Requirements

### Requirement: A link to a trial has a reason and a strength
Every link from a link lead to a registry trial SHALL be recorded with one reason and the strength that reason carries, and, where it was made on a term, with the term as the registry writes it and the condition word found beside it. The strengths SHALL be, strongest first: `exact`, the title or the address gives the trial's registry number; `strong`, the title holds a development code of the trial and a word of its conditions; `named`, the title holds a development code of the trial and no word of its conditions, or holds the trial's acronym and a word of its conditions; `candidate`, the title holds the name the trial is searched by, or another name of one of its drug or biological interventions, and a word of its conditions, or the news search found the address for the trial. Linking SHALL send no request, call no model and record no spend.

#### Scenario: A lead that gives a registry number
- **WHEN** a lead's address or title holds a stored trial's registry number
- **THEN** the lead has an exact link to that trial alone, with no condition word needed

#### Scenario: A telling name without the condition
- **WHEN** a lead's title holds a trial's development code and no word of its conditions
- **THEN** the link is recorded as named, and no strong link is recorded

#### Scenario: Linking a million leads
- **WHEN** links are made over every stored lead
- **THEN** no request is sent, no model is called and no usage is recorded

### Requirement: A telling name
A trial's name SHALL be telling only when it is a development code among the trial's intervention names and other names: two to six letters, an optional hyphen, at least three digits and at most a short tail, whatever its letter case and with or without its hyphen. Letters that open an antigen, a virus, a registry's number or a measure SHALL NOT make a code. A study's acronym, a class of treatments, a behaviour, a food and a name of a substance SHALL NOT be telling. A substance's name MAY become telling only once the substance registry has been asked about it and the share of stored titles that hold it has been measured and set; until then it links as a candidate and no more.

#### Scenario: A development code
- **WHEN** a trial's intervention is named "TARA-002"
- **THEN** that name is telling

#### Scenario: A code written without its hyphen
- **WHEN** a lead's title holds "tara002" and a stored trial lists "TARA-002"
- **THEN** the title holds that trial's code

#### Scenario: A substance most headlines could hold
- **WHEN** a trial's intervention is "Insulin"
- **THEN** the name is not telling

#### Scenario: A study's acronym
- **WHEN** a trial's intervention is named "LIFE" after the study
- **THEN** the name is not telling

### Requirement: A strong link
A link from a link lead to a registry trial SHALL be strong only when the lead's title holds a telling name of the trial and a word of the trial's conditions that is neither a general word nor shorter than four letters. Every intervention name and other name of the trial SHALL be tried. A strong link SHALL be recorded with the name and the condition word it was made on.

#### Scenario: A code and its condition
- **WHEN** a lead's title holds "TARA-002" and "bladder", and a stored trial of TARA-002 lists bladder cancer
- **THEN** the lead is strongly linked to that trial, and the link records "TARA-002" and "bladder"

### Requirement: An acronym links only when it carries a number
A trial's acronym SHALL link a lead only when it carries a digit beside a word of at least five letters, holds no word of any stored trial's conditions, is the acronym of no more than three stored trials, and the title holds a word of the trial's conditions beside it. The link SHALL be recorded as named and SHALL NOT be strong. An acronym with no digit SHALL never link a lead, whatever its length.

#### Scenario: An acronym with a number
- **WHEN** a lead's title holds "KEYNOTE-789" and a word of the conditions of the one stored trial with that acronym
- **THEN** the lead has a named link to that trial, with the acronym recorded

#### Scenario: A common-word acronym
- **WHEN** a trial's acronym is "HOPE" or "RECOVERY" and a lead's title holds that word and a word of the trial's conditions
- **THEN** no link is recorded

### Requirement: Another name of an intervention is a candidate
Another name of a trial's drug, biological, genetic or combination intervention SHALL link a lead as a candidate when the title holds it as whole words with a word of the trial's conditions, the name is at least five letters, is not the name the trial is searched by, is not a development code, and holds no general word of health news and no word of any stored trial's conditions. Another name of a behaviour, a device or a procedure SHALL NOT link. At most the configured number of trials SHALL be kept for one name.

#### Scenario: A brand name
- **WHEN** a lead's title holds a trial's other name for its drug and a word of its condition
- **THEN** the lead has a candidate link to the trial, and no strong link

#### Scenario: A class of treatments
- **WHEN** a trial's other name for its intervention is "cancer vaccine"
- **THEN** the name links no lead

#### Scenario: A behaviour
- **WHEN** a behavioural intervention has another name and a lead's title holds it beside the condition
- **THEN** no link is recorded

### Requirement: A strong link is to a name and a condition
A lead that is strongly linked on a name and a condition SHALL be linked to every stored trial that carries both, and the linking SHALL NOT choose one of them as the trial reported. The count of trials a lead is linked to SHALL NOT be capped for an exact or a strong link.

#### Scenario: Nine trials of one drug for one condition
- **WHEN** a lead's title names a drug and a condition that nine stored trials carry
- **THEN** the lead is strongly linked to all nine and none is marked as the one reported

### Requirement: The present link is kept as a candidate
The link screening records when a title holds a trial's search name and a word of its indication SHALL be kept as it is and SHALL NOT be treated as strong. It SHALL NOT be described, in any report or on any page, as a report of the trial.

#### Scenario: A common name with its indication
- **WHEN** a lead's title holds "protein" and "diabetes" and a stored trial has that search name and indication
- **THEN** the lead has a candidate link to the trial and no strong link

### Requirement: What a strong link changes
A link SHALL change only which leads are read and in what order. Only an exact or a strong link SHALL be enough for a lead triage held to be read, and only when it is to a trial in the set being worked. A lead triage rejected SHALL NOT be read on any link. Due leads SHALL be read in this order: those naming one of the operator's topics; those with an exact or strong link to a phase 3 trial of the set being worked; those so linked to any trial of that set; those so linked to any other trial; those with any other link to a trial; then by shares.

#### Scenario: A held lead with a strong link
- **WHEN** a lead's score is between the two thresholds and it is strongly linked to a trial in the set being worked
- **THEN** it is read

#### Scenario: A held lead with a weaker link
- **WHEN** a lead's score is between the two thresholds and its only link to the set being worked is named or a candidate
- **THEN** it is not read

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
The operator SHALL be able to name the set of trials being worked, as a setting for every read and as the argument of a command that reads only the leads linked to the set. The sets SHALL be those the stored trials are selected by: `active-since-2025` and `completed-with-results-since-2025`. Within a set, leads linked to its phase 3 trials SHALL be read before the others. A set SHALL say only which trials' links are read first and nothing of how any trial turned out.

#### Scenario: Reading the leads of a set
- **WHEN** the operator reads the set `active-since-2025` with a limit
- **THEN** only leads linked to a trial of that set at the strength asked for are read, those linked to its phase 3 trials first, by the reading step and ledger every read uses

### Requirement: A set that cannot be worked is refused
A set name the command does not know SHALL be refused with the list of sets, and a strength it does not know with the list of strengths.

#### Scenario: A set the command does not know
- **WHEN** the operator asks for the set `successful`
- **THEN** nothing is read and the command lists the sets it has

### Requirement: A plan before a set is worked
Before any lead of a set is read, the command SHALL print how many leads in scope are linked to the set at the strength asked for and to how many of its trials, how many of those triage passed, held and rejected, how many are already read, how many would be read, what the reads are expected to cost, what the reads for the set have used this month of the route's share of the ceiling, and how many claims the reads are expected to send to audit. The share SHALL be a setting. Without a limit the command SHALL read nothing. It SHALL read nothing when the expected cost would pass what is left of the route's share. The weakest strength read for SHALL be the operator's to give, strong unless given; a weaker one widens which passed leads are read and never which held leads.

#### Scenario: A plan for the first set
- **WHEN** the operator asks for the plan of `active-since-2025`
- **THEN** the counts, the expected cost and the expected claims are printed and no article is fetched

#### Scenario: The share would be passed
- **WHEN** the reads of a set are expected to cost more than is left of the route's share for the month
- **THEN** nothing is read and the command says how much is left

### Requirement: A read on this route is an ordinary read
A lead read because of a link to a trial SHALL be read, drafted, prepared, approved and held awaiting audit by the same steps and rules as any link lead a backfill reads. No claim it drafts SHALL be published before `thenwhat audit clear` releases it.

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
