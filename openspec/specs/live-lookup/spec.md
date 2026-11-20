# live-lookup Specification

## Purpose
Answers a reader who asks what became of the article or post in front of them: the site's lookup service reads it, matches it to published claims, knowledge cards and registry trials, and shows the answer with its scores to that reader only, never worded as a status.

## Requirements

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

### Requirement: Study-only interventions retain their study identity
When a report identifies an intervention only by its trial or paper, both scorers SHALL require the candidate to establish the same study identity. Similar conditions or outcomes SHALL NOT supply the missing intervention. Registry acronyms SHALL be preserved within the existing bounded candidate context. Differently named studies of a specifically identified intervention SHALL remain eligible. Corrected completed answers SHALL replace older saved results without clearing source caches.

#### Scenario: Unnamed intervention and unrelated same-condition study
- **WHEN** the reported intervention is identified only by a study name and a candidate does not establish that study identity
- **THEN** the scorer is instructed to reject the candidate instead of inferring its intervention from the shared condition

#### Scenario: Registry acronym carries the identity
- **WHEN** a candidate's acronym identifies the reported study but its title and long descriptions do not
- **THEN** the acronym still reaches clinical scoring within the existing candidate text limit
- **AND** the name alone does not override a clinical conflict

#### Scenario: Treatment is specifically identified
- **WHEN** the claim names the complete treatment and a compatible trial has a different study name
- **THEN** that different name alone does not disqualify the trial

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

### Requirement: Candidate match confidence
The shared presentation SHALL provide each displayed trial record with its own match-confidence percentage, rounded from a valid model score between zero and one. Missing or invalid scores SHALL be labelled unavailable. The explanation SHALL identify this as an automatic estimate of matching the reported treatment and condition, not a verified probability, treatment-effectiveness estimate or trial-quality rating. Reviewed claims SHALL NOT acquire model confidence scores.

#### Scenario: Reader compares candidate records
- **WHEN** an automatic answer includes multiple candidate records
- **THEN** each record carries its own match confidence, and a record explicitly named by the article retains its actual score even when that score is low

#### Scenario: A record has no usable score
- **WHEN** an explicitly named record has a missing or invalid model score
- **THEN** its match confidence is labelled unavailable rather than invented

### Requirement: A lookup returns ranked trial candidates for a piece of text
Given the text of a news article or a post, the lookup SHALL name the treatment and the condition the text reports, search the trial registry for them, and return the records found, each with the probability that it is a trial of that treatment for that condition, likeliest first. A record for the same treatment in another condition SHALL be returned as such, below the matches. The lookup SHALL NOT approve anything, derive a status, or present its answer as reviewed.

#### Scenario: Article about a treatment with registered trials
- **WHEN** the text reports a named treatment for a condition, and the registry holds one trial of it for that condition and one for another condition
- **THEN** both are returned, the first as a match with the higher score, the second as the same treatment for another indication

#### Scenario: Text that is not about a treatment
- **WHEN** the text reports no specific treatment for a specific condition
- **THEN** the lookup says so, searches nothing and returns no candidates

### Requirement: Every way of finding the trial is used
The lookup SHALL look up directly any registry number the text states. It SHALL search the registry for the treatment's name, each other name the text gives, each part of a combination, each name the model knows the treatment by, up to three search phrases for a treatment with no product name, and each development code a substance registry lists for the treatment, each within the reported condition. A description that is not a name SHALL NOT be searched for as a name, and a registry number SHALL NOT be treated as a name. Names that come from the model's knowledge SHALL be reported apart from the names the text gives. Development codes SHALL be taken only from a substance registry whose terms are recorded, only for the one substance it lists under the names the text gives (or under one part of a combination), and SHALL be reported apart from both. A name from the model's knowledge SHALL NOT be asked about. When the substance registry cannot be asked, the lookup SHALL go on without codes and SHALL say that they were not looked up and why.

#### Scenario: Text that states a registry number
- **WHEN** the text contains a ClinicalTrials.gov number in any letter case
- **THEN** that trial is among the candidates even when no name search finds it

#### Scenario: Registry lists the treatment under a name the text does not give
- **WHEN** the model knows a development code for the treatment that the text does not state, and the registry lists a trial under that code
- **THEN** the trial is among the candidates and the code is reported as a name the text does not give

#### Scenario: Trial filed under a development code
- **WHEN** the substance registry lists the treatment's name under one substance with a code the text does not state, and the registry lists a trial under that code within the condition
- **THEN** the trial is among the candidates and the code is reported as a development code from the substance registry

