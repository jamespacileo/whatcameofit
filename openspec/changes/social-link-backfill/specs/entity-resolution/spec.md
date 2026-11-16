## ADDED Requirements

### Requirement: A rule's trial approvals can be scored again
On request, resolving a claim SHALL score again, with the question, thresholds and rule of a first resolution, each trial match a rule approved that the registry search still returns, and SHALL let the rule decide it again. A match a person or an assistant decided SHALL be left as it is. A match the rule no longer approves SHALL wait for review, or be rejected by the rule when it scores under the rejection threshold, and the claim's status SHALL be derived again. Nothing SHALL be decided until every match is scored.

#### Scenario: A rule's approval no longer stands
- **WHEN** a trial a rule approved is scored again and is read as the intervention studied for something else
- **THEN** the match waits for review, the events read from it are rejected by the rule, and the claim's status no longer rests on that trial

#### Scenario: A rule's approval stands
- **WHEN** a trial a rule approved is scored again at or above the approval threshold for the claim's indication
- **THEN** the match stays approved by the rule and its events are unchanged

#### Scenario: A decision by a person or an assistant
- **WHEN** a claim's trial match was approved by a person or an assistant
- **THEN** it is not scored again and its events are unchanged

#### Scenario: A scoring that fails
- **WHEN** the scoring of a claim's rule approvals fails part of the way
- **THEN** every approval and event is as it was

### Requirement: What a re-scoring withdraws and leaves is reported
For a match the rule no longer approves, the events read from it that a rule approved or that still wait SHALL be rejected by the rule; an event a person or an assistant decided SHALL be left and reported. A rule-approved trial the search no longer returns SHALL stay approved and be reported. The result SHALL name the trials now waiting, the trials rejected, the trials not returned and the events left.

#### Scenario: An event decided by a person or an assistant
- **WHEN** a match is no longer approved and one of its events was approved by an assistant
- **THEN** that event stays approved and the result names it

#### Scenario: An approved trial the search no longer returns
- **WHEN** a rule approved a trial for a claim and the registry search for the claim no longer returns it
- **THEN** the match stays approved, it is not scored, and the result names it

### Requirement: A trial the intervention is in without being what it tests is its own answer
The question asked about a trial record SHALL offer, beside a match, another indication and not a match, the answer that the claim's intervention is in the record but is not what the trial tests as a treatment for the indication: it is the comparator or control for something else under test, it is given to every arm alongside what is tested, or it has another role in the trial, such as the anaesthetic for a procedure. A record read so SHALL NOT be approved by rule, whatever its score. The review queue and the site SHALL say that it was read so. The live lookup SHALL ask the same question with the same answers. An active comparator is not tested: in a head-to-head trial of another drug against the claim's drug, the trial's phase and outcome belong to the other drug's claim. For a claim whose intervention is a combination, the combination is what is tested when the arms differ in a part of it.

#### Scenario: Comparator or background treatment
- **WHEN** a trial gives the claim's drug to every arm as the anaesthetic for the procedure it tests, and the record is read as in the trial but not what is tested
- **THEN** the match is not approved by rule and the review queue says how it was read

#### Scenario: Active comparator in a head-to-head trial
- **WHEN** a trial tests another drug against the claim's drug as its active comparator
- **THEN** the record is read as in the trial but not what is tested, and is not approved by rule for the claim

#### Scenario: The claim's drug is the treatment on trial
- **WHEN** a trial's arms differ in whether patients receive the claim's drug for the claim's condition
- **THEN** the record can be read as a match and approved by rule as before

### Requirement: A combination is searched for all its treatments together
When the intervention's name or one of its other names joins several treatments ("plus", "with", "and", "in combination with", "combined with", "+" or "/"), the registry search SHALL also look for every one of those treatments at once, each part in brackets and the parts joined by AND, under the same rules as a name. The name as written SHALL still be searched. Every trial found is a candidate scored like any other; finding it by the parts does not make it a match.

#### Scenario: A combination
- **WHEN** a claim's intervention is "aspirin plus avelumab"
- **THEN** the registry is searched for "aspirin plus avelumab" and for "(aspirin) AND (avelumab)", and a trial the second search finds becomes a candidate

#### Scenario: One treatment
- **WHEN** a claim's intervention is "semaglutide"
- **THEN** only its names, phrases and codes are searched, as before

### Requirement: A treatment is also searched by its substance's name
The registry of substances SHALL be asked for each of the intervention's names and, where a name carries a dose or schedule, for its core name too ("semaglutide 2.4 mg" as "semaglutide"). When it lists those names under one substance, the registry search SHALL also search the name it gives that substance, as a name, unless it equals a name already searched. A brand such as Mosquirix, Aduhelm or Wegovy then finds the trials filed under the substance. Every trial found is a candidate scored like any other.

#### Scenario: A brand name and its substance
- **WHEN** a claim's intervention is a brand that the registry of substances lists under a substance with another name
- **THEN** the trial registry is searched for the brand and for the substance's name, and a trial found by the substance's name becomes a candidate

## MODIFIED Requirements

### Requirement: Broad names are searched within the indication
When the registries are searched for a claim, the search SHALL be narrowed by the claim's indication, so that a broad intervention name returns trials for that condition. A name that still returns more than a hundred trials within the indication SHALL contribute the registry's first page there, its hundred most relevant trials, each scored like any candidate; no further page is asked for. A search phrase that does so SHALL contribute none, as a phrase is broader than a name. A name or phrase with no trial within the indication SHALL contribute none.

#### Scenario: Broad intervention name
- **WHEN** the intervention is "CAR-T cell therapy" and the indication is stiff person syndrome
- **THEN** the search returns trials of CAR-T cell therapy in stiff person syndrome, not every CAR-T trial

#### Scenario: An established drug with many trials for the condition
- **WHEN** a claim is about buprenorphine for opioid use disorder and the registry holds hundreds of such trials
- **THEN** the hundred the registry ranks first within the condition become candidates, and the claim does not read "no trial record found" for want of them

#### Scenario: Name that identifies nothing
- **WHEN** a search phrase still returns more than a hundred trials within the indication, or a name or phrase returns none
- **THEN** it contributes no candidates
