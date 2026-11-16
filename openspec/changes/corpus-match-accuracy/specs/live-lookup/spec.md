## Purpose

Associates automatic article and post lookups with existing knowledge cards only when they describe the same claim.

## ADDED Requirements

### Requirement: Independent claims receive separate answers
Several identifiable independent intervention/indication pairs SHALL receive separate matches and card associations, retaining each pair's scores, scope, provenance and uncertainty. Genuine combinations SHALL remain whole; unspecified treatments SHALL not acquire invented identities. One source reading and eligible fetched records SHALL be reused within existing request and deadline limits. Unprocessed claims SHALL remain explicitly unchecked.

#### Scenario: Roundup identifies two independent treatments
- **WHEN** the source separately describes two identifiable treatments and their conditions
- **THEN** each receives its own answer and compatible cards, without combining the treatments or assigning one claim's trial to the other

#### Scenario: A genuine combination and a vague reference coexist
- **WHEN** the source describes a studied two-treatment regimen and an unspecified new drug
- **THEN** the complete regimen remains one claim and the vague reference establishes no invented treatment or match

#### Scenario: Existing work limits prevent complete coverage
- **WHEN** the lookup cannot finish all identified claims within its existing bounds
- **THEN** the answer identifies the unchecked claims and does not imply the whole page was verified

### Requirement: An unspecified drug does not establish treatment identity
Both lookup readers SHALL distinguish a specifically described unnamed intervention from disease and generic drug wording alone. The latter SHALL produce a negative identification without invented products or aliases, term search, scoring or research enrichment. Specific descriptions and reported study identities SHALL remain usable evidence, without automatically establishing a match. Obsolete saved answers SHALL be invalidated; no extra model call SHALL be added.

#### Scenario: Linked article is unavailable and headline names no treatment
- **WHEN** only a headline about a new drug and longer survival for a disease can be read
- **THEN** the reader reports that the treatment could not be identified and no clinical match or card is inferred from the disease alone

#### Scenario: Specific unnamed treatment is described
- **WHEN** a report describes a wrist device applying electrical stimulation to the median nerve for tics without a product name
- **THEN** the descriptive treatment remains eligible for lookup

#### Scenario: Report supplies its study identity
- **WHEN** a report omits the product name but explicitly identifies its reported trial or paper
- **THEN** the existing identifier lookup remains available and any candidate still requires comparison with the reported claim

### Requirement: A tracked linked article is described as deliberately reused
When a post links to an article already in the published index, the shared presenter SHALL say its card is shown without another article read or automatic search. It SHALL retain whether the service or browser read the post, and SHALL NOT describe the skipped read as a failure. Saved answers SHALL receive the correction without invalidation or extra requests.

#### Scenario: Journal short link leads to a tracked article
- **WHEN** a service-read or browser-read post links through `nej.md` and its current robots rules permit the redirect lookup
- **THEN** the existing bounded short-link reader resolves its destination and returns any exact tracked card without reading the article or searching
- **AND** a shortener refusal remains a refusal, with no alternate fetch route

#### Scenario: Browser post links to a tracked source
- **WHEN** a browser-read post returns an exact tracked linked-article answer
- **THEN** its source wording identifies the browser reading and deliberate reuse of the tracked card

#### Scenario: Service post links to a tracked source
- **WHEN** a service-read post returns an exact tracked linked-article answer
- **THEN** its source wording identifies the platform reading without claiming the linked article was unreadable

#### Scenario: Untracked article read is refused
- **WHEN** the article is not tracked and its attempted read is refused
- **THEN** the existing refusal explanation remains

### Requirement: Readings preserve formulation, population and activation roles
Both lookup readers SHALL preserve explicit formulation, route and population constraints. The transient gist supplied to scoring SHALL retain delivery and activation details. The indication SHALL retain the reported target and studied population without inflating surrogate benefits. Only experimental treatments SHALL form combination names; explicitly identified activation agents, adjuvants and supportive care SHALL retain their stated roles.

#### Scenario: Eye insert and oral ingredient
- **WHEN** a report names an intravitreal insert and its active ingredient
- **THEN** the reading retains the insert formulation and does not reduce its product alias to the unrestricted ingredient
- **AND** a trial of the oral ingredient does not become a compatible formulation

#### Scenario: Aging biomarkers in people with a lung disease
- **WHEN** a report measures aging-clock estimates in participants with idiopathic pulmonary fibrosis
- **THEN** the indication retains both the measured aging target and that disease population, without claiming demonstrated longevity or an effect in healthy people