#### Scenario: Substance registry cannot be asked
- **WHEN** the substance registry does not answer
- **THEN** the candidates found by the other searches are returned, with no code, and the answer gives the reason the codes were not looked up

#### Scenario: Combination of two treatments
- **WHEN** the text reports "A and B" as one treatment and the registry lists a trial under B
- **THEN** that trial is among the candidates

### Requirement: A page is read for what it says about itself
When a lookup starts from an article's address, the reader of the page SHALL take the headline, the summary and the publication date from the tags the page carries for other software, and SHALL put them before the article in the text the model is shown. When the page carries the article itself as structured data of at least 500 characters, that article SHALL be used in place of the visible text. Structured data that cannot be parsed SHALL be ignored without failing the lookup. The reader SHALL collect the ClinicalTrials.gov numbers in the page's text and links, and the papers its links point to, by DOI or PubMed number, at most five of each. Nothing read from the page SHALL be stored.

#### Scenario: Page that describes itself in its tags
- **WHEN** a page gives its title, description and publication time in its tags
- **THEN** the text the model is shown begins with that headline, summary and date

#### Scenario: Page that carries the article as structured data
- **WHEN** the visible page is a teaser and its structured data holds the article
- **THEN** the model is shown the article from the structured data and not the teaser

#### Scenario: Article after a large navigation menu
- **WHEN** a page marks its main content with a main element after navigation that exceeds the lookup text limit
- **THEN** the visible text sent to the model comes from the main element, with the page's headline, summary and date retained and structured article data still taking precedence
- **AND** registry numbers and paper links elsewhere in the page remain available as signals

#### Scenario: Page that links to the paper it reports
- **WHEN** the page links to a paper by DOI, and that paper's abstract gives a ClinicalTrials.gov number
- **THEN** that trial is among the candidates, marked as given by a paper the page links to

### Requirement: The trial an article reports is told from its siblings by rule
The lookup SHALL ask the model for what the text says of the trial itself: its name, its number of participants, and who ran it. A trial the text names SHALL be searched for by that name. Each candidate SHALL carry the reasons it agrees with the article, as codes: its number is stated in the text or the page, its number is given by a linked paper, it carries the trial's name, its registered enrolment is within a tenth of the reported number of participants, or its sponsor or a collaborator carries every telling word of the named sponsor. These agreements SHALL be decided by rule and not by the model. A candidate whose number the article states SHALL be ranked first. Among the candidates that read as trials of the treatment for the condition, those agreeing with more details SHALL come first; agreement SHALL NOT lift a candidate that does not read as such a trial above one that does. A paper that gives more than three registry numbers SHALL be treated as identifying no trial, and so SHALL a trial name carried by more than twenty trials.

#### Scenario: Text that names the trial
- **WHEN** the text names its trial and the registry has a trial with that acronym
- **THEN** that trial is among the candidates and is ranked above the treatment's other trials

#### Scenario: Text that gives the trial's size and who ran it
- **WHEN** two trials of the treatment for the condition are found and one agrees with the reported number of participants and the named sponsor
- **THEN** that one is ranked first, and a trial for another condition that agrees with both stays below them

### Requirement: Which outlets can be read is recorded
The pipeline SHALL be able to check every tracked article's address and report, per outlet, how many articles its site let the pipeline read, how many it refused by robots.txt, how many failed and with which status, and how many pages carried each signal: headline, summary, date, structured article, a link to a paper, a registry number. The check SHALL obey robots.txt, SHALL ask one outlet at most once a second, SHALL NOT try an archive, and SHALL store counts and codes only, never an article's text.

#### Scenario: Outlet that can be read, outlet that refuses, outlet that fails
- **WHEN** one outlet serves its article, a second forbids reading in robots.txt and a third answers with a payment-required status
- **THEN** the record shows the first as read with its signals, the second as refused without its article being asked for, and the third as failed with that status

### Requirement: Work that does not wait on other work is done at the same time
A lookup SHALL read the text with the model while it looks up the papers the page links to and the registry numbers the article gives. One host SHALL still be asked one request at a time. The outlet check SHALL be able to check several outlets at the same time; one outlet SHALL still be asked one article at a time, a second apart, and all lookups running together SHALL keep, between them, to each registry's rate. Each lookup of an outlet check SHALL be saved when it ends, so a run that is stopped keeps what it fetched and what it spent. The registry cache SHALL accept two sessions writing the same request without failing.

