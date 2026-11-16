# Spec Delta

## ADDED Requirements

### Requirement: Registry records are grouped by reading and laid out field by field
Registry records listed on a claim page outside its trials SHALL be shown in groups by how each was read, closest to the claim first: this treatment for this condition; for another condition, patient group or setting; a study it is in but does not test; a study of something else; and last, records scored before the condition was asked. Each group's heading SHALL say its reading once, with how many records it holds, and each group of possible records SHALL say that none of them counts in the status. Each record SHALL show the study's title as written in the registry, then one line with its identifier and its registry's name in sight, linking to the registry, its phase, its state in the trial entries' words and its match note, then what it is for and the interventions the record names. The interventions SHALL NOT be worded as what the trial tests, because a record lists comparators and procedures among them. A record SHALL never be worded as recruiting. A record whose fields have not been read SHALL take "Registry record" and its identifier as its title and say its details have not been read, and SHALL NOT show its one-line summary in their place. The section's folded heading, its entry in the section list and the digest SHALL give how many records it holds, the digest's count of possible records linking to it.

#### Scenario: Possible record read as another condition
- **WHEN** a claim page lists a candidate read as the same treatment for another condition, recruiting, Phase 1, scored 0.31
- **THEN** it sits under "Read as this treatment for another condition, patient group or setting" and "Not counted in the status: no rule or person has confirmed these matches.", its title leads, its line reads "NCT00000077 at ClinicalTrials.gov", "Phase 1", "Under way" and "Match to this claim: low, 31%", and its interventions are under "Named in the record"

#### Scenario: Possible record not yet read into fields
- **WHEN** a candidate's record is null in the export
- **THEN** the row's title is "Registry record NCT00000077", its line reads "Details not read from the registry yet" and its match note, and no summary is shown