#### Scenario: Treatment requires an activation agent
- **WHEN** the report explicitly says a substance only activates the experimental gene therapy
- **THEN** the intervention remains the gene therapy and the gist retains the activation role
- **AND** a genuine multi-treatment experimental regimen remains a complete combination

### Requirement: Scope corrections replace obsolete saved answers
The scope-reading correction SHALL add no model or source calls to the lookup workflow. Shared and extension storage SHALL invalidate completed answers made before this correction while retaining normal reuse of complete new answers.

#### Scenario: Older reading is saved
- **WHEN** shared or extension storage contains a pre-correction reading
- **THEN** it is not reused and the normal fresh-reading path remains available

#### Scenario: Complete corrected reading is saved
- **WHEN** a complete corrected answer is requested again within its unchanged lifetime
- **THEN** it is reused without repeating model or registry calls

### Requirement: Reused clinical answers use the available publication index
Reused clinical answers SHALL recompute tracked-claim associations using the fresh lookup's whole-intervention and exact-condition comparison. Shared answers SHALL use the current static index; local answers SHALL use the extension's loaded index. Reuse SHALL preserve the clinical reading, trial scores, check time, lifetime and index refresh policy, without repeating model, registry or paper work. Exact source-address responses and non-treatment answers SHALL remain separate.

#### Scenario: A card is published after a clinical answer was saved
- **WHEN** a completed answer names the exact whole intervention and condition of a card newly present in the available index
- **THEN** reuse includes that card without another paid lookup and retains the original check time

#### Scenario: A card is removed or its indication is corrected
- **WHEN** a saved association is absent or no longer matches the available index
- **THEN** the reused answer omits it without changing its trial results

#### Scenario: An available card covers only a component or another setting
- **WHEN** a saved answer concerns a complete regimen for a particular patient setting
- **THEN** reuse does not associate a component card or a card for a different setting

#### Scenario: The service index fails or stalls
- **WHEN** the service cannot obtain its current static index within 500 milliseconds
- **THEN** it still returns the completed saved clinical answer, with no unverified card associations

### Requirement: Mentioned records do not imply a possible match
The site and extension SHALL count and lead with valid scored `match` candidates at or above the existing display threshold. Other cited records SHALL appear in a separate collapsed section marked as unestablished matches, retaining title, link, confidence and citation explanation. They SHALL NOT suppress the no-match notice or increase the possible-match count.

#### Scenario: Cited first-line study conflicts with prior-treatment claim
- **GIVEN** an answer includes a cited first-line study at zero match confidence and a compatible previously treated study at high confidence
- **WHEN** the site or extension presents the answer
- **THEN** the compatible study leads the possible matches, while the cited mismatch remains separately inspectable

#### Scenario: Only a cited mismatch is returned
- **WHEN** a cited record is read as another indication or setting
- **THEN** it does not count as a possible match and the no-match uncertainty notice remains visible

### Requirement: Compatible candidates retain reported-trial evidence ordering
Within compatible candidates, the site and extension SHALL preserve the lookup service's evidence ordering: explicitly stated registry identifiers first, then more agreeing reported-trial details, then descending score. Display ordering SHALL NOT change scores or establish compatibility by citation alone.

#### Scenario: Compatible named trial has a slightly lower model score
- **GIVEN** a compatible candidate agrees with the reported study name and other compatible candidates agree with no reported study details
- **WHEN** the site or extension orders and caps the possible matches
- **THEN** the named study leads, its original score remains visible, and unrelated cited nonmatches remain excluded

### Requirement: Study names preserve numeric identity across hashtag separators
Both lookup implementations SHALL recognise a missing space, hyphen or underscore between a study name's letters and following number. They SHALL retain the complete alphanumeric token so another study number or attached letter suffix does not become the same name. This comparison SHALL use already fetched records without additional model or source calls. Obsolete completed answers lacking this agreement SHALL be invalidated while source caches remain reusable.

#### Scenario: Study name is written as a hashtag
- **WHEN** a report names REGROW2 and the fetched registry record names REGROW 2
- **THEN** the record gains the trial-name agreement, but REGROW 21, REGROW 3 and REGROW2A do not

### Requirement: Ambiguous study names retain condition-specific discovery
When a study-name search exceeds twenty records, both lookup implementations SHALL narrow it at most once with the unchanged name and full stated condition, if available. They SHALL preserve existing work allowances and source pacing, without pagination or another model call. Multi-claim query reuse SHALL include condition in its identity. Returned records SHALL still undergo clinical scoring; a shared acronym SHALL not establish compatibility.

