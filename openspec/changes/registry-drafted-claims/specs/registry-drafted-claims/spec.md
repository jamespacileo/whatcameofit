# Spec Delta

## Purpose

Says how a claim is drafted from stored registry trials when no news report exists: which trials, how they are grouped into one treatment for one condition, when an existing claim is joined, what a draft holds, how it is prepared and decided, and what happens when a report arrives.

## ADDED Requirements

### Requirement: Claims are drafted for one named set of trials at a time
`thenwhat draft-from-registry` SHALL draft claims for trials in the named set when registry evidence establishes the intervention or full regimen and indication. A set SHALL name its dates and SHALL say nothing of how any trial turned out.

#### Scenario: A trial with a descriptive intervention label
- **WHEN** a trial in the named set lists its intervention as a description
- **THEN** use the label when it identifies what was tested, and report otherwise unresolved scope for review

#### Scenario: A set the command does not know
- **WHEN** the operator names a set the command does not have
- **THEN** nothing is drafted and the command lists its sets

#### Scenario: The 2026 rollout set
- **WHEN** the operator selects `active-phase-2-3-or-completed-2026`
- **THEN** the set includes active Phase 2 or 3 interventional trials and those actually completed in 2026, including combined phases and all sponsor classes and results states
- **AND** trials with unresolved scope remain in the coverage count until their scope is verified

### Requirement: A name made only of ordinary words drafts nothing
A legacy search name made only of ordinary words, by the project's word list and the inflected forms of its words, SHALL NOT establish the intervention's identity. The planner SHALL record such a trial for review when it cannot identify the intervention from the registered arms and intervention description.

#### Scenario: A stored name that is an ordinary word
- **WHEN** a trial's stored name is "Home" and its registry fields identify no specific intervention
- **THEN** no claim is drafted for it and the report lists the name

#### Scenario: A tested arm includes a schedule in place of a treatment
- **WHEN** a component is recorded only as a schedule or role such as "Maintenance Therapy"
- **THEN** the planner holds the trial pending scope review
- **AND** a full registered intervention that includes a schedule or role can still establish the scope

### Requirement: Trials are grouped into one treatment for one condition by rule
Trials SHALL be grouped by fixed rules on the verified intervention or complete regimen and the full indication. The rule SHALL preserve clinically distinct formulations and combination components. Names SHALL be compared ignoring letter case and spacing, and documented aliases SHALL be checked for equivalence. Each group SHALL draft at most one claim.

#### Scenario: Two trials of one treatment for one condition
- **WHEN** two trials in the set test the same named treatment and the rule gives both the same indication
- **THEN** one claim is drafted and both trials are its candidates

#### Scenario: One treatment, two conditions
- **WHEN** two trials test the same named treatment and the rule gives them different indications
- **THEN** two claims are drafted

#### Scenario: A trial lists several conditions
- **WHEN** a trial lists several conditions
- **THEN** evidence must establish each regimen and indication pairing before it is grouped

#### Scenario: A registered disease qualifier follows the disease name
- **WHEN** two verified indications differ only in whether a recognized disease qualifier precedes or follows the same disease name
- **THEN** compare them as the same indication for grouping and existing claim candidates
- **AND** a trial with a single registered condition can retain a more specific phrase from the title when it contains the reordered condition

#### Scenario: A crossover arm lists multiple interventions
- **WHEN** membership describes a sequence of different treatments
- **THEN** verify which regimen is tested before grouping

#### Scenario: The registry identifies a separate inactive control
- **WHEN** the registry explicitly identifies an assigned component as a placebo or sham
- **THEN** exclude it from the active regimen
- **AND** keep a control-only arm out of the test arms even if it is marked experimental

#### Scenario: One component label mixes alternatives or roles
- **WHEN** a component label names alternative products or joins an active treatment and a control without separating their roles
- **THEN** hold the record for scope review before grouping

