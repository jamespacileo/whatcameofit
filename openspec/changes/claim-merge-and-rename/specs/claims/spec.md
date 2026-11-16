# Claims: merging duplicates and renaming an intervention

## ADDED Requirements

### Requirement: Merging duplicate claims
The operator SHALL be able to merge one claim into another that stands for the same intervention and indication, giving a reason. The merge SHALL move to the kept claim the merged claim's source articles with their promises and reported statements, its link-lead pointers, and the papers, organisations and people a source article named, and SHALL add the merged intervention's name and synonyms to the kept intervention's synonyms. Nothing the kept claim already has SHALL be doubled. The merged claim SHALL NOT be deleted: it SHALL be archived with the reason, SHALL point at the kept claim, SHALL NOT be unarchived, and SHALL NOT count as a claim for an intervention in any duplicate check. The merge SHALL record who decided it: the operator or an assistant. A merge that is refused SHALL change nothing.

#### Scenario: Duplicate claim merged
- **WHEN** the operator merges a claim for "VSV-EBOV" into the claim for "Ervebo", both for "Ebola virus disease", with a reason
- **THEN** the kept claim has both claims' articles, promises and reported statements, "VSV-EBOV" is a synonym of its intervention, and the merged claim is archived with the reason and points at the kept claim

#### Scenario: Merge decided by an assistant
- **WHEN** an assistant merges two claims with `--as-assistant`
- **THEN** the merge is recorded as decided by an assistant, not by the operator

#### Scenario: Named entities are not doubled
- **WHEN** both claims name the company "Merck" and the merged claim also names a paper the kept claim lacks
- **THEN** the kept claim has one "Merck" and gains the paper

#### Scenario: New claim for a merged claim's name
- **WHEN** an operator adds a claim for "VSV-EBOV" and "Ebola virus disease" after the merge
- **THEN** the claim is not created and the operator is told the slug of the kept claim

#### Scenario: Duplicate named by a description
- **WHEN** the merged claim's intervention is a description, a dose or carries brackets
- **THEN** the merge is refused naming the entry rule, unless the operator gives `--drop-name`, and then that name does not become a synonym

### Requirement: A merge leaves registry evidence to be found again
A merge SHALL NOT move or copy the merged claim's matches on its intervention or any of its evidence events. They SHALL stay with the merged claim. The kept claim's registry search SHALL be marked due, so that every event behind the kept claim's status was found for the kept claim. The merge SHALL tell the operator which approved registry records of the merged claim's intervention the kept claim does not hold approved.

#### Scenario: Registry evidence is found again, not moved
- **WHEN** the merged claim has an approved match on trial NCT02503202 with a registered event, and the kept claim has no match on that trial
- **THEN** after the merge the match and the event still belong to the merged claim, the kept claim's registry search is due, and the operator is told to look for NCT02503202 after the search

### Requirement: Merges that are refused
A merge SHALL be refused when the two claims' indications differ, ignoring letter case and spacing, unless the operator states that the difference is accepted. A merge SHALL be refused when the kept claim is archived or rejected, when the merged claim was already merged, and when either claim is awaiting audit unless the operator states that explicitly. A merge SHALL be refused when a third claim stands for one of the merged intervention's names and the kept claim's indication.

#### Scenario: Different indications
- **WHEN** the operator merges a claim for "prevention of Ebola virus disease" into a claim for "Ebola virus disease" without `--different-indication-accepted`
- **THEN** the merge is refused, both indications are named, and nothing is changed

#### Scenario: Kept claim is archived
- **WHEN** the operator merges a claim into an archived claim
- **THEN** the merge is refused

#### Scenario: Claim awaiting audit
- **WHEN** the operator merges a claim that is awaiting audit without `--awaiting-audit-accepted`
- **THEN** the merge is refused and the claim awaiting audit is named

### Requirement: Renaming an intervention
The operator SHALL be able to correct the name of a claim's intervention. The old name SHALL be kept as a synonym unless the operator states that it is a description, and then it SHALL be dropped. The new name SHALL be refused, with the rule named, when it carries brackets, a dose, schedule or form, or its maker, or when it is a description. The new name SHALL be refused when another claim stands for it and the claim's indication, and the refusal SHALL give the merge command for the two claims. The rename SHALL record the old name, the new name and who decided it.

#### Scenario: Intervention renamed
- **WHEN** the operator renames "VSV-EBOV" to "rVSV-ZEBOV-GP"
- **THEN** the intervention is called "rVSV-ZEBOV-GP" and "VSV-EBOV" is one of its synonyms

#### Scenario: Old name is a description
- **WHEN** the operator renames "treatment for Guillain-Barre syndrome" to "ANX005" with `--old-is-description`
- **THEN** the intervention is called "ANX005" and the old name is not a synonym

#### Scenario: New name breaks an entry rule
- **WHEN** the operator renames an intervention to "targeted thermal therapy (TTT)"
- **THEN** the rename is refused and the operator is told a name carries no brackets

#### Scenario: New name is another claim's
- **WHEN** the operator renames an intervention to a name another claim has for the same indication
- **THEN** the rename is refused and the operator is given the `claim merge` command for the two claims

### Requirement: Registry search due after a merge or a rename
A rename SHALL mark the claim's registry search as due, and a merge SHALL mark the kept claim's. `thenwhat prepare --due` SHALL prepare every claim whose registry search is due and that was not merged into another. A registry search of the claim that succeeds SHALL clear the mark.

#### Scenario: Search due after a rename
- **WHEN** an approved claim's intervention was renamed and the operator runs `thenwhat prepare --due`
- **THEN** that claim's registries are searched, and claims that are neither due nor named are not

## MODIFIED Requirements

### Requirement: Claim slug
Each claim SHALL have a unique slug made of lowercase letters, digits and hyphens, at most 60 characters long. A slug SHALL NOT change after the claim has been published, with one exception: a rename of the claim's intervention MAY, when the operator asks, make the slug again by rule from the new name. The slug the claim had SHALL then stay taken, SHALL NOT be given to another claim, and its address SHALL lead to the claim.

#### Scenario: Duplicate slug
- **WHEN** an operator creates a claim with a slug that another claim already uses
- **THEN** the claim is not created and the operator is told the slug is taken

#### Scenario: Slug change after publication
- **WHEN** an operator tries to change the slug of a claim that has been published with `claim rename-slug`
- **THEN** the change is refused

#### Scenario: Slug made again
- **WHEN** the operator renames a published claim's intervention with `--reslug`
- **THEN** the claim has the slug the rule makes from the new name and its indication, and no new claim can take the old slug

#### Scenario: Rule's slug belongs to another claim
- **WHEN** the slug the rule makes from the new name is another claim's, or was another claim's
- **THEN** the rename is refused and nothing is changed
