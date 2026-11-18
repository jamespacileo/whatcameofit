# claims Specification

## Purpose
Holds the claims the site tracks, where a claim is one intervention for one indication, together with the news articles that reported each claim and the timelines those articles promised.

## Requirements

### Requirement: Claim identity
A claim SHALL represent exactly one intervention for one indication. News articles about the same intervention and indication SHALL attach to the same claim, whatever their publication date.

#### Scenario: Later article about an existing claim
- **WHEN** an operator adds a 2021 article about an intervention and indication that already have a claim from a 2018 article
- **THEN** the article is attached to the existing claim and no new claim is created

#### Scenario: Same intervention, different indication
- **WHEN** an operator adds a claim for an intervention that already has a claim for a different indication
- **THEN** a separate claim is created

### Requirement: No duplicate claims
Every claim SHALL record its intervention and its indication. The system SHALL refuse a new claim whose indication equals that of an existing claim and whose intervention equals that claim's intervention by name or by any synonym, ignoring letter case and spacing. The refusal SHALL name the existing claim.

#### Scenario: Second claim for the same intervention and indication
- **WHEN** an operator adds a claim for an intervention and indication that already have a claim
- **THEN** the claim is not created and the operator is told the slug of the existing claim

#### Scenario: Compound known under another name
- **WHEN** an existing claim's intervention has the synonym "TRG-035" and an operator adds a claim for "trg-035" with the same indication
- **THEN** the claim is not created

### Requirement: Claim slug
Each claim SHALL have a unique slug made of lowercase letters, digits and hyphens, at most 60 characters long. A slug SHALL NOT change after the claim has been published, with one exception: a rename of the claim's intervention MAY, when the operator asks, make the slug again by rule from the new name. The slug the claim had SHALL then stay taken, SHALL NOT be given to another claim, and its address SHALL lead to the claim. The claim itself MAY take a former slug of its own back, and no earlier record of a rename SHALL be changed by that.

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

### Requirement: Source articles
A claim SHALL have one or more source articles, each recorded with URL, outlet, title and published date. The same URL SHALL appear at most once per claim.

#### Scenario: Add an article
- **WHEN** an operator adds an article with URL, outlet, title and published date to a claim
- **THEN** the article is listed among the claim's source articles

#### Scenario: Duplicate article URL
- **WHEN** an operator adds an article whose URL is already attached to the claim
- **THEN** no second article record is created and the operator is told the claim already has it

### Requirement: No article text
The system SHALL NOT persist the body text of a news article in any form. Only the URL, outlet, title, published date, a content hash and an archive URL MAY be kept for an article.

#### Scenario: Article stored after extraction
- **WHEN** an article has been added and processed
- **THEN** no stored record contains the article body

### Requirement: Promised timelines
Each timeline promised for a claim SHALL be recorded separately with a short description, the source article it came from, and a parsed date when one can be determined. A claim MAY have zero or more promises.

#### Scenario: Repeated promises
- **WHEN** a 2018 article promises human trials "by 2020" and a 2021 article promises them "by 2024"
- **THEN** the claim has two promises, each linked to its own article

#### Scenario: Year-only promise
- **WHEN** a promise reads "by 2025"
- **THEN** its parsed date is 31 December 2025

#### Scenario: Relative promise
- **WHEN** an article published on 10 March 2018 promises results "within five years"
- **THEN** the parsed date is 10 March 2023

#### Scenario: Unparseable promise
- **WHEN** a promise reads "in the near future"
- **THEN** the description is kept and the parsed date is empty

### Requirement: First reported date
A claim's first reported date SHALL equal the earliest published date among its source articles.

#### Scenario: Earlier article added later
- **WHEN** a claim first reported in 2019 gains a source article published in 2017
- **THEN** the claim's first reported date becomes the 2017 date

### Requirement: Vertical
Each claim SHALL belong to exactly one vertical from a configured set of verticals. Each vertical belongs to one group, as defined by the health-areas capability.

#### Scenario: Unknown vertical
- **WHEN** an operator creates a claim with a vertical that is not in the configured set
- **THEN** the claim is not created and the valid verticals are listed

#### Scenario: Retired vertical
- **WHEN** an operator creates a claim with the retired vertical `pain`
- **THEN** the claim is not created and the valid verticals are listed

### Requirement: Evidence stage at announcement
A claim SHALL be able to carry the stage of evidence at the time of announcement: in vitro, animal, early human or late human. The stage SHALL stay empty until an operator or the separately specified evidence-stage threshold rule confirms it.

#### Scenario: Suggested but unconfirmed stage
- **WHEN** a stage has been suggested for a claim, no operator has confirmed it, and the threshold rule has not confirmed it
- **THEN** the claim's stage is empty