#### Scenario: Several outlets checked at the same time
- **WHEN** the outlet check runs with three workers
- **THEN** its record is the same as when it runs one outlet at a time, and each article is reported as it is finished

#### Scenario: Two lookups fetch the same page at once
- **WHEN** another session caches a registry answer while this one is fetching the same request
- **THEN** this session's answer replaces it and no error is raised

### Requirement: A post is read by its address where its platform offers posts to software
The lookup SHALL read a post by its address on the platforms noted in `docs/sources.md` as offering posts to software without signing in: Bluesky, Hacker News and Mastodon servers. It SHALL take the post's text, the headline and summary of the link card the post carries, and the links in the post, leaving out links to tags and to people. It SHALL NOT read out who wrote the post. A Mastodon server SHALL be asked only when its robots.txt allows it and only for a post that is public. A post that is private, deleted or not there SHALL be refused with a code that names the platform. Nothing read from a post SHALL be stored.

#### Scenario: Post on Bluesky
- **WHEN** the address is a post on Bluesky that carries a link card
- **THEN** the post's text, the card's headline and summary, and the linked address are read, and the author's name and handle are not

#### Scenario: Story on Hacker News
- **WHEN** the address is a story or a comment on Hacker News
- **THEN** its title or text and the address it links to are read, and a deleted item is refused

#### Scenario: Post on a Mastodon server
- **WHEN** the address has the shape of a post on a Mastodon server, on any host
- **THEN** the server is asked only if its robots.txt allows it, a public post is read, and a post for followers only is refused

### Requirement: The article a post links to is read with it
The lookup SHALL follow the first link in a post that is the address of an article, read it as any article, and look up the post and the article together, the post first. A link to another post and a shortened link SHALL NOT be followed. When the linked article cannot be read, or the post links to none, the lookup SHALL go on from the post alone. The answer SHALL say which of the three happened. On the site, a post that links to an article the site tracks SHALL be answered with that claim's page: the article SHALL NOT be fetched and no automatic search SHALL be made.

#### Scenario: Post that links to an article
- **WHEN** a post links to an article that can be read
- **THEN** the model is shown the post and then the article, and the answer says it was read from a post on that platform and the article it links to

#### Scenario: Post whose article cannot be read
- **WHEN** the linked article's site forbids reading
- **THEN** the lookup is made from the post alone and the answer says the article could not be read

#### Scenario: Post that links to a tracked article
- **WHEN** a post links to an article a tracked claim cites
- **THEN** the answer is that claim's page, the model is not asked, and the article is not fetched

### Requirement: A post that cannot be read is turned back by name
For a post on a platform the lookup does not read, the service SHALL ask nothing of that platform and SHALL answer with a code and the platform's name, and the site SHALL say that it cannot read posts there and offer to take the post's text or the article's address instead.

#### Scenario: Post on a platform that cannot be read
- **WHEN** the address is a post on a platform that is not read
- **THEN** no request is sent to that platform and the reader is told, by the platform's name, to paste the post's text or the article's address

### Requirement: The service takes what a reader's own browser read
The service SHALL accept text together with the addresses that text links to (thirty at most, each at most 500 characters, web addresses only) and the name of the platform the text was a post on. It SHALL NOT ask for the address of the page the text came from. A platform name it does not know SHALL be ignored and SHALL NOT be repeated in the answer. With a platform name, the text SHALL be treated as a post: the first link that is an article is read and looked up with it, a tracked article is answered with its claim's page, and the answer SHALL say the post was read by the reader's browser. A shortened link SHALL NOT be followed, and when a post links only through one the answer SHALL say so. Without a platform name, the links SHALL be used for the papers and registry numbers they point to.

#### Scenario: Post read by the reader's browser
- **WHEN** text is sent with the platform name of a platform the service does not read, and a link to an article
- **THEN** that platform is asked nothing, the article is read, and the answer says the post was read by the reader's browser

#### Scenario: Article read by the reader's browser
- **WHEN** text is sent with links and no platform name
- **THEN** the text is looked up as it is, and a link to a paper is used to find the paper's trial

#### Scenario: Link-only post read by the browser
- **WHEN** a recognised platform name and an outgoing article link arrive with no post text
- **THEN** the linked article is read without inventing post text, a reviewed article retains its no-model answer, and an unreadable article produces a refusal without asking the model

