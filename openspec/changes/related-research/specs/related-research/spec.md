# Spec Delta

## Purpose

Finds published papers about a claim's intervention and indication when the article cited none by DOI, scores each one, and shows the approved ones beside the claim without letting them change its status.

## ADDED Requirements

### Requirement: Paper candidates from a literature search
For each claim the system SHALL search the literature for the intervention's name, its other names and its search phrases, each together with the indication. Every paper found SHALL be stored as a candidate match with its source, external identifier, score and a one-line record of title, year, kind of paper and journal. The system SHALL also search the same terms, without the indication, among papers with an author at each organisation the article named and the organisation registry identified and no one rejected, three organisations at most, published from two years before the first report to a month after it when that date is known. At most twenty papers SHALL be kept per claim: those found under a named organisation first, the ones found under more organisations ahead, then the rest in the source's own order of relevance.

#### Scenario: Claim whose article gave no DOI
- **WHEN** resolution runs for a claim with no paper entity and the literature holds four papers on its intervention and indication
- **THEN** four paper candidates are stored for the claim

#### Scenario: The paper's title shares few words with the report (pipeline)
- **WHEN** the search with the indication does not return the paper a claim's article reports, and the article named two organisations that are identified
- **THEN** one search is sent per organisation, and a paper found under both is stored ahead of one found under one, which is ahead of the papers found with the indication

#### Scenario: No organisation identified
- **WHEN** a claim's article named no organisation that the registry identified
- **THEN** only the search with the indication is sent

#### Scenario: Paper found by two terms
- **WHEN** the name and a search phrase both find the same paper
- **THEN** one candidate is stored for that paper

#### Scenario: Search that finds nothing
- **WHEN** no term finds a paper
- **THEN** no candidate is stored and resolution reports that none was found

### Requirement: Paper candidates are scored for the claim
A paper candidate SHALL be scored through a decision with four options: a study of the claim's intervention for the claim's indication, a study of the intervention for another indication, a review or commentary, and unrelated. The probability of the first option SHALL be the candidate's score.

#### Scenario: Review article
- **WHEN** a candidate is a review that mentions the intervention among many others
- **THEN** it scores below a study of the intervention for the claim's indication

#### Scenario: Same intervention, another condition
- **WHEN** a candidate studies the intervention for a different condition
- **THEN** it is shown to the reviewer as being for another indication

### Requirement: Each paper candidate carries its reasons
A paper candidate SHALL carry the reasons found by rule, as codes: the intervention or a search phrase is named in the title, the indication is named in the title or abstract, an author's institution is one the article named, and the paper was published before the claim was first reported. The reasons SHALL be computed without a model.

#### Scenario: Paper from the institution the article named
- **WHEN** the article named a university and a candidate's author is affiliated with it
- **THEN** the candidate carries the reason for a named institution

#### Scenario: Paper with no sign
- **WHEN** a candidate shows none of the signs
- **THEN** it carries no reasons and keeps its score

### Requirement: Paper candidates are decided like other matches
A paper candidate SHALL follow the review states and the rule for rejecting by threshold that apply to trial candidates. A paper candidate scored at or above the accept threshold for matches SHALL be approved by rule, with no person involved, whether or not it carries a reason. Every paper so approved SHALL be listed. An operator SHALL be able to reject one afterwards. A threshold of zero SHALL turn the rule off.

#### Scenario: Several confident papers
- **WHEN** three candidates score 0.97, 0.9 and 0.85 and the threshold is 0.8
- **THEN** all three are approved, recorded as decided by a rule

#### Scenario: High score and no reason
- **WHEN** a candidate scores 0.97, the threshold is 0.8 and it carries no reason
- **THEN** it is approved and is published with its score and no reasons

#### Scenario: Below the threshold
- **WHEN** a candidate scores 0.5 and the threshold is 0.8
- **THEN** it stays pending and is not published

### Requirement: Approved papers do not change the status
An approved paper candidate SHALL NOT be an evidence event and SHALL NOT enter status derivation.

#### Scenario: Claim with papers and no trial
- **WHEN** a claim has three approved paper candidates and no approved trial
- **THEN** its status is what it would be with no paper candidates

### Requirement: Registry numbers in an approved paper become trial candidates
When a paper candidate is approved, each trial registry number its record states SHALL be looked up and stored as a trial candidate for the claim's intervention, scored as any trial candidate is. A paper that states more than three registry numbers SHALL contribute none.

#### Scenario: Trial report
- **WHEN** an approved paper states one registry number that the claim has no candidate for
- **THEN** that trial is stored as a pending trial candidate and scored

#### Scenario: Review listing many trials
- **WHEN** an approved paper states five registry numbers
- **THEN** no trial candidate is created from it

### Requirement: The origin paper is chosen by rule
For a claim with approved paper candidates and no origin paper, the system SHALL ask a decision which approved paper published on or before the first reported date is the one first reported on, or none. A paper chosen with a probability at or above the accept threshold SHALL become the origin paper, recorded as decided by a rule. An operator SHALL be able to replace or remove it.