#### Scenario: Study acronym shared by unrelated conditions
- **GIVEN** a title/acronym identifies more than twenty records across conditions
- **WHEN** the reported condition narrows it to a bounded set
- **THEN** those records remain candidates for the same full claim's clinical scoring
- **AND** a second independent claim with that acronym and a different condition does not reuse the first narrowed set

#### Scenario: Study name remains ambiguous
- **WHEN** a study name remains over the limit within the condition, or no condition is available
- **THEN** it contributes no candidates without further discovery requests

#### Scenario: Saved answer predates condition narrowing
- **WHEN** a completed answer predates this discovery correction
- **THEN** it is invalidated while public source responses remain reusable

### Requirement: Presentation correction reuses bounded saved answers
The existing ten-record display cap SHALL apply across both groups, prioritising possible matches. The corrected presentation SHALL apply to saved answers without invalidation and SHALL add no model or source requests.

#### Scenario: Saved answer contains cited mismatches
- **WHEN** the reader reopens a complete saved answer
- **THEN** the corrected grouping applies locally, with at most ten displayed records and no added lookup

### Requirement: Trial matching preserves explicit intervention scope
Both lookup and private-pipeline scoring SHALL receive intervention descriptions and arm membership from the fetched registry record. Explicit route, formulation, stereoisomer and regimen conflicts SHALL mean `not_a_match`. Separate component arms SHALL NOT establish a complete regimen. Missing or truncated evidence SHALL retain uncertainty about explicit restrictions.

#### Scenario: Injected treatment against an inhaled claim
- **GIVEN** the claim explicitly concerns inhaled treatment and a record describes subcutaneous injection
- **WHEN** that trial is scored
- **THEN** the description is available to the scorer and the conflicting route is not a full match

#### Scenario: Separate component arms
- **GIVEN** the claim concerns A plus B while the registry describes an A-only arm and a B-only arm
- **WHEN** that trial is scored
- **THEN** arm membership is available and the two names alone cannot establish a combination match

#### Scenario: Long duplicate title
- **GIVEN** an unusually long official title and short intervention/arm descriptions
- **WHEN** the existing input limit is applied
- **THEN** the short route and arm evidence comes before the duplicate title and shortened content is marked

#### Scenario: A short official title carries the patient setting
- **GIVEN** a complete official title of at most 240 characters names a treatment setting absent from the brief title
- **WHEN** the scoring input is built
- **THEN** that official title is used as the primary title before descriptions; a longer official title remains secondary to the bounded brief title

#### Scenario: Compatibility is absent
- **GIVEN** an explicit route restriction and a missing or truncated description that does not establish the route
- **WHEN** the record is scored
- **THEN** the restriction remains uncertain rather than becoming a confident match

### Requirement: Detailed trial inputs remain bounded
The existing 1,500-character record limit, request counts and source caches SHALL remain. Shortened content SHALL be marked and obsolete completed answers SHALL be invalidated.

#### Scenario: Record exceeds the input limit
- **WHEN** descriptions and arm details exceed the record limit
- **THEN** the shortened input remains within 1,500 characters, carries a truncation marker and adds no request

### Requirement: Trial scoring distinguishes access and treatment roles
Both scorers SHALL receive study type and arm roles/membership before verbose intervention descriptions. They SHALL use the fourth `not_what_is_tested` answer for a comparator, background medicine or other incidental role, as specified in `social-link-backfill`. Expanded access SHALL be read as `not_a_match`. Missing or truncated details SHALL retain uncertainty.

#### Scenario: Expanded access is returned beside a trial
- **WHEN** the registry returns an `EXPANDED_ACCESS` record for the named medicine and condition
- **THEN** it is not counted as a possible trial match solely because those names agree

#### Scenario: Treatment roles survive verbose descriptions
- **WHEN** long intervention descriptions would exhaust the record limit
- **THEN** the scorer receives study type and arm roles/membership first, within the same existing limit

### Requirement: Combination-only trials do not establish single-medicine matches
A combination-only experimental regimen SHALL NOT establish a match for a claim about one of its medicines alone. Placebo and supportive care SHALL NOT count as additional experimental medicines. A claim about the complete combination SHALL remain eligible when that regimen is what the study tests.