### Requirement: A shortened link in a post is followed where its shortener allows
For a shortened link among a post's links, three at most per post, the service SHALL ask the shortener where the link leads, only if the shortener's robots.txt allows it, and SHALL read only the redirect, never a page. It SHALL take up to four steps when one shortened link leads to another, and stop at the first address that is not a shortened link. A shortener that refuses software, a link that leads nowhere and a link that leads back to itself SHALL be given up on, and when a post then has no article among its links the answer SHALL say it links through a shortened address the site may not follow.

#### Scenario: Post that links through a shortened address
- **WHEN** a post's link goes through a shortener that allows software, and that leads through a second one to an article
- **THEN** each shortener is asked only for its redirect, and the article is read from its own site and looked up with the post

### Requirement: A tracked claim is named
When a claim is already tracked under one of the names found, the lookup SHALL name that claim.

#### Scenario: Treatment already tracked
- **WHEN** the text names a treatment by a name recorded as another name of a tracked claim's intervention
- **THEN** the answer names that claim

### Requirement: A lookup keeps nothing it read
A lookup SHALL NOT store a claim, an entity, a match, an article or any of the text. It MAY record that a model was called and what it cost.

#### Scenario: Nothing is kept
- **WHEN** a lookup finds a trial
- **THEN** the numbers of claims, entities, matches and articles stored are unchanged

### Requirement: A reader may ask for a lookup, and its answer is marked
Where the site is built with a lookup address, an answer of "not tracked" for a pasted article address SHALL offer a registry search. Nothing SHALL be sent until the reader asks. The words beside the offer SHALL say what is sent and that the site keeps none of it. The answer SHALL begin by saying that it is an automatic search, made by software, not checked by a person and not a status. It SHALL carry the notice that a registered trial is not a treatment option. A record SHALL be shown with its title, phase, state, registry number and a link to the registry, and never with a verdict. Finding no record SHALL NOT be worded as there being no trial. Where the site is built without a lookup address, no search SHALL be offered.

#### Scenario: Reader sees an automatic answer
- **WHEN** a reader asks for a registry search and one record reads as a trial of the treatment for the condition and two do not
- **THEN** the marking comes first, the one record is listed with its phase, state and number, the other two are counted, and the trial notice is shown

#### Scenario: Reader asks about pasted text
- **WHEN** a reader sends the text of an article or post instead of an address
- **THEN** the answer is made from that text

### Requirement: The lookup service reads politely and keeps nothing
The service SHALL obey a site's robots.txt and SHALL NOT fetch an article when the rules forbid it or cannot be read. It SHALL NOT fetch a local or private address. It SHALL say why it cannot answer with a code the site words. It SHALL limit how many searches one reader and all readers together can make per minute. It SHALL NOT store or log an address, a text or an answer.

#### Scenario: Article the site does not allow to be read
- **WHEN** the article's site forbids automated reading in robots.txt, or refuses robots.txt itself
- **THEN** the article is not fetched and the reader is asked to paste its headline and opening paragraphs

#### Scenario: Nothing a reader sends is written down
- **WHEN** a lookup succeeds or fails
- **THEN** nothing of the text sent appears in any log

### Requirement: Public searches have bounded paid usage
The public service SHALL use a separate provider project with an enforced monthly spending limit of USD 13 and an alert at 80 percent. It SHALL restrict that project to the configured model and prohibit premium service tiers. Provider enforcement can lag; this limitation SHALL be documented. Per-minute application limits SHALL NOT be represented as a global monthly money cap. The private pipeline's local ledger SHALL remain separate.

The model adapter SHALL bound completion output, cancel stalled calls, and make no automatic retries. A provider project or organization spend-limit error SHALL produce a monthly-allowance refusal without exposing provider messages or reader text. Reviewed pages SHALL remain available. The privacy page and search offers SHALL identify OpenAI and explain what data is sent and possible provider retention before public enablement.

#### Scenario: Monthly allowance exhausted
- **WHEN** either model endpoint returns a project or organization spend-limit error
- **THEN** the service returns a budget-exhausted refusal without retrying, and reviewed pages remain available

#### Scenario: Ordinary rate limit
- **WHEN** the provider returns an ordinary request rate-limit error
- **THEN** it is not described as the monthly allowance being exhausted

#### Scenario: Provider stalls
- **WHEN** the provider stalls while sending headers or the response body
- **THEN** the request is cancelled at its deadline and is not automatically retried

