# Spec Delta

## ADDED Requirements

### Requirement: What the registry lists, beside the approach
The export SHALL carry, for a claim whose approved trials list its intervention under exactly one registry intervention type that maps to the claim's approach, that type and the number of trials that list it, as codes, whoever set the approach. For any other claim it SHALL carry none. A claim page SHALL state it beside the approach label, in the site's own wording, and SHALL NOT say whether the intervention works or is available.

#### Scenario: Registry supports the approach
- **WHEN** a reader opens a claim whose approach is drug and whose 3 approved trials list its intervention as a drug
- **THEN** the page shows the label for drug and states that the registry lists the intervention as a drug in 3 trials

#### Scenario: Approach the registry does not support
- **WHEN** a reader opens a claim whose approach an operator set to gene therapy and whose trials list the intervention as a drug
- **THEN** the page shows the label for gene therapy and nothing about the registry's type

#### Scenario: Claim with no approach
- **WHEN** a reader opens a claim with no approach
- **THEN** the page shows nothing about the registry's type

#### Scenario: Registry type without site wording
- **WHEN** the export carries a registry type the site has no words for
- **THEN** the site build fails and names the type

### Requirement: Clinical index
The site SHALL have a clinical index at `/clinical` that lists the top categories of the MeSH tree under which at least one published claim falls, each with the number of published claims at or below it. A category with no published claim SHALL NOT be listed. The page SHALL say that the categories are MeSH's and that the reader-friendly topics are at the topics page.

#### Scenario: Top category with claims
- **WHEN** 161 published claims have a clinical category at or below "Neoplasms"
- **THEN** the index lists "Neoplasms" with the count 161

#### Scenario: Claim under two top categories
- **WHEN** a published claim's category sits under two top categories
- **THEN** it is counted once under each

#### Scenario: Top category with no claim
- **WHEN** no published claim falls under a top category
- **THEN** the index does not list it

#### Scenario: A category comes only from the checked condition

- **WHEN** a filed claim has an approved condition reading and no trial or paper supporting that category
- **THEN** the clinical index identifies a checked condition term as a possible source and does not imply that every assignment was indexed from a trial or paper

### Requirement: Clinical category page
Each MeSH category at or above a published claim's clinical category SHALL have a page at `/clinical/{descriptor identifier}`. It SHALL show the category's MeSH name, every broader category it sits under, its narrower categories that have published claims with their counts, and the published claims at or below it with their statuses. A claim under several narrower categories SHALL be listed once.

#### Scenario: Category in two places
- **WHEN** a reader opens the page for "Obesity", which sits under two broader categories
- **THEN** the page links to both broader categories

#### Scenario: Claims at and below
- **WHEN** 4 published claims have the category "Dementia" and 20 have narrower ones
- **THEN** the page lists 24 claims with their statuses and the narrower categories with their counts

#### Scenario: Category with no published claim
- **WHEN** a category has no published claim at or below it
- **THEN** it has no page and no link leads to it

### Requirement: Clinical categories on the claim page
A claim page SHALL list the claim's clinical categories by their MeSH names, each linking to its category page, and SHALL say for each which of the claim's trials and papers gave it. A claim with no clinical category SHALL show no such list and no placeholder. The categories SHALL NOT be worded as a diagnosis, as who a treatment is for, or as advice.

#### Scenario: Category from a trial and a paper
- **WHEN** a reader opens a claim whose category "Psoriasis" came from one trial and one paper
- **THEN** the page shows "Psoriasis" linking to its category page, and names that trial and that paper as its source

#### Scenario: Category from the reading of the claim's condition
- **WHEN** a reader opens a claim whose category "Psoriasis" came from the reading of its own condition, scored 0.93
- **THEN** the page says the category is what the claim's own condition was read as, and shows the score 0.93

#### Scenario: Claim with no category
- **WHEN** a reader opens a claim with no clinical category
- **THEN** the page shows no clinical category list

### Requirement: Clinical pages credit the vocabulary
Every page that shows a MeSH category SHALL credit "Medical Subject Headings (MeSH), U.S. National Library of Medicine", state the MeSH year the categories were read from, and say that NLM does not endorse the site.

#### Scenario: Credit on a category page
- **WHEN** a reader opens any clinical category page
- **THEN** the page carries the credit line, the MeSH year and the statement that NLM does not endorse the site

#### Scenario: Export without a MeSH year
- **WHEN** the export carries clinical categories and no MeSH year
- **THEN** the site build fails and says so

### Requirement: Clinical browse is reachable
The clinicians page and the topics page SHALL each link to the clinical index, and the sitemap SHALL list the clinical index and every clinical category page.

#### Scenario: From the clinicians page
- **WHEN** a reader opens the page for clinicians
- **THEN** it links to the clinical index

#### Scenario: Sitemap
- **WHEN** the site is built with 300 clinical category pages
- **THEN** the sitemap lists the clinical index and all 300