#### Scenario: Preparation or activation is explicit
- **WHEN** the record explicitly describes an ingredient as a vaccine adjuvant or required activation agent
- **THEN** that role belongs to the treatment's preparation or delivery rather than establishing a separate experimental medicine

#### Scenario: Duplicate membership would displace regimen evidence
- **WHEN** both directions of the registry record state exactly the same intervention-arm membership
- **THEN** the scorer receives that membership once, leaving more of the bounded input for descriptions; unpaired or inconsistent labels remain present

#### Scenario: A single medicine appears only in combination arms
- **WHEN** the claim names medicine A alone and every experimental arm containing A also includes another experimental medicine
- **THEN** the complete intervention is not established as a match for the single-medicine claim

#### Scenario: The claim concerns the combination being tested
- **WHEN** the claim names A plus B and the experimental arm tests A plus B, including a comparison against B
- **THEN** the combination remains eligible as a match

### Requirement: Trial matching respects explicit patient restrictions
Lookup and private-pipeline scoring SHALL treat explicit patient populations and treatment settings as part of the indication. An incompatible setting SHALL be read as `other_indication`, even for a mentioned trial. Missing compatibility SHALL retain uncertainty; a broad claim SHALL NOT gain an unstated restriction. Existing bounded calls and source caches SHALL remain; obsolete completed answers SHALL be invalidated.

#### Scenario: Article links a separate first-line trial
- **GIVEN** the claim concerns previously treated metastatic pancreatic cancer and a linked record concerns first-line treatment
- **WHEN** candidates are scored
- **THEN** that record is not a full match solely because it tests the same drug and is explicitly linked

#### Scenario: Compatible prior-treatment study
- **GIVEN** the claim and record both concern the named intervention in previously treated metastatic pancreatic cancer
- **WHEN** the candidate is scored
- **THEN** it remains eligible as a match

#### Scenario: Broad condition is not silently narrowed
- **GIVEN** a claim about metastatic pancreatic cancer with no prior-treatment restriction
- **WHEN** first-line and previously treated records are scored
- **THEN** neither is excluded solely because of an unstated prior-treatment restriction

#### Scenario: Prior adjuvant treatment is compatible
- **GIVEN** the claim describes previous adjuvant therapy for resected disease and the record explicitly permits it for first-line metastatic treatment
- **WHEN** the candidate is scored
- **THEN** prior treatment alone does not make the settings incompatible

### Requirement: Card association preserves claim identity
A live answer SHALL name a tracked card only when its complete intervention and condition match. A single component SHALL NOT establish a combination match. Missing or ambiguous condition information SHALL produce no confirmed card association. Case and whitespace differences and recorded whole-intervention aliases SHALL remain supported without an extra model or source call.

#### Scenario: Same medicine for another condition
- **WHEN** an obesity report names a medicine also tracked for biological ageing
- **THEN** the biological-ageing card is not returned as its tracked claim

#### Scenario: Combination contains a tracked medicine
- **WHEN** a report names a two-medicine regimen and an existing card concerns only one of them
- **THEN** that card is not returned as the same claim, even if a component appears among extracted aliases

#### Scenario: Matching recorded alias
- **WHEN** the complete intervention matches a recorded alias and the same condition is identified
- **THEN** the tracked card is returned without another model call

#### Scenario: Older index lacks condition
- **WHEN** an index entry has names but no explicit condition
- **THEN** name overlap alone cannot confirm a card association

### Requirement: Corrected associations replace saved mistakes
The service and extension SHALL reject saved results produced before the claim-identity correction. Exact tracked source-address mappings SHALL retain their no-model path.

#### Scenario: Previously saved wrong-condition card
- **WHEN** a version-four result contains a name-only card association
- **THEN** the next eligible lookup does not reuse it

### Requirement: Combination readings retain the complete experiment
Both lookup readers SHALL retain the complete experimental regimen, without shortening it because a component-only comparison arm is discussed. Explicit monotherapy SHALL remain monotherapy. Unrelated roundup items SHALL remain separate claims; company profiles SHALL remain negative identifications. The readers SHALL use equivalent instructions and obsolete saved answers SHALL be invalidated.

#### Scenario: Combination trial discusses a component-only result
- **WHEN** a report describes A plus B and also highlights an A-only arm
- **THEN** its main combination is named A plus B

#### Scenario: Main claim is monotherapy
- **WHEN** the report explicitly concerns A alone and mentions an earlier combination as context
- **THEN** A remains the identified treatment