### Requirement: Reported treatment claim
Identification SHALL require a reported therapeutic claim or study concerning an intervention and condition. Incidental drug mentions in earnings, supply, pricing, company-profile or litigation reporting SHALL NOT trigger a registry search. Preclinical work, observational findings and trial starts MAY identify a treatment without implying human efficacy or approval.

#### Scenario: Financial story names an obesity drug
- **WHEN** a story reports sales or supply without a treatment finding
- **THEN** identification reports no specific treatment claim and does not search the registry

#### Scenario: Company history lists a past medicine approval
- **WHEN** a company profile lists its founding, offices and products, including a product’s usual indication, mechanism or historical approval
- **THEN** those catalogue facts do not become the post’s own research finding and no registry search is made

### Requirement: Coherent intervention and condition
Identification SHALL choose one clearly main intervention-condition pair and SHALL NOT combine separate roundup items into a fictional treatment. A genuine combination regimen SHALL remain one intervention. If no clear main pair exists, the response SHALL explain that several separate claims were present.

#### Scenario: Research roundup names unrelated treatments
- **WHEN** a post lists bladder-cancer therapy, atrial-fibrillation surgery and sickle-cell gene editing as separate items
- **THEN** the response does not combine them into a single registry query

#### Scenario: One trial compares monotherapy and a combination
- **WHEN** a report describes different arms of the same trial
- **THEN** the experimental treatment or regimen is identified and comparator arms are study context, not separate roundup claims

### Requirement: Correction-aware saved results
Results stored before the social-reading and treatment-claim corrections SHALL NOT be reused by either the shared service cache or the extension's local result cache.

#### Scenario: Opening a previously misclassified business story
- **WHEN** an otherwise fresh version-2 or version-3 result exists
- **THEN** the corrected service and extension ignore it and perform a new eligible lookup

### Requirement: Bounded visual reading
The service SHALL accept one inline PNG/JPEG at most 750KB, 1600px maximum side and 1MP. It SHALL validate dimensions and request size before paid calls. It SHALL treat all pixels and text as untrusted report content, never instructions or proof. Identification failure SHALL be worded as insufficient identification, not absence of a treatment claim.

#### Scenario: Image-only claim
- **WHEN** a valid screenshot accompanies a short caption
- **THEN** both reach one model reading call and candidate scoring remains unchanged

### Requirement: Shared on-demand results
The service MAY retain structured automatic findings from independently public reports for 24h and reuse them across clients by a hashed cleaned URL. It SHALL retain no copied report text, screenshots or reader identity. Shared answers SHALL remain unreviewed and dated. Browser-only or selected content SHALL NOT populate shared storage.

#### Scenario: Previously processed public report
- **WHEN** a fresh shared result exists for the requested source
- **THEN** the service returns it with its original checked-at time and no model call

#### Scenario: Public access cannot be verified
- **WHEN** the service cannot independently read a report publicly
- **THEN** visual lookup may proceed but its result remains in the reader's local cache only

### Requirement: Bounded source retrieval
Article retrieval SHALL have a total deadline covering robots checks, response headers and response bodies. Independent public verification of browser-supplied text SHALL have a shorter deadline; if it expires, lookup SHALL continue with the supplied text without sharing that result. Paper and trial-registry requests SHALL have deadlines through body consumption. A registry timeout SHALL be reported as failure, never as evidence that no trial exists.

#### Scenario: A publisher stalls during public verification
- **WHEN** a browser supplies usable text but the anonymous publisher request exceeds three seconds
- **THEN** lookup continues from browser text and does not publish its result to shared storage

#### Scenario: A non-treatment report links to a stalled paper service
- **WHEN** identification finds no specific treatment and a linked-paper or stated-record request is still pending
- **THEN** the identification result returns without waiting for those requests

#### Scenario: Response headers arrive but the body stalls
- **WHEN** a publisher, paper or trial-registry response body fails to complete before its deadline
- **THEN** the request is aborted and follows the same failure behavior as a header timeout

### Requirement: A linked paper not looked up is said
Failed or timed-out linked papers SHALL be counted as not looked up, with no guessed registry numbers. When that count exceeds zero, the site and extension SHALL show an unfolded notice beside the records explaining that a linked paper could not be looked up and a trial it reports may be missing.

#### Scenario: Linked paper not answered in time
- **WHEN** the page links to two papers, the first paper's host does not answer within the deadline, and the second paper's abstract gives a ClinicalTrials.gov number
- **THEN** the second paper's trial is among the candidates, and the answer says one linked paper was not looked up

