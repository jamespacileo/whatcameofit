# Spec Delta

## Purpose

States what a paper's index record says of the paper itself (its kind, journal, year, whether it was a study in people or in animals, whether it is retracted) and which papers a trial's registry record names as its results, so that a claim's papers can be weighed without opening each one.

## ADDED Requirements

### Requirement: Results papers come from the trial's registry record
For each approved trial, the papers its registry record lists as reporting its results SHALL be attached to that trial by rule, with no search and no model. A paper the record lists as background reading SHALL NOT be attached. Each attachment SHALL say whether the sponsor listed the paper or the registry linked it by the trial's number.

#### Scenario: Trial whose sponsor listed a results paper
- **WHEN** a trial's record lists one paper as a result and four as background
- **THEN** one paper is attached to the trial, marked as listed by the sponsor

#### Scenario: Paper linked by the registry
- **WHEN** a trial's record carries a paper the registry linked from the trial's number
- **THEN** the paper is attached to the trial, marked as linked by the registry

#### Scenario: Reference with no PubMed number
- **WHEN** a results reference in a trial's record has no PubMed number
- **THEN** no paper is attached for it

### Requirement: One paper per identifier
The export SHALL list, for each published claim, each paper the claim page shows once, identified by its DOI or, when it has none, by its PubMed number. A paper SHALL carry every role it plays for the claim: the origin paper, a follow-up paper, a results paper of a named trial, or related research.

#### Scenario: Origin paper that a trial also lists
- **WHEN** a claim's origin paper is also listed as a result by one of its trials
- **THEN** the export lists the paper once, with both roles and the trial's identifier

#### Scenario: Paper behind a rejected event
- **WHEN** the only reason to list a paper is a follow-up event an operator rejected
- **THEN** the export does not list the paper

### Requirement: Facts are read from the index record by rule
Paper facts SHALL be read by fixed rules from the paper's stored index record. No model SHALL be asked. A fact the record does not state SHALL be absent and SHALL NOT be inferred from the paper's title or abstract.

#### Scenario: Record with no index terms yet
- **WHEN** a recently published paper's record carries no subject headings
- **THEN** the paper's facts say nothing about whether it studied people or animals

### Requirement: Kind of publication
A paper's facts SHALL state, as codes, each kind of publication its record gives among: randomised trial, clinical trial, meta-analysis, systematic review, review, observational study, case report, preprint, comment, correction, retraction notice, and article. The codes SHALL be in that order, so the first is the most specific.

#### Scenario: Report of a Phase 3 randomised trial
- **WHEN** a record gives the publication types randomised controlled trial, Phase 3 clinical trial and journal article
- **THEN** the facts carry randomised trial, clinical trial and article, in that order

#### Scenario: Preprint
- **WHEN** a record gives the publication type preprint
- **THEN** the facts carry preprint

### Requirement: Where and when it appeared
A paper's facts SHALL state its title, the journal's name and its year of publication as the record gives them, and whether the record marks it open access.

#### Scenario: Paper in a journal
- **WHEN** a record gives a journal title, a first publication date in 2021 and an open access mark
- **THEN** the facts carry that title, 2021 and open access

### Requirement: Studied in people or in animals
A paper's facts SHALL state whether its record's subject headings say the study was in people, in animals, or both. The facts SHALL state nothing when the record has no subject headings or names neither.

#### Scenario: Study in mice
- **WHEN** a record's headings include "Animals" and "Mice" and not "Humans"
- **THEN** the facts state a study in animals

#### Scenario: Study in people and animals
- **WHEN** a record's headings include both "Humans" and "Animals"
- **THEN** the facts state both

#### Scenario: Laboratory study with neither heading
- **WHEN** a record's headings include neither "Humans" nor "Animals"
- **THEN** the facts state neither

### Requirement: Retracted papers are marked
A paper's facts SHALL state that it is retracted when its record marks it a retracted publication. The mark SHALL NOT change a claim's status unless the paper is the origin paper, whose retraction is already an evidence event.

#### Scenario: Retracted results paper
- **WHEN** a trial's results paper is marked retracted in its record
- **THEN** the paper's facts state that it is retracted and the claim's status is unchanged

### Requirement: The stored record holds no abstract and no author
The record a paper's facts are read from SHALL be stored with the time it was fetched. Before it is stored, its abstract, author names, author identifiers and affiliations SHALL be removed. Paper facts SHALL NOT carry an author, an affiliation or any text from an abstract.

#### Scenario: Record with an abstract and eleven authors
- **WHEN** a paper's record is stored for its facts
- **THEN** the stored record has no abstract and names no author

### Requirement: Facts carry the date their record was read
Each paper's facts SHALL carry the time their record was fetched. A paper the index does not hold SHALL be listed with its identifier and link only.

#### Scenario: Paper the index does not hold
- **WHEN** a results paper's PubMed number returns no record
- **THEN** the paper is listed with its number and link and carries no facts

### Requirement: Paper facts do not change the status
Paper facts and results papers SHALL NOT be inputs to a claim's status. A claim's status and the events that explain it SHALL be the same with and without them.

#### Scenario: Claim with no trial and a paper of a study in people
- **WHEN** a preclinical-only claim gains a results paper tagged as a study in people
- **THEN** the claim's status and its explaining events are unchanged
