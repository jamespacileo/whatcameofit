# Spec Delta

## Purpose

Gives every claim its clinical categories in a standard medical hierarchy (MeSH), with the records each came from, so that clinicians can browse claims by condition in their own terms. It also maps those categories to the reader-friendly topics, so that the friendly filing can be derived from the clinical one and the two can be compared.

## ADDED Requirements

### Requirement: Clinical categories from approved trials
A claim's clinical categories SHALL include every MeSH descriptor that an approved trial of the claim lists as a condition term in its registry record. Broader terms the registry lists as ancestors SHALL NOT be stored as the claim's own categories. A trial whose match is not approved SHALL give none. No model SHALL take part.

#### Scenario: Trial with a condition term
- **WHEN** a claim's approved trial lists the MeSH condition term "Alzheimer Disease"
- **THEN** "Alzheimer Disease" is one of the claim's clinical categories

#### Scenario: Ancestor not stored
- **WHEN** the same record lists "Dementia" only as an ancestor
- **THEN** "Dementia" is not stored as the claim's own category

#### Scenario: Candidate trial
- **WHEN** a trial is matched to the claim as a candidate and not approved
- **THEN** its condition terms give the claim no clinical category

### Requirement: Clinical categories from approved papers
A claim's clinical categories SHALL also include each MeSH descriptor that an approved paper of the claim is indexed under as a major topic, when that descriptor sits in the MeSH tree of diseases or of mental disorders. Any other heading of the paper SHALL NOT become a category.

#### Scenario: Claim with no trial
- **WHEN** a claim has no approved trial and an approved paper indexed with the major topic "Periodontitis"
- **THEN** "Periodontitis" is one of the claim's clinical categories

#### Scenario: Heading that is not a condition
- **WHEN** the paper is also indexed under "Humans", "Middle Aged" and the name of a drug
- **THEN** none of those becomes a clinical category

#### Scenario: Heading that is not a major topic
- **WHEN** the paper lists "Diabetes Mellitus" as a heading that is not a major topic
- **THEN** it does not become a clinical category

### Requirement: Each category names the records that gave it
A claim's clinical category SHALL record every approved trial and approved paper that gave it. When the last such record is no longer approved, the category SHALL be removed. A category SHALL NOT be entered by hand.

#### Scenario: Two sources
- **WHEN** a trial and a paper of the claim both give "Psoriasis"
- **THEN** the category "Psoriasis" names both records

#### Scenario: Match no longer approved
- **WHEN** the only trial that gave "Psoriasis" is archived or its match rejected
- **THEN** the claim no longer has the category "Psoriasis"

#### Scenario: Claim with no approved trial or paper
- **WHEN** a claim has no approved trial and no approved paper
- **THEN** it has no clinical category, and the pipeline says so when asked

### Requirement: Categories do not change status or publication
A claim's clinical categories SHALL NOT change its status, its evidence stage, its vertical, or whether and when it is published.

#### Scenario: New category on a published claim
- **WHEN** a published claim gains a clinical category
- **THEN** its status, its vertical and its published date are unchanged

### Requirement: The hierarchy comes from the vocabulary's own records
For every clinical category in use, the pipeline SHALL hold NLM's record of the descriptor, with its tree numbers, and the record of each broader descriptor up to the top of the tree. A descriptor with several tree numbers SHALL be placed under each of its broader descriptors. The pipeline SHALL record the MeSH year each record was read from.

#### Scenario: Descriptor in two places
- **WHEN** "Obesity" has one tree number under nutritional disorders and one under signs and symptoms
- **THEN** it is narrower than both, and a claim with the category "Obesity" is at or below both

#### Scenario: Record not yet read
- **WHEN** a claim has a category whose record or a broader record has not been read
- **THEN** the pipeline names the missing records, and the export is not built until they are read

#### Scenario: Descriptor the vocabulary no longer holds
- **WHEN** NLM answers that a descriptor does not exist in the current year
- **THEN** the claim keeps the category with the year it was last read in, and the pipeline lists it as retired

### Requirement: Topic mapping from clinical categories
A checked-in mapping SHALL name, for each reader-friendly group and vertical, the MeSH descriptors it covers. One topic MAY cover several descriptors, and one descriptor MAY be covered by several topics. A claim's derived topics SHALL be every topic that covers one of its clinical categories or a broader category of one. Every descriptor in the mapping SHALL exist in the vocabulary.

#### Scenario: One topic, several categories
- **WHEN** a topic for weight loss covers "Obesity", "Overweight" and "Weight Loss"
- **THEN** a claim whose only category is "Obesity, Morbid" has that topic among its derived topics

#### Scenario: One claim, several topics
- **WHEN** a claim has the categories "Diabetic Retinopathy", which sits under both eye diseases and diabetes
- **THEN** its derived topics include both the eye topic and the diabetes topic

#### Scenario: Unknown descriptor in the mapping
- **WHEN** the mapping names a descriptor the vocabulary does not hold
- **THEN** the configuration check fails and names the topic and the descriptor

#### Scenario: Category no topic covers
- **WHEN** none of a claim's categories, nor any broader category, is covered by a topic
- **THEN** the claim has no derived topic, and the category is listed as uncovered

### Requirement: Derived topics do not file a claim
Derived topics SHALL NOT change a claim's vertical and SHALL NOT be exported or shown on reader-friendly topic pages. A claim SHALL keep exactly one vertical, filed as before.

#### Scenario: Derived topic differs from the vertical
- **WHEN** a claim filed under "Skin and hair" has the one derived topic "Cancer"
- **THEN** the claim stays under "Skin and hair" and its topic page is unchanged

### Requirement: Measured comparison of derived topics with filed verticals
The pipeline SHALL report, on request, for all unarchived claims: how many have a derived topic in the group of their vertical (agrees), how many have derived topics and none in that group (disagrees), how many have none to compare and why, how many have more than one derived topic, and the count per topic. It SHALL read stored records only.

#### Scenario: Counts
- **WHEN** an operator asks for the comparison over 970 claims
- **THEN** the report gives the four counts, which sum with "none to compare" to 970, and the number of claims under each topic

#### Scenario: Specific vertical in a derived group
- **WHEN** a claim is filed under dementia and its derived topics include "Brain and nerves"
- **THEN** it counts as agrees

#### Scenario: Nothing to compare
- **WHEN** a claim has no clinical category, or none that a topic covers
- **THEN** it counts as none to compare, under the one of the two that applies

### Requirement: Disagreeing claims are listed
The pipeline SHALL list, on request, every unarchived claim whose derived topics disagree with its vertical, with its slug, intervention, indication, filed vertical, derived topics, and the clinical categories that produced them. The list SHALL also be available as tab-separated rows. `thenwhat prepare` SHALL say how many of the claims it handled disagree.

#### Scenario: Rows for the fault tab
- **WHEN** an operator asks for the disagreeing claims as tab-separated rows
- **THEN** each row carries the slug, intervention, indication, filed vertical, derived topics and clinical categories, and no article text

#### Scenario: Prepare reports disagreements
- **WHEN** `thenwhat prepare --pending` handles 40 claims and 3 of them disagree
- **THEN** its summary says so and names the command that lists them

#### Scenario: Nothing disagrees
- **WHEN** no unarchived claim disagrees
- **THEN** the list says so
