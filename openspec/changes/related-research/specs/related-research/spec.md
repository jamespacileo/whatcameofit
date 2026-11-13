# Spec Delta

## Purpose

Finds published papers about a claim's intervention and indication when the article cited none by DOI, scores each one, and shows the approved ones beside the claim without letting them change its status.

## ADDED Requirements

### Requirement: Paper candidates from a literature search
For each claim the system SHALL search the literature for the intervention's name, its other names and its search phrases, each together with the indication. Every paper found SHALL be stored as a candidate match with its source, external identifier, score and a one-line record of title, year, kind of paper and journal. At most twenty papers SHALL be kept per claim, taken in the source's own order of relevance.

#### Scenario: Claim whose article gave no DOI
- **WHEN** resolution runs for a claim with no paper entity and the literature holds four papers on its intervention and indication
- **THEN** four paper candidates are stored for the claim

#### Scenario: Paper found by two terms
- **WHEN** the name and a search phrase both find the same paper
- **THEN** one candidate is stored for that paper

#### Scenario: Search that finds nothing
- **WHEN** no term finds a paper
- **THEN** no candidate is stored and resolution reports that none was found

### Requirement: Paper candidates are scored for the claim
A paper candidate SHALL be scored through a decision with four options: a study of the claim's intervention for the claim's indication, a study of the intervention for another indication, a review or commentary, and unrelated. The probability of the first option SHALL be the candidate's score.

#### Scenario: Review article
- **WHEN** a candidate is a review that mentions the intervention among many others
- **THEN** it scores below a study of the intervention for the claim's indication

#### Scenario: Same intervention, another condition
- **WHEN** a candidate studies the intervention for a different condition
- **THEN** it is shown to the reviewer as being for another indication

### Requirement: Each paper candidate carries its reasons
A paper candidate SHALL carry the reasons found by rule, as codes: the intervention or a search phrase is named in the title, the indication is named in the title or abstract, an author's institution is one the article named, and the paper was published before the claim was first reported. The reasons SHALL be computed without a model.

#### Scenario: Paper from the institution the article named
- **WHEN** the article named a university and a candidate's author is affiliated with it
- **THEN** the candidate carries the reason for a named institution

#### Scenario: Paper with no sign
- **WHEN** a candidate shows none of the signs
- **THEN** it carries no reasons and keeps its score

### Requirement: Paper candidates are decided like other matches
A paper candidate SHALL start as pending and follow the review states, the queue and the rules for rejecting by threshold that apply to trial candidates. A paper candidate SHALL be approved by rule only when its score is at or above a configured threshold and it carries at least one reason. An empty threshold SHALL turn that rule off.

#### Scenario: High score and no reason
- **WHEN** a candidate scores 0.97, the threshold is 0.9 and it carries no reason
- **THEN** it stays pending

#### Scenario: High score with a reason
- **WHEN** a candidate scores 0.97, the threshold is 0.9 and its title names the intervention
- **THEN** it is approved, recorded as decided by a rule

### Requirement: Approved papers do not change the status
An approved paper candidate SHALL NOT be an evidence event and SHALL NOT enter status derivation.

#### Scenario: Claim with papers and no trial
- **WHEN** a claim has three approved paper candidates and no approved trial
- **THEN** its status is what it would be with no paper candidates

### Requirement: Registry numbers in an approved paper become trial candidates
When a paper candidate is approved, each trial registry number its record states SHALL be looked up and stored as a trial candidate for the claim's intervention, scored as any trial candidate is. A paper that states more than three registry numbers SHALL contribute none.

#### Scenario: Trial report
- **WHEN** an approved paper states one registry number that the claim has no candidate for
- **THEN** that trial is stored as a pending trial candidate and scored

#### Scenario: Review listing many trials
- **WHEN** an approved paper states five registry numbers
- **THEN** no trial candidate is created from it

### Requirement: An origin paper is suggested
For a claim with approved paper candidates and no origin paper, the system SHALL suggest which approved paper published on or before the first reported date is the one first reported on, or none. The suggestion SHALL come from a decision, SHALL be shown in the review queue, and SHALL NOT designate the origin paper by itself.

#### Scenario: One paper predates the report
- **WHEN** a claim has two approved papers, one published a week before the first report and one a year after
- **THEN** only the earlier paper is offered, together with the option of none

#### Scenario: Claim that has an origin paper
- **WHEN** a claim already has an origin paper
- **THEN** no suggestion is made

### Requirement: Paper text is not published
The system SHALL use a paper's abstract only to score and to find reasons and registry numbers. The export and the site SHALL carry a paper's title, year, kind, identifier and link, and no part of its abstract.

#### Scenario: Export of a claim with approved papers
- **WHEN** a claim with an approved paper is exported
- **THEN** the export holds the paper's title and link and no abstract text
