# Spec Delta

## MODIFIED Requirements

### Requirement: Studied in people or in animals
A paper's facts SHALL preserve whether its record carries human or animal subject headings, or both. Public wording SHALL identify these as the index's subject headings, without inferring experiments in living people or animals: headings can also describe the sources of laboratory materials. The facts SHALL state nothing when the record has no subject headings or names neither. These headings SHALL NOT determine the claim's evidence stage or status.

#### Scenario: Study in mice
- **WHEN** a record's headings include "Animals" and "Mice" and not "Humans"
- **THEN** the site identifies the animal subject heading and attributes it to the index

#### Scenario: Laboratory study using extracted human teeth and wool
- **WHEN** its record's headings include both "Humans" and "Animals"
- **THEN** the site identifies both subject headings without saying the treatment was studied in people
- **AND** the independently confirmed laboratory evidence stage remains unchanged

#### Scenario: Study in people and animals
- **WHEN** a record's headings include both "Humans" and "Animals"
- **THEN** the facts retain both and the site identifies them as subject headings

#### Scenario: Laboratory study with neither heading
- **WHEN** a record's headings include neither "Humans" nor "Animals"
- **THEN** the facts state neither