#### Scenario: Eligible stage confirmed by rule
- **WHEN** the enabled evidence-stage rule confirms a sufficiently confident recorded suggestion
- **THEN** the claim carries that stage without marking the suggestion as human-reviewed

### Requirement: Manual and bulk entry
An operator SHALL be able to add claims and source articles one at a time from the command line, or many at once from a CSV file. A CSV import SHALL be all-or-nothing.

#### Scenario: CSV with an invalid row
- **WHEN** an operator imports a CSV file in which row 7 has no URL
- **THEN** nothing is imported and the error names row 7 and the missing field

#### Scenario: Valid CSV
- **WHEN** an operator imports a CSV file in which every row is valid
- **THEN** every claim and article in the file is created

### Requirement: Approach on entry
An operator SHALL be able to give a claim's approach when entering it one at a time or in a CSV file, and to change it later. A CSV row with an unknown approach SHALL fail the whole import.

#### Scenario: CSV with an approach column
- **WHEN** an operator imports a CSV whose rows give the approaches drug and gene therapy
- **THEN** each claim is stored with its approach

#### Scenario: CSV with an unknown approach
- **WHEN** one row of a CSV import gives an approach that is not in the configured set
- **THEN** no claim from the file is created and the row and the valid approaches are named

### Requirement: Merging duplicate claims
The operator SHALL be able to merge one claim into another that stands for the same intervention and indication, giving a reason. The merge SHALL move to the kept claim the merged claim's source articles with their promises and reported statements, its link-lead pointers, and the papers, organisations and people a source article named, and SHALL add the merged intervention's name and synonyms to the kept intervention's synonyms. Nothing the kept claim already has SHALL be doubled. The merged claim SHALL NOT be deleted: it SHALL be archived, SHALL point at the kept claim, and SHALL NOT count as a claim for an intervention in any duplicate check. A claim archived before the merge SHALL keep its archive date and reason. The merge SHALL record its reason, who decided it (the operator or an assistant), and every row it moved. A merge SHALL move a link lead's pointers only: what the lead's read recorded SHALL stay as it was. A merge that is refused SHALL change nothing.

#### Scenario: Duplicate claim merged
- **WHEN** the operator merges a claim for "VSV-EBOV" into the claim for "Ervebo", both for "Ebola virus disease", with a reason
- **THEN** the kept claim has both claims' articles, promises and reported statements, "VSV-EBOV" is a synonym of its intervention, and the merged claim is archived with the reason and points at the kept claim

#### Scenario: Evidence stages differ
- **WHEN** the merged claim has an evidence stage and the kept claim has another, or none
- **THEN** the kept claim's stage is unchanged, the operator is told both, and the record of the merge holds both

#### Scenario: Merge decided by an assistant
- **WHEN** an assistant merges two claims with `--as-assistant`
- **THEN** the merge is recorded as decided by an assistant, not by the operator

#### Scenario: Named entities are not doubled
- **WHEN** both claims name the company "Merck" and the merged claim also names a paper the kept claim lacks
- **THEN** the kept claim has one "Merck" and gains the paper

#### Scenario: Two people with one name
- **WHEN** both claims name a person "A. Researcher"
- **THEN** the two person entities are not joined, and the merged claim keeps its own

#### Scenario: New claim for a merged claim's name
- **WHEN** an operator adds a claim for "VSV-EBOV" and "Ebola virus disease" after the merge
- **THEN** the claim is not created and the operator is told the slug of the kept claim

#### Scenario: Lead that drafted the merged claim
- **WHEN** a link lead's read drafted the merged claim
- **THEN** after the merge the lead points at the kept claim, its read outcome and detail are unchanged, and the record of the merge names the lead and the claim it pointed at

#### Scenario: Duplicate named by a description
- **WHEN** the merged claim's intervention is a description, a dose or carries brackets
- **THEN** the merge is refused naming the entry rule, unless the operator gives `--drop-name`, and then that name does not become a synonym; a synonym of the merged intervention that breaks an entry rule is left out and named to the operator

### Requirement: A merge leaves registry evidence to be found again
A merge SHALL NOT move or copy the merged claim's matches on its intervention or any of its evidence events. They SHALL stay with the merged claim. The kept claim's registry search SHALL be marked due, so that every event behind the kept claim's status was found for the kept claim. The merge SHALL tell the operator which approved registry records of the merged claim's intervention the kept claim does not hold approved.

