# Spec Delta

## ADDED Requirements

### Requirement: A claim named in other words for the same condition is a candidate
When a read names a treatment, every claim whose intervention name or synonym shares a telling word with one of the read's names, and whose condition shares a word with the read's, SHALL be a candidate of the same-claim decision. A telling word says which treatment: it is not on the checked-in list of words many treatments carry, such as "therapy" or "vaccine". A rejected, archived or merged claim SHALL NOT be a candidate. Being a candidate joins nothing: only the decision joins.

#### Scenario: A transplant named in other words
- **WHEN** a claim exists for "Genetically modified pig kidney transplant" for end-stage kidney failure, and a read names "gene-edited pig kidney transplant" for kidney failure
- **THEN** that claim is offered to the same-claim decision, and the article is added to it when the decision says it is the same claim

#### Scenario: A name written with other punctuation
- **WHEN** a claim exists for "RTS,S/AS01" for malaria and a read names "RTS,S" for malaria
- **THEN** that claim is a candidate

#### Scenario: Only a word many treatments carry is shared
- **WHEN** a claim exists for "Janssen COVID-19 vaccine" for COVID-19 and a read names "Novavax vaccine" for COVID-19
- **THEN** the claim is not a candidate by this rule

#### Scenario: The same words for another condition
- **WHEN** a claim exists for a pig kidney transplant for kidney failure and a read names a pig heart transplant for heart failure
- **THEN** the claim is not a candidate by this rule

#### Scenario: A rejected or archived claim
- **WHEN** the only claim that shares a telling word and a condition word with the read is rejected or archived
- **THEN** it is not offered, and no decision is asked on its account

### Requirement: Candidates by shared words never displace another candidate
Claims found only by a shared telling word SHALL be added after the candidates the read offers without them, up to eight. Among them, a claim whose condition is the read's or the read's narrowed by words in front SHALL come first, then the claim sharing the most telling words, then the oldest. None SHALL take the place of a claim offered without this rule. The decision's two tests SHALL be unchanged.

#### Scenario: More claims share a word than may be added
- **WHEN** twelve claims share a telling word and a condition word with a read, and three of them are for the read's own condition
- **THEN** eight are offered, those three among them, beside every candidate the read would offer without this rule

#### Scenario: A claim that shares the read's whole name
- **WHEN** eight claims are found only by a shared word and a ninth shares the read's name whole
- **THEN** the ninth is still a candidate, and the eight are candidates beside it

#### Scenario: A split vote
- **WHEN** the decision gives two candidates 0.48 and 0.47
- **THEN** the article is added to neither, as today

### Requirement: The record says how each candidate was found
The lead's detail and the logged decision SHALL say, for the claim an article was joined to, how that claim came to be offered: by a shared name, by its substance's record, by the lead's title, by its slug, by a shared word, or by a shared trial. When a decision was asked and joined nothing, the logged decision SHALL still hold every candidate offered.

#### Scenario: A join through a shared word
- **WHEN** an article is added to a claim that was offered only because it shares a telling word with the read
- **THEN** the lead's detail says the claim was found by a shared word, with both probabilities

### Requirement: A drafted claim that shares an approved trial is asked about again
Once a drafted claim's registries are searched, and before the rule for drafts decides it, every claim that is not rejected, archived or merged, that has an approved match to a registry trial the draft also has an approved match to, and whose condition shares a word with the draft's, SHALL be offered to the same-claim decision, shown each side's treatment, condition and summary. The two tests of the read's decision SHALL apply. The decision SHALL be logged.

#### Scenario: Two names of one treatment
- **WHEN** a claim exists for MM120 for generalized anxiety disorder, a read drafts a claim for LSD for generalized anxiety disorder, and both have an approved match to the same registry trial
- **THEN** the older claim is offered to the same-claim decision when the draft is prepared

#### Scenario: No approved trial in common
- **WHEN** a drafted claim shares no approved registry trial with any other claim
- **THEN** no decision is asked, and the rule for drafts decides the claim as today

#### Scenario: A trial that is only a candidate
- **WHEN** two claims have the same registry trial as a match that is pending or rejected for either
- **THEN** the trial does not make one a candidate of the other

#### Scenario: The same trial for another condition
- **WHEN** two claims share an approved trial and their conditions share no word
- **THEN** neither is offered for the other

### Requirement: A draft the decision joins is rejected and its articles kept
When that decision says the drafted claim is one of the claims offered, the draft SHALL be rejected by rule and its articles, with their promises and reported statements, SHALL be moved to that claim, as for a draft that shares a substance with a claim. The lead that drafted it SHALL be recorded as added to that claim, with both probabilities. The claim joined SHALL keep its headline, summary, names, condition and review state.

#### Scenario: A draft joined after its registries were searched
- **WHEN** the decision gives the older claim 0.9 and none of the candidates 0.1
- **THEN** the draft is rejected by rule, its article is a source article of the older claim, and the lead says it joined that claim after the registry search

#### Scenario: An article the claim already has
- **WHEN** the older claim already has the draft's article address
- **THEN** no second article is added, and the lead points at the claim's own copy

#### Scenario: The decision does not establish the same claim
- **WHEN** the decision gives the older claim 0.45 and none of the candidates 0.55
- **THEN** nothing is joined, and the rule for drafts decides the draft as today

### Requirement: The audit list shows claims that share an approved trial
`thenwhat audit list` SHALL show, beside each claim held awaiting audit, every other claim that shares an approved registry trial with it for a condition that shares a word, with the trials shared. The line SHALL be worded as a pair to look at, never as a duplicate. Showing a pair SHALL change neither claim.

#### Scenario: A held claim that shares a trial
- **WHEN** a claim held awaiting audit shares an approved trial with an approved claim, and the decision did not join them
- **THEN** the list names the other claim and the registry number beside the held claim

#### Scenario: A held claim that shares no trial
- **WHEN** a held claim shares no approved trial with another claim
- **THEN** its line is as it is today