#### Scenario: Reader is told a linked paper was not looked up
- **WHEN** an answer says one linked paper was not looked up
- **THEN** the reader sees, beside the list, that a linked paper could not be looked up just now and a trial it reports may be missing
- **AND** the answer is not saved for reuse

### Requirement: Incomplete paper results are retried
An answer with a paper not looked up SHALL NOT be kept in the shared results library or the extension's saved results.

#### Scenario: Opening an incompletely checked report again
- **WHEN** the previous answer had a linked paper not looked up
- **THEN** the next lookup asks again instead of reusing that incomplete answer

### Requirement: Stop irrelevant source work
When identification finds no specific treatment, the paper request in flight SHALL be ended and no further paper or stated record SHALL be asked for.

#### Scenario: Identification finishes before a linked-paper request
- **WHEN** identification reports no specific treatment while paper retrieval is pending
- **THEN** the request is cancelled and further source requests are skipped

### Requirement: Overlapped bounded source work
Once a treatment is identified, independent registry-name search and optional enrichment SHALL start without waiting for all linked papers. A single lookup SHALL spend at most five seconds waiting for its linked papers together, with at most three paper requests and starts at least 500 ms apart. Every unanswered paper SHALL be counted; exact cited record priority, matching semantics and unchecked-paper cache exclusions SHALL remain intact.

#### Scenario: The first paper stalls
- **WHEN** the first paper does not answer but a later paper can supply a registry number within the aggregate allowance
- **THEN** that later request can run and its trial is included, and all unanswered papers are reported

### Requirement: Progressive result compatibility
An opt-in streaming lookup SHALL emit a completed core result before optional research enrichment and emit a final complete result afterwards. Ordinary JSON clients SHALL retain their existing complete response. A failure before core completion SHALL be explicit and never an empty successful search.

#### Scenario: Related-paper search is pending
- **WHEN** clinical searching and scoring finish while enrichment remains pending
- **THEN** an opted-in client receives the completed core result without another model invocation

### Requirement: Bounded structured source reuse
Successful DOI/PubMed-to-trial mappings and public registry query results MAY be reused for at most 24h. Cache operations SHALL be bounded, with origin fallback on cache failure. Abstracts, copied report text, images, credentials and reader identifiers SHALL NOT be retained. Errors and timeouts SHALL NOT be cached as empty answers. Independently public completed non-treatment outcomes MAY enter the dated shared-result library; provisional and incomplete outcomes SHALL NOT.

#### Scenario: A paper service fails
- **WHEN** a paper metadata request fails or times out
- **THEN** no successful empty mapping is stored and a later lookup can ask again

### Requirement: Public on-demand research context
The public lookup SHALL return the records of papers the report links to, bibliographic search results and identifiers for organisations explicitly named in the report, in addition to trial candidates. These SHALL be labelled unreviewed search results, separate from any status and from match confidence. The interface SHALL collapse secondary context initially. Missing keys, provider limits and failures SHALL leave trial results available. Old cached results and older extensions SHALL remain compatible.

#### Scenario: A report has related papers and names a university
- **WHEN** OpenAlex finds papers and ROR selects the university's identity
- **THEN** paper titles, metadata and source links and the ROR organisation link are available in collapsed sections, with no status change

#### Scenario: The report links to its paper
- **WHEN** the page links to a paper by DOI or PubMed number and a keyword search would not return that paper
- **THEN** the paper's record is fetched by its identifier, listed first and marked as linked from the article

#### Scenario: The paper's title shares few words with the report
- **WHEN** the report links to no paper, names two organisations that ROR identifies, and a keyword search does not return the paper it reports
- **THEN** works on the treatment's terms with an author at each named organisation, published around the report's date, are searched for, and a paper found this way is listed before keyword results with the organisations it was found under, those found under more organisations first

#### Scenario: The free allowance cannot be established
- **WHEN** OpenAlex's allowance is exhausted, unknown, exceeds the free budget or has prepaid credit
- **THEN** no charged literature search is sent, a temporary unavailability is shown, and trial lookup and ROR continue

#### Scenario: Repeated research query
- **WHEN** a normalized metadata result is less than seven days old
- **THEN** it is reused without a provider request, including an empty result

#### Scenario: A provider times out or limits access
- **WHEN** an API call or its body takes more than five seconds, or a source responds with a quota error
- **THEN** the optional source stops without retries or alternative accounts and the remaining results are returned