#### Scenario: A single listed arm includes alternatives
- **WHEN** its label identifies an optional component among the listed treatments or its title explicitly assigns separate regimens to different treatment lines
- **THEN** hold the trial for review of each complete regimen before grouping

#### Scenario: Distinct component lists have the same display name
- **WHEN** the regimen display name and normalized indication agree but the registered component lists differ
- **THEN** the preview preserves both group identifiers and component lists and holds the groups before drafting

#### Scenario: The registry lists one group's regimen as another group's alias
- **WHEN** separate groups with the same normalized indication have overlapping registry names
- **THEN** the preview lists the groups and the trial identifiers supporting each direction of the alias
- **AND** when each group names the other, both groups require review before either can draft
- **AND** the preview digest binds alias evidence for every selected group

### Requirement: Scope review candidates cite exact registry fields
A scope review packet SHALL contain the stored trial's titles, condition labels, named interventions, arm assignments and planned outcome names. A structured selection SHALL copy phrases from appropriate fields. A proposal SHALL require an evidence-backed scope judgment before it becomes a review receipt. Live model requests SHALL use the configured ceiling and the shared cache.

#### Scenario: Two studies file a tablet and injection under the same product code
- **WHEN** their registry titles state different formulations
- **THEN** the packet supports separate candidate regimen names with verbatim evidence

#### Scenario: A returned phrase is absent from the cited field
- **WHEN** the grounding check compares the selected phrase with the packet
- **THEN** the answer is rejected

#### Scenario: A term appears in an exclusion or an unassigned cohort
- **WHEN** an arm-scoped candidate cites a protocol condition listed only in an exclusion, an unassigned cohort, or eligibility with unclear headings
- **THEN** the packet retains the exact wording for review and rejects the citation as evidence of the enrolled population
- **AND** an explicit study-wide inclusion criterion or registered study population can support the enrolled population

#### Scenario: A reviewed pair cites a detailed cached protocol
- **WHEN** a scope receipt cites an arm description or eligibility field from a detailed protocol
- **THEN** the planner verifies the receipt against that protocol and checks that its identifier, update date and shared scope fields agree with the stored record
- **AND** a batch that selects the pair binds its receipt into the preview digest

#### Scenario: A detailed protocol changes
- **WHEN** a detailed protocol cited by a receipt changes, or its shared fields differ from the stored record
- **THEN** the planner refuses the receipt before any group in the batch is drafted

### Requirement: A treatment and condition a claim already holds drafts no second claim
Before a group drafts a claim, it SHALL be compared with every claim that is not archived for which the complete regimen or an alias and the indication match. When a match is verified, no claim SHALL be drafted, and the group's trials SHALL be handed to that claim as candidates for preparation to score.

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
A registry-drafted claim's vertical SHALL be set by rule from its registry condition terms and the MeSH vocabulary. Groups with no topic or unresolved competing evidence SHALL wait for topic review. Topic placement SHALL use these sources without a model.

#### Scenario: Independent terms point to competing topics
- **WHEN** distinct disease descriptors support competing topics
- **THEN** the group waits for topic review and the preview lists its terms

#### Scenario: A registered condition has an explicit population qualifier
- **WHEN** a proposed indication starts with a registered condition followed by an enrollment phrase such as “in adults”
- **THEN** use descriptors with the exact registered condition name for topic evidence
- **AND** when the registry omits its descriptor projection, an exact preferred disease or disorder label from the installed MeSH vocabulary can supply that evidence
- **AND** preserve the full indication for grouping and hold topic conflicts that the primary-topic rule cannot resolve

### Requirement: One tumor descriptor can establish Cancer as the primary vertical
A MeSH descriptor that places a disease in both Cancer and an anatomical topic SHALL establish Cancer as the primary vertical when the descriptor supports every candidate topic and all other supporting descriptors are its ancestors.

#### Scenario: The same tumor descriptor supports Cancer and an anatomical topic
- **WHEN** a group uses the primary Cancer vertical rule
- **THEN** the preview lists the exact descriptor and all supported topics and binds them to its digest

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
