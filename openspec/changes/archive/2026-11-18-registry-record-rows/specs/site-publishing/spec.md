# Spec Delta

## ADDED Requirements

### Requirement: Registry records are grouped by reading and laid out field by field
Registry records listed on a claim page outside its trials SHALL be shown in groups by how each was read, closest to the claim first: this treatment for this condition; for another condition, patient group or setting; a study it is in but does not test; a study of something else; and last, records scored before the condition was asked. Each group's heading SHALL say its reading once, with how many records it holds. A group SHALL show its first three records and fold the rest under one control that says how many. Each record SHALL show the study's title as written in the registry, then one line of what the record says of the trial in the trials table's words: its phase, its size ("780 people planned") when the record states one, and its state. A possible record's line SHALL open with its match ("Possible match: medium, 78%"), so the uncertainty is read before its phase and state. Then the record and its page here as a trial entry names them: its identifier with its registry's name in sight, linking to the registry, and "View trial details here"; a matched record's match note follows. Then what it is for and the interventions the record names, never worded as what the trial tests, because a record lists comparators and procedures among them. A record SHALL never be worded as recruiting. A record whose fields have not been read SHALL take "Registry record" and its identifier as its title and say on a line of its own that its details have not been read, and SHALL NOT show its one-line summary in their place.

#### Scenario: Possible record read as another condition
- **WHEN** a claim page lists a candidate read as the same treatment for another condition, recruiting, Phase 1, scored 0.31
- **THEN** it sits under "Read as this treatment for another condition, patient group or setting", its title leads, its line reads "Possible match: low, 31%", "Phase 1", "120 people planned" and "Under way", then "NCT00000077 at ClinicalTrials.gov" and "View trial details here", and its interventions are under "Named in the record"

#### Scenario: Possible record not yet read into fields
- **WHEN** a candidate's record is null in the export
- **THEN** the row's title is "Registry record NCT00000077", its line reads its possible match, then "Details not read from the registry yet" and its identifier, and no summary is shown

#### Scenario: Group of more than three records
- **WHEN** a group holds five records
- **THEN** three are shown and "The other 2 of 5 records" opens the rest

### Requirement: Possible records say once that none counts, and why
Above the possible records the page SHALL say once that none of them is counted in the status and no person has checked them, then the rule that would count one: read as this treatment for this condition with a match at or above the score the export gives for approval by rule, or, when the export gives none, confirmed by a person. It SHALL link to the guide entry on match and confidence. Under a subheading for possible records beneath matched ones, the subheading SHALL NOT say again that they are not counted. The section SHALL have one name in its heading and its section-list entry, and its folded heading, section-list entry and the digest SHALL give how many records it holds, the digest's count of possible records linking to the section.

#### Scenario: Claim with one possible record
- **WHEN** a claim page lists one candidate and no other unplaced record, and the export gives 0.8 as the score for approval by rule
- **THEN** "None of these is counted in the status, and no person has checked them." appears once, followed by "…its match is 80% or more." and a link to "How a match is scored"; the folded heading says "1 possible", and the digest's "1 possible" links to the section

#### Scenario: Possible records when only a person approves a match
- **WHEN** the export gives no score for approval by rule
- **THEN** the note says a record counts only once a person confirms it, and names no percentage

### Requirement: A trial page tells citing claims from possible ones
A trial details page SHALL list the claims that cite the record (by an event or an approved match) apart from the claims it is only a possible match for, which it SHALL list under their own heading with a line saying the match is not counted in those claims' status.

#### Scenario: Trial page reached from a possible match
- **WHEN** one claim cites a trial and another has it only as a candidate
- **THEN** the trial page lists the first under "Claims citing this record" and the second under "Claims this record may be about"

### Requirement: A trial names its registry in sight
A trial entry's identifier SHALL be followed in sight by its registry's name ("NCT05899608 at ClinicalTrials.gov"), the same words a registry record row uses, so the two sections describe a trial in one grammar.

#### Scenario: Trial on ClinicalTrials.gov
- **WHEN** a claim page lists trial NCT00000002 from ClinicalTrials.gov
- **THEN** its entry reads "NCT00000002 at ClinicalTrials.gov" in sight
