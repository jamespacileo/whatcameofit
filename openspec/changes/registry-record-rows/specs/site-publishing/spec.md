# Spec Delta

## ADDED Requirements

### Requirement: Registry records are grouped by reading and laid out field by field
Registry records listed on a claim page outside its trials SHALL be shown in groups by how each was read, closest to the claim first: this treatment for this condition; for another condition, patient group or setting; a study it is in but does not test; a study of something else; and last, records scored before the condition was asked. Each group's heading SHALL say its reading once, with how many records it holds. Each record SHALL show the study's title as written in the registry, then one line with its identifier linking to the registry, its phase, its state in the trial entries' words and its match note, then what it is for and what it tests. A record SHALL never be worded as recruiting. A record whose fields have not been read SHALL show its identifier and say its fields have not been read, and SHALL NOT show its one-line summary in their place.

#### Scenario: Possible record read as another condition
- **WHEN** a claim page lists a candidate read as the same treatment for another condition, recruiting, Phase 1, scored 0.31
- **THEN** it sits under "Read as this treatment for another condition, patient group or setting", its title leads, and its line reads its identifier, "Phase 1", "Under way" and "Match to this claim: low, 31%"

#### Scenario: Possible record not yet read into fields
- **WHEN** a candidate's record is null in the export
- **THEN** the row shows its identifier, "Its registry record has not been read into fields yet." and its match note, and no title or summary