#### Scenario: One paper predates the report
- **WHEN** a claim has two approved papers, one published a week before the first report and one a year after
- **THEN** only the earlier paper is offered, together with the option of none

#### Scenario: Confident choice
- **WHEN** the decision chooses a paper with a probability of 0.9 and the threshold is 0.8
- **THEN** that paper becomes the claim's origin paper

#### Scenario: Unsure choice
- **WHEN** the decision's highest probability is 0.5
- **THEN** the claim keeps no origin paper

#### Scenario: Claim that has an origin paper
- **WHEN** a claim already has an origin paper
- **THEN** no decision is asked

### Requirement: Paper text is not published
The system SHALL use a paper's abstract only to score and to find reasons and registry numbers. The export and the site SHALL carry a paper's title, year, kind, identifier and link, and no part of its abstract.

#### Scenario: Export of a claim with approved papers
- **WHEN** a claim with an approved paper is exported
- **THEN** the export holds the paper's title and link and no abstract text

### Requirement: Public on-demand research context
The public lookup SHALL return bibliographic search results and identifiers for organisations explicitly named in the report, in addition to trial candidates. These SHALL be labelled unreviewed search results, separate from claim status and match confidence. The interface SHALL collapse secondary context initially. Missing keys, provider limits and failures SHALL leave trial results available. Old cached results and older extensions SHALL remain compatible.

#### Scenario: A report has related papers and names a university
- **WHEN** OpenAlex finds papers and ROR selects the university's identity
- **THEN** paper titles, metadata and source links and the ROR organisation link are available in collapsed sections, with no status change

#### Scenario: The free allowance cannot be established
- **WHEN** OpenAlex's allowance is exhausted, unknown, exceeds the free budget or has prepaid credit
- **THEN** no charged literature search is sent, a temporary unavailability is shown, and trial lookup and ROR continue

#### Scenario: Repeated research query
- **WHEN** a normalized metadata result is less than seven days old
- **THEN** it is reused without a provider request, including an empty result

#### Scenario: A provider times out or limits access
- **WHEN** an API call or its body takes more than five seconds, or a source responds with a quota error
- **THEN** the optional source stops without retries or alternative accounts and the remaining results are returned

### Requirement: Public discovery does not depend on a citation
Public lookup SHALL derive up to two literature queries about the experimental subject and method, separately from clinical-trial phrases, and up to two explicitly involved named researchers, using the existing extraction call. It SHALL NOT append a future clinical indication to those complete queries or depend on a paper identifier for discovery.

#### Scenario: Laboratory report without a paper link
- **WHEN** a report describes tooth-formation experiments and names a study researcher but supplies no DOI, PMID or paper title
- **THEN** discovery searches the experimental topic with that researcher and returns the relevant paper when the source finds it
- **AND** neither the expected paper identifier nor its title is supplied to extraction or search

#### Scenario: Missing or unhelpful researcher
- **WHEN** a report names no researcher or its researcher-scoped search finds nothing
- **THEN** unscoped experimental-topic searches still run

#### Scenario: Clinical lookup alongside literature discovery
- **WHEN** literature queries or researcher names are added
- **THEN** clinical-trial queries, match scoring and claim status are unchanged

### Requirement: Public discovery follows a bounded search plan
Public lookup SHALL search with each validated quoted researcher name and the first literature query, then up to two unscoped queries. A valid article date SHALL bound publication dates. Missing literature fields SHALL retain the two-query clinical-name fallback. Cache identity SHALL include all search constraints. Results SHALL remain unreviewed, with scoped matches first, deduplicated by work ID and canonical link, and at most twenty returned.

#### Scenario: Same topic with different researcher or date
- **WHEN** a later request uses the same topic with a different researcher or publication-date bound
- **THEN** it does not reuse metadata cached under the earlier constraints

#### Scenario: Scoped results fill the result cap
- **WHEN** scoped searches return twenty unique papers
- **THEN** the bounded unscoped fallbacks still run and no more than twenty papers are returned

### Requirement: Cited papers complement discovery
Public lookup SHALL resolve at most three unique validated DOI/PubMed citations through free singleton lookups and place resolved papers before discovered papers without duplication. A citation's absence SHALL NOT prevent discovery. A 404 SHALL be cached as an empty result; other failures SHALL NOT be cached as misses. Source cooldown, authentication, metadata-only storage, timeout and redirect-refusal rules SHALL apply. Every charged search SHALL retain its free-allowance check.

#### Scenario: Cited paper absent from keyword results
- **WHEN** the article links to a PubMed record that OpenAlex resolves but keyword searches miss
- **THEN** the resolved paper appears first and broader discovery still runs

#### Scenario: Citation lookup fails
- **WHEN** a citation is missing from OpenAlex or its lookup fails without a rate-limit cooldown
- **THEN** discovery remains available and successful sibling results are retained

#### Scenario: Temporary failure followed by a completed keyword search
- **WHEN** a citation lookup fails and a keyword search succeeds
- **THEN** the answer preserves the source's unavailability and its successful results
- **AND** an incomplete OpenAlex answer is neither written to nor reused from the shared result cache
