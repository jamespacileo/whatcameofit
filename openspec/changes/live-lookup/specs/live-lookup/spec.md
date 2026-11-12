# Spec Delta

## ADDED Requirements

### Requirement: A lookup returns ranked trial candidates for a piece of text
Given the text of a news article or a post, the lookup SHALL name the treatment and the condition the text reports, search the trial registry for them, and return the records found, each with the probability that it is a trial of that treatment for that condition, likeliest first. A record for the same treatment in another condition SHALL be returned as such, below the matches. The lookup SHALL NOT approve anything, derive a status, or present its answer as reviewed.

#### Scenario: Article about a treatment with registered trials
- **WHEN** the text reports a named treatment for a condition, and the registry holds one trial of it for that condition and one for another condition
- **THEN** both are returned, the first as a match with the higher score, the second as the same treatment for another indication

#### Scenario: Text that is not about a treatment
- **WHEN** the text reports no specific treatment for a specific condition
- **THEN** the lookup says so, searches nothing and returns no candidates

### Requirement: Every way of finding the trial is used
The lookup SHALL look up directly any registry number the text states. It SHALL search the registry for the treatment's name, each other name the text gives, each part of a combination, each name the model knows the treatment by, and up to three search phrases for a treatment with no product name, each within the reported condition. A description that is not a name SHALL NOT be searched for as a name, and a registry number SHALL NOT be treated as a name. Names that come from the model's knowledge SHALL be reported apart from the names the text gives.

#### Scenario: Text that states a registry number
- **WHEN** the text contains a ClinicalTrials.gov number in any letter case
- **THEN** that trial is among the candidates even when no name search finds it

#### Scenario: Registry lists the treatment under a name the text does not give
- **WHEN** the model knows a development code for the treatment that the text does not state, and the registry lists a trial under that code
- **THEN** the trial is among the candidates and the code is reported as a name the text does not give

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
