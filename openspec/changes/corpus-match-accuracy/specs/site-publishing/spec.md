# Spec Delta

## ADDED Requirements

### Requirement: No-trial wording does not imply a human study
Status explanations, topic summaries and guide text for `no_trial_found` SHALL describe the absence of a matched trial record without asserting a study in people. Confirmed first-report evidence SHALL remain separately visible where available. `preclinical_only` explanations SHALL describe confirmed laboratory or animal evidence.

#### Scenario: Claim has an unknown first-report stage
- **WHEN** a claim with no approved trial and no confirmed evidence stage is displayed or counted in a topic summary
- **THEN** its no-trial wording does not say it was studied in people or only in the laboratory

## MODIFIED Requirements

### Requirement: A paper says whether it studied people or animals
A paper's entry SHALL identify its human or animal subject headings as the index's subject headings, not as proof of a study in living participants. It SHALL state nothing when neither heading is recorded. These headings SHALL remain separate from the claim's confirmed evidence stage.

#### Scenario: Paper using extracted human teeth
- **WHEN** a laboratory paper has human and animal subject headings
- **THEN** its entry attributes those headings to the index without saying the treatment was studied in people

#### Scenario: Paper of a study in mice
- **WHEN** a paper's facts include the animal subject heading
- **THEN** its entry identifies that heading and attributes it to the index

#### Scenario: Paper with no statement
- **WHEN** a paper's facts state neither heading
- **THEN** its entry says nothing about human or animal headings

### Requirement: The claim page counts its records in people and in animals
A claim page SHALL count its trial records and papers separately, without deriving a count of human or animal studies from indexing terms. These are counts of records, not independent studies or participants. A paper listed in multiple roles SHALL count once. Missing paper facts SHALL NOT exclude a listed paper. An empty record set SHALL show no count; legacy exports without structured papers SHALL retain their existing display.

#### Scenario: Claim with three trials and one mouse paper
- **WHEN** a claim has three trials and one paper with an animal subject heading
- **THEN** the page states three trial records and one paper

#### Scenario: Laboratory paper with human and animal headings
- **WHEN** a claim has no trial and one paper with both headings
- **THEN** the page states one paper, without implying a human trial

#### Scenario: Claim with no such record
- **WHEN** a claim has neither trials nor papers
- **THEN** the page shows no record count
