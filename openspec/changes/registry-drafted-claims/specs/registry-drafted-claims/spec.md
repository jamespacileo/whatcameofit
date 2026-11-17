# Spec Delta

## Purpose

Says how a claim is drafted from stored registry trials when no news report exists: which trials, how they are grouped into one treatment for one condition, when an existing claim is joined, what a draft holds, how it is prepared and decided, and what happens when a report arrives.

## ADDED Requirements

### Requirement: Claims are drafted for one named set of trials at a time
`thenwhat draft-from-registry` SHALL draft claims only for trials in a set the operator names, and only for trials that have a usable treatment name by the rule that works out a trial's search name. A set SHALL say which trials are in it and nothing of how any trial turned out, and its dates SHALL be part of its name. A trial with no usable name SHALL be counted and SHALL draft nothing.

#### Scenario: A trial of a device with a description for a name
- **WHEN** a trial in the named set lists its intervention as a description that is not a name
- **THEN** no claim is drafted for it and it is counted as having no name

#### Scenario: A set the command does not know
- **WHEN** the operator names a set the command does not have
- **THEN** nothing is drafted and the command lists its sets

### Requirement: A name made only of ordinary words drafts nothing
A treatment name SHALL NOT draft a claim when it is made only of ordinary words, by the project's word list and the inflected forms of its words. Such a trial SHALL be counted with its name, so the operator can see a real treatment that was left out.

#### Scenario: A stored name that is an ordinary word
- **WHEN** a trial's stored name is "Home"
- **THEN** no claim is drafted for it and the report lists the name

### Requirement: Trials are grouped into one treatment for one condition by rule
Trials SHALL be grouped by fixed rules, with no model, on the treatment name and the trial's indication as the rule that works out a trial's search indication gives it. Names SHALL be compared ignoring letter case and spacing, and a name equal to another name of the same registry intervention SHALL count as the same. Each group SHALL draft at most one claim. A trial that lists several conditions SHALL be grouped once for each indication the rule gives it.

#### Scenario: Two trials of one treatment for one condition
- **WHEN** two trials in the set test the same named treatment and the rule gives both the same indication
- **THEN** one claim is drafted and both trials are its candidates

#### Scenario: One treatment, two conditions
- **WHEN** two trials test the same named treatment and the rule gives them different indications
- **THEN** two claims are drafted

### Requirement: A treatment and condition a claim already holds drafts no second claim
Before a group drafts a claim, it SHALL be compared with every claim that is not archived, by the rule that refuses a duplicate claim: the same indication, and an intervention equal by name or by any synonym. When such a claim exists, no claim SHALL be drafted, and the group's trials SHALL be handed to that claim as candidates for preparation to score.

#### Scenario: A reported claim for the same treatment and condition
- **WHEN** a group's treatment and indication equal those of a published claim that a news article reported
- **THEN** no claim is drafted, and the group's trials are candidates of the published claim

#### Scenario: The same treatment under another name
- **WHEN** a group's treatment name is a synonym of an existing claim's intervention with the same indication
- **THEN** no claim is drafted

### Requirement: What a registry-drafted claim holds
A claim drafted from registry records SHALL hold its intervention by name alone, its indication, the vertical the rule places it in, that it was drafted from registry records, and the registry numbers of the trials it was drafted from. It SHALL hold no source article, no promise, no reported statement, no origin paper and no evidence stage, and no headline or summary written by a model.

#### Scenario: A draft is made
- **WHEN** a claim is drafted from two trials
- **THEN** it records both registry numbers and that it was drafted from registry records, and it has no source article

### Requirement: A draft the rule cannot place in a vertical is not made
A registry-drafted claim's vertical SHALL be set by rule from the condition terms the registry files its trials under. When those terms point to no group, or to more than one, no claim SHALL be drafted, and the group SHALL be listed with its terms. No model SHALL be asked.

#### Scenario: Terms that point to two groups
- **WHEN** a group's trials are filed under terms that point to two different groups
- **THEN** no claim is drafted and the group is listed as not placed, with its terms

### Requirement: A registry-drafted claim is prepared and decided as any draft
A registry-drafted claim SHALL be pending until `thenwhat prepare --pending` has searched the registries for it, and SHALL then be decided by the rule for drafts. The trials it was drafted from SHALL be candidates, scored for the claim's indication, and SHALL NOT be approved for having led to it. A draft SHALL be approved only when at least one of the trials it was drafted from is approved for it; otherwise it SHALL stay pending and be listed with the scores.

#### Scenario: The drafting trial is approved
- **WHEN** preparation scores the trial a claim was drafted from in the high band for the claim's indication
- **THEN** the match and the claim are approved by rule and the claim's status comes from the trial's events

#### Scenario: The drafting trial is not approved
- **WHEN** preparation scores the only trial a claim was drafted from below the high band
- **THEN** the claim stays pending, is listed with the score and its reasons, and no export publishes it

### Requirement: A registry-drafted claim's status comes from its approved events
A registry-drafted claim's status SHALL be derived from its approved evidence events by the rules that derive any claim's status, and no rule SHALL treat it differently for having no report.

#### Scenario: A started phase 3 trial
- **WHEN** a registry-drafted claim has one approved trial, started, in phase 3
- **THEN** its status is phase 3, with that trial's events listed as what produced it

### Requirement: A prepared batch waits for its audit
A claim that preparation approves for a registry draft SHALL be held awaiting audit, and no export SHALL publish it until its batch is released, as for a claim a read drafts.

#### Scenario: Export before the audit
- **WHEN** 200 registry-drafted claims are approved and their batch is not yet released
- **THEN** the export contains none of them and says how many it left out

### Requirement: A report that arrives is attached, and the claim is then an ordinary claim
When a read's same-claim decision says an article reports a registry-drafted claim, the article SHALL be attached as a source article by the rules for any claim. The claim SHALL keep the record that it was drafted from registry records. A published registry-drafted claim that gains an article SHALL NOT be held for it.

#### Scenario: A report of a registry-drafted claim is read
- **WHEN** a lead's read reports the treatment and condition of a published registry-drafted claim
- **THEN** the article is attached, the claim's first reported date is the article's date, and the claim says a report is linked

### Requirement: A plan before a set is drafted
Before a set is drafted, the command SHALL print: the trials in the set; those with no name and those whose name is ordinary words; the groups; the groups an existing claim holds; the groups not placed in a vertical; the claims that would be drafted; and what preparing them would ask of each registry against its allowance and cost at the decision step. It SHALL draft nothing when asked only for the plan.

#### Scenario: A plan for the first set
- **WHEN** the operator asks for the plan of a set
- **THEN** the counts are printed and no claim is drafted

### Requirement: Drafting can be run again
Drafting a set a second time SHALL draft nothing for a group that already drafted a claim or that a claim already holds. A trial a load adds to the set SHALL be grouped at the next run.

#### Scenario: Run twice
- **WHEN** a set is drafted and drafted again with no new trial
- **THEN** the second run drafts nothing