#### Scenario: Registry evidence is found again, not moved
- **WHEN** the merged claim has an approved match on trial NCT02503202 with a registered event, and the kept claim has no match on that trial
- **THEN** after the merge the match and the event still belong to the merged claim, the kept claim's registry search is due, and the operator is told to look for NCT02503202 after the search

### Requirement: Merges that are refused
A merge SHALL be refused unless the two interventions share a name or synonym, the same record in the registry of substances, or a development code, or the decider states that they are one treatment; the record of the merge SHALL say which. A merge SHALL be refused when the two claims' indications differ, ignoring letter case and spacing, unless the operator states that the difference is accepted. A merge SHALL be refused when the kept claim is archived or rejected, when the merged claim was already merged, and when either claim is awaiting audit unless the operator states that explicitly. A merge SHALL be refused when a third claim stands for one of the merged intervention's names and the kept claim's indication.

#### Scenario: Two different treatments
- **WHEN** the operator merges a claim for one drug into a claim for another drug for the same indication, and nothing stored shows they are one treatment, without `--same-treatment-accepted`
- **THEN** the merge is refused and nothing is changed

#### Scenario: Shown to be one treatment by what is stored
- **WHEN** the two interventions are listed under the same substance record
- **THEN** the merge needs no statement that they are one treatment, and records that the substance record showed it

#### Scenario: Different indications
- **WHEN** the operator merges a claim for "prevention of Ebola virus disease" into a claim for "Ebola virus disease" without `--different-indication-accepted`
- **THEN** the merge is refused, both indications are named, and nothing is changed

#### Scenario: Kept claim is archived
- **WHEN** the operator merges a claim into an archived claim
- **THEN** the merge is refused

#### Scenario: Claim awaiting audit
- **WHEN** the operator merges a claim that is awaiting audit without `--awaiting-audit-accepted`
- **THEN** the merge is refused and the claim awaiting audit is named

### Requirement: A hold for audit follows what it was for
What has not passed an audit SHALL NOT reach the site through a merge or through its undoing. A merge SHALL NOT clear or shorten any claim's hold for audit. When the merged claim is awaiting audit, is still pending or was rejected, the merge SHALL be refused unless the decider states that explicitly, and the kept claim, when it has no hold, SHALL then be held awaiting audit: from the merged claim's hold, or from the time of the merge when the merged claim had none. The operator SHALL be told that the kept claim leaves the site until its audit is cleared. Undoing a merge SHALL NOT release any hold.

#### Scenario: A hold follows what it was for
- **WHEN** a claim awaiting audit is merged, with `--awaiting-audit-accepted`, into a published claim
- **THEN** both claims await audit, the kept claim is left out of the next export, and it is published again only after `thenwhat audit clear`

#### Scenario: Merged claim was never approved
- **WHEN** a pending or rejected claim is merged, with `--awaiting-audit-accepted`, into an approved claim that is not held
- **THEN** the kept claim awaits audit from the time of the merge and is left out of the next export

#### Scenario: Unmerge after the kept claim was held again
- **WHEN** the kept claim's hold from a merge was cleared, the claim was then held again for another reason, and the merge is undone
- **THEN** the kept claim still awaits audit

### Requirement: A merge can be undone
The operator SHALL be able to undo a merge. Undoing SHALL return to the merged claim every row the merge moved, SHALL remove from the kept claim's entities the names the merge added, SHALL make the merged claim stand for its intervention again, unarchived unless it was archived before the merge, and SHALL mark both claims' registry searches due. No hold SHALL be released: the operator SHALL be told when the kept claim still awaits audit. The record of the merge SHALL be kept, with who undid it, when and why. `unarchive` SHALL refuse a merged claim and name the command that undoes the merge.

#### Scenario: Merge undone
- **WHEN** the operator undoes the merge of "VSV-EBOV" into "Ervebo"
- **THEN** the articles, promises, reported statements, link-lead pointers and named entities the merge moved belong to the "VSV-EBOV" claim again, "VSV-EBOV" is no longer a synonym of "Ervebo", and a new claim for "VSV-EBOV" is refused naming the "VSV-EBOV" claim

#### Scenario: Unmerge of a claim that was not merged
- **WHEN** the operator undoes the merge of a claim that is not merged
- **THEN** the command is refused

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
A rename SHALL mark the claim's registry search as due, and a merge SHALL mark the kept claim's. `thenwhat prepare --due` SHALL prepare every claim whose registry search is due and that was not merged into another. A registry search of the claim SHALL clear the mark only when every step of it succeeded and every name could be searched for.

#### Scenario: Search due after a rename
- **WHEN** an approved claim's intervention was renamed and the operator runs `thenwhat prepare --due`
- **THEN** that claim's registries are searched, and claims that are neither due nor named are not
