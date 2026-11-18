# clinical-classification Specification

## Purpose
Gives every claim its clinical categories in a standard medical hierarchy (MeSH), with the records each came from, so that clinicians can browse claims by condition in their own terms. It also maps those categories to the reader-friendly topics, so that the friendly filing can be derived from the clinical one and the two can be compared.

## Requirements

### Requirement: Clinical categories from approved trials
A claim's clinical categories SHALL include every MeSH descriptor that an approved trial of the claim lists as a condition term in its registry record. Broader terms the registry lists as ancestors SHALL NOT count as the claim's own categories. A trial whose match is not approved SHALL give none. No model SHALL take part.

#### Scenario: Trial with a condition term
- **WHEN** a claim's approved trial lists the MeSH condition term "Alzheimer Disease"
- **THEN** "Alzheimer Disease" is one of the claim's clinical categories

#### Scenario: Ancestor is not a category
- **WHEN** the same record lists "Dementia" only as an ancestor
- **THEN** "Dementia" is not one of the claim's own categories

#### Scenario: Candidate trial
- **WHEN** a trial is matched to the claim as a candidate and not approved
- **THEN** its condition terms give the claim no clinical category

#### Scenario: A once-approved trial match is rejected

- **WHEN** an approved trial match is rejected while its approved historical evidence event remains
- **THEN** the trial ceases to supply clinical categories or provenance on either export path. Independently supported categories remain

#### Scenario: A newer trial snapshot removes a condition

- **WHEN** successive snapshots for one approved trial give different conditions
- **THEN** only the current snapshot supplies that trial's categories, regardless of the order of the historical events

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

#### Scenario: A definitive negative paper heading accompanies usable evidence

- **WHEN** a paper heading has no descriptor in the current vocabulary and the claim has independently supported categories
- **THEN** a fresh session still exports the known categories. A pending or failed lookup remains distinguishable from the completed negative result

### Requirement: Clinical categories from the claim's checked condition term
A claim's clinical categories SHALL also include each MeSH descriptor that an approved term check read as the claim's own condition. The category SHALL carry the score of that reading. A term read as broader than the condition, and a reading that is not approved, SHALL NOT give a category. This SHALL apply to every claim alike, whether or not a trial or a paper gives it a category.

#### Scenario: Claim with a checked condition term
- **WHEN** a claim has no approved trial and its condition was read as "Psoriasis" with a score of 0.93 and approved by rule
- **THEN** "Psoriasis" is one of the claim's clinical categories, from that reading, with the score 0.93

#### Scenario: Term read as broader
- **WHEN** the term check read "Skin Diseases" as broader than the claim's condition
- **THEN** "Skin Diseases" is not one of the claim's own categories

#### Scenario: Reading not approved
- **WHEN** a reading of the claim's condition scored below the approval threshold and waits
- **THEN** it gives the claim no clinical category

#### Scenario: A trial and the reading agree
- **WHEN** an approved trial lists "Psoriasis" and the claim's condition was also read as "Psoriasis"
- **THEN** the claim has the one category "Psoriasis", naming both the trial and the reading

### Requirement: Each category names the records that gave it
A claim's clinical category SHALL record every approved trial, approved paper and approved reading of its condition that gave it. The categories SHALL be derived from the stored records each time they are read, and SHALL be the same whichever store they are read from. A category SHALL NOT be entered by hand.

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
- **THEN** the pipeline names the missing records, and the export carries that claim's categories as not yet read, shows none of them, counts the claim, and publishes everything else

#### Scenario: Descriptor the vocabulary no longer holds
- **WHEN** NLM answers that a descriptor does not exist in the current year
- **THEN** the claim keeps the category with the year it was last read in, and the pipeline lists it as retired

#### Scenario: A parent descriptor has an unrelated placement

- **WHEN** a disease reaches a parent with several tree numbers and only one shares its branch
- **THEN** the export and browse hierarchy follow compatible tree-number prefixes. Other placements of that parent contribute no ancestor on this path

#### Scenario: A stored descriptor changes in a new vocabulary year

- **WHEN** a new MeSH year changes one previously stored placement and retires another descriptor
- **THEN** refresh updates the changed placement and identifies the retired descriptor with its last known year

#### Scenario: Preparation first discovers an approved condition term

- **WHEN** normal preparation approves a new condition term after trial evidence was fetched and NLM is available
- **THEN** the first subsequent export includes the required ancestry without a separate tree command

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
The pipeline SHALL report, on request, for all unarchived claims: how many have a derived topic in the group of their vertical (agrees), how many of those rest only on the reading of the claim's own condition, how many have derived topics and none in that group (disagrees), how many have none to compare and why, how many have more than one derived topic, and the count per topic. It SHALL read stored records only.

#### Scenario: Counts
- **WHEN** an operator asks for the comparison over 970 claims
- **THEN** the report gives the four counts, which sum with "none to compare" to 970, and the number of claims under each topic

#### Scenario: Specific vertical in a derived group
- **WHEN** a claim is filed under dementia and its derived topics include "Brain and nerves"
- **THEN** it counts as agrees

#### Scenario: Nothing to compare
- **WHEN** a claim has no clinical category, or none that a topic covers
- **THEN** it counts as none to compare, under the one of the two that applies

#### Scenario: Independent evidence supports a different topic

- **WHEN** only a checked condition term supports the agreeing group and a trial supports an unrelated group on the same claim
- **THEN** the comparison counts the agreement as term-only. A trial supporting the agreeing group instead counts as independent evidence

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
