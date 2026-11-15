# Spec Delta

## Purpose

Reads the article of a link lead that triage passed, once, and makes it a source article of the claim it reports or a new claim, by the rules that already govern extraction, claims and publishing.

## ADDED Requirements

### Requirement: Which leads are read
The reading step SHALL apply to leads that are passed at the configured thresholds, and to the held leads that name one of the operator's topics (see "Topic leads"). Before a lead is read, the check for an article already tracked SHALL run again; a lead that has become already tracked SHALL NOT be read.

#### Scenario: A held lead
- **WHEN** a lead's score is between the two thresholds and its title names no topic
- **THEN** it is not read

#### Scenario: Tracked since it was screened
- **WHEN** a lead's address became a claim's source article after the lead was screened
- **THEN** the lead's outcome becomes already tracked, and no article is fetched and no model is called for it

### Requirement: Reading order
Due leads SHALL be read in this order: first those whose title names one of the operator's topics, then those linked to a registry trial, then by the sum of their shares' scores, highest first.

#### Scenario: A topic lead and a much-shared lead
- **WHEN** two leads are due, and the less shared one names a topic
- **THEN** the lead that names the topic is read first

#### Scenario: Two leads, one linked to a trial
- **WHEN** two leads are due and only the less shared one is linked to a registry trial
- **THEN** the lead linked to a trial is read first

### Requirement: Topic leads
The operator's topics SHALL be a checked-in list of names, each with the words that mark a link lead or a claim as belonging to it. A lead's title names a topic when it holds one of the topic's words as a whole word, whatever its letter case. A lead that names a topic and that triage held SHALL be read as a passed lead is; a lead that triage rejected SHALL NOT be read. With no topic listed, only passed leads SHALL be read. A lead on an outlet that is not listed is not in scope and SHALL NOT be read, whatever it names. A topic is covered by what was reported of its treatments. A lead is on a topic when its title, or the treatment its read names, holds one of the topic's words. For a lead on a topic, when the probability that the article is about what the treatment does (new or established: evidence, safety, a new use, an approval) is below the configured probability, 0.5 unless set, no claim SHALL be joined or drafted and the lead's outcome SHALL be business news. A topic's list MAY group the names of one drug, brand and generic; a claim under any name of the group SHALL be a candidate for an article that names another (see "The same story in other words"). The precision measured for triage at the thresholds does not hold for held leads, so the outcomes of topic leads SHALL be reported apart, in the topic's coverage. A topic SHALL change only which leads are read, in what order, and which claims are candidates: it SHALL NOT change a status and SHALL NOT appear in the export.

#### Scenario: A held lead on a topic
- **WHEN** a lead scored 0.4 names a GLP-1 drug in its title, and the thresholds are 0.7 and 0.2
- **THEN** it is read, and the check after the read decides whether it becomes or joins a claim

#### Scenario: A held lead on no topic
- **WHEN** a lead scored 0.4 names no topic
- **THEN** it is not read

#### Scenario: A rejected lead on a topic
- **WHEN** a lead scored 0.1 names a topic, and the lower threshold is 0.2
- **THEN** it is not read

#### Scenario: A word inside another word
- **WHEN** a title holds "GLP-12" and the topic's word is "GLP-1"
- **THEN** the title does not name the topic

#### Scenario: No topics are listed
- **WHEN** no topic is listed
- **THEN** a held lead is not read, whatever its title

#### Scenario: A shortage of a topic's drug
- **WHEN** a lead names a topic, and the decision gives 0.03 to the article being about what the treatment does and 0.95 to business news
- **THEN** no claim is created or joined, and the lead's outcome is business news with that probability

#### Scenario: A trial result for a topic's drug
- **WHEN** a lead names a topic, and the decision says an established treatment and what it does
- **THEN** the read goes on to join a claim or draft one

#### Scenario: A price rise for a tracked treatment on no topic
- **WHEN** a lead is on no topic, the decision says business news, and a claim exists for what the read names
- **THEN** the article is added to that claim, and the lead's detail says business news about a treatment

#### Scenario: A price rise with no claim to join
- **WHEN** a lead is on no topic, the decision says business news, and no claim exists for what the read names
- **THEN** no claim is created, and the lead's outcome is business news

#### Scenario: Shared under a title that names nothing
- **WHEN** a lead's title names no topic word, the read names Wegovy, and the decision says business news
- **THEN** the lead is on the topic, and the article is not added to the semaglutide claim

#### Scenario: A brand name and its generic name
- **WHEN** a claim's intervention is semaglutide, and a lead's read names Wegovy, which the topic lists as the same drug
- **THEN** that claim is a candidate, and the same-claim decision says whether the article reports it

### Requirement: Topic coverage
`thenwhat backfill topics` SHALL report, for every topic or for the one named: how many link leads name it; how many of those are not screened yet, on an outlet that is not listed, already a source article, in scope and not scored yet, rejected by triage, and to be read; the outcomes of those that were read; and each unarchived claim whose intervention names the topic, with its review state or that it is published, its status, and how many articles, approved trials, approved papers and approved background cards it has. It SHALL send no request and change nothing.

#### Scenario: Leads at every stage
- **WHEN** leads that name a topic stand at different stages
- **THEN** the report gives the number at each stage and the outcomes of those read

#### Scenario: A claim with a trial and a paper
- **WHEN** a claim for semaglutide has one article, one approved trial, one rejected trial and one approved paper
- **THEN** the report lists it with 1 article, 1 trial, 1 paper and 0 cards

#### Scenario: An unknown topic
- **WHEN** the operator names a topic that is not listed
- **THEN** the command fails and lists the topics

### Requirement: Outlets are asked through the page reader
An article SHALL be fetched only through the page reader, which decides whether an address may be fetched, how often an outlet is asked and where a copy comes from (`docs/adr/0006`, change `firecrawl-page-reader`). The reading step SHALL act on the reader's answer and keep no rule of its own about an outlet.

#### Scenario: Not allowed
- **WHEN** the reader answers that a lead's address is not allowed
- **THEN** the article is not read, the lead's outcome is cannot be read with the reader's reason, and it is not tried again

#### Scenario: Not now
- **WHEN** the reader answers that a lead's outlet cannot be asked now
- **THEN** the lead is given no outcome, no attempt is counted against it, it stays due, and the run goes on with other leads

#### Scenario: Two processes, one outlet
- **WHEN** two processes each hold a due lead on the same outlet
- **THEN** both requests go to the reader, and how far apart the outlet is asked is the reader's doing

#### Scenario: The site did not serve the page
- **WHEN** the reader answers that the site gave a status other than success
- **THEN** the lead's outcome is cannot be read, with that status, and no text is asked of the operator

#### Scenario: The reader cannot be asked
- **WHEN** the reader does not answer, fails, says it is overloaded, or answers in a form that is none of these
- **THEN** the run ends, the leads not yet read stay due with their attempts unchanged, and nothing is recorded against an outlet

### Requirement: One read per article
An article SHALL be read by the model at most once for its lead, with the existing extraction. Its text SHALL be held only while the read runs and SHALL NOT be stored, cached, logged or written to a fixture. The article's content hash SHALL be recorded.

#### Scenario: After a read
- **WHEN** a lead's article has been read
- **THEN** its text is stored nowhere, and a second run does not read it again

### Requirement: The article's date
A source article made from a lead SHALL carry the publication date that the article's own page gives. The date a link was first shared SHALL NOT be used as a publication date, and neither SHALL a date read from the article's address. A lead whose page gives no date that can be read SHALL NOT be read by the model: its outcome SHALL be cannot be read, with the reason that the page gives no publication date.

#### Scenario: A date the page gives in a tag
- **WHEN** a lead's page carries its publication time in a tag made for other software
- **THEN** the source article's date is that day

#### Scenario: A date the page shows in words
- **WHEN** a lead's page shows its date only as words, in an element the page reader knows for that outlet
- **THEN** the source article's date is that day

#### Scenario: A page with no date
- **WHEN** a lead's page gives no publication date
- **THEN** no model is called, the lead's outcome is cannot be read with that reason, and no source article is made

#### Scenario: A date that cannot be read
- **WHEN** a lead's page gives a date in a form the page reader does not know
- **THEN** the lead is treated as a page with no date, and its outlet is counted among those with no date

### Requirement: The outlet's name
A source article made from a lead SHALL carry its outlet's display name from the checked-in list of outlets. No model names an outlet, and no name SHALL be made from a domain. A lead whose outlet has no display name SHALL NOT be fetched or read: its outcome SHALL be cannot be read, with the reason that its outlet has no name.

#### Scenario: A listed outlet
- **WHEN** a lead on theguardian.com is read
- **THEN** its source article's outlet is "The Guardian"

#### Scenario: An outlet with no display name
- **WHEN** a lead's outlet is in scope by its kind and has no display name
- **THEN** no article is fetched, no model is called, and the lead's outcome is cannot be read with the reason that its outlet has no name

### Requirement: The article's title
A source article made from a lead SHALL carry the headline its own page gives as its title. The title a link was shared under SHALL NOT become a source article's title or reach the export. A lead whose page gives no headline SHALL NOT be read by the model: its outcome SHALL be cannot be read, with that reason.

#### Scenario: A shared title that differs from the headline
- **WHEN** a lead was shared under a title a person wrote
- **THEN** the source article's title is the page's headline, and the shared title is not in the export

#### Scenario: A page with no headline
- **WHEN** a lead's page gives no headline
- **THEN** no model is called and the lead's outcome is cannot be read with that reason

### Requirement: Only an article about one treatment for one condition becomes a claim
After the read and before any claim is joined or drafted, a decision SHALL say which the article is: about one treatment for one condition where the treatment is new, experimental or being tested for it; about one treatment for one condition where the treatment is already in established use and the article is about what it does; business news about one treatment for one condition, such as its price, sales, supply, a lawsuit or who takes it; or none of these. It SHALL be shown the read's own headline, summary, treatment and condition and nothing of the article's text. An article about an established treatment SHALL be joined or drafted exactly as one about a new treatment, and the lead's detail SHALL say it is an established treatment in the news. Business news SHALL NOT start a claim, for any lead. It SHALL be joined to a claim that exists, with the lead's detail saying it is business news, unless the lead is on a topic (see "Topic leads"); with no claim to join, or on a topic, the lead's outcome SHALL be business news. An article is business news when the probability that it is about what the treatment does, new or established, is below the configured probability. A kind logged before the business answer existed never says business news. When the probability that the article is about one treatment for one condition, of any of those three kinds, is below the configured probability, 0.5 unless set, no claim SHALL be joined or drafted, and the lead's outcome SHALL be not one treatment, with what was read and the probability. The decision SHALL be logged under its own step name, `treatment_kind`, with the lead's reference; that log entry is the record of whether an article was about a new or an established treatment.

#### Scenario: A trial result
- **WHEN** the decision says a new treatment at 0.95
- **THEN** the read goes on to join a claim or draft one

#### Scenario: News about an established treatment
- **WHEN** a read summarises a trial in which a drug long in use did not prevent a first heart attack, and the decision says an established treatment
- **THEN** a claim is drafted as for any read, and the lead's detail says an established treatment in the news

#### Scenario: News about a tracked, established treatment
- **WHEN** the read names a claim's intervention and indication, and the decision says an established treatment
- **THEN** the article is added to that claim

#### Scenario: Unsure whether new or established
- **WHEN** the decision gives an established treatment 0.4, a new treatment 0.3 and neither 0.3
- **THEN** the article is about one treatment at 0.7 and the read goes on

#### Scenario: An approach with no one condition
- **WHEN** a read summarises a class of compounds proposed for four conditions, and the decision gives neither 0.95
- **THEN** no claim is created, and the lead's outcome is not one treatment with the probability 0.05

#### Scenario: Not one treatment, though it names a tracked one
- **WHEN** the read names a claim's intervention and indication, and the decision gives neither 0.95
- **THEN** the article is not added to that claim

### Requirement: A class of treatments is not one treatment
When the treatment the read names is a class by a checked-in rule on the name, no claim SHALL be joined or drafted and no decision SHALL be asked; the lead's outcome SHALL be not one treatment, with what was read and that it is a class. A name is a class when, with anything it is said to be for set aside, it holds a word for a class (agonist, inhibitor, blocker, analog, modulator, mimetic, singular or plural), ends in a plural kind of thing (drugs, medications, medicines, treatments, therapies, vaccines, antibodies, prescriptions), or holds the plural of a code. A name is also a class when it holds a topic's class word, none of the topic's drugs, and what is left of it is not a name. A code in the name SHALL NOT change this. A singular category that hides several products, such as "COVID-19 vaccine", is not this rule's case: the same-claim decision compares the summaries and refuses the join (`corpus-match-accuracy`, "identity unresolved").

#### Scenario: A class of treatments
- **WHEN** a read names "GLP-1 receptor agonists" as the treatment
- **THEN** the lead's outcome is not one treatment, its detail says a class of treatments, no claim exists and no treatment-kind decision was asked

#### Scenario: A topic's class named without a drug
- **WHEN** a read names "GLP-1 metabolic therapy" as the treatment, and GLP-1 is a topic's class word
- **THEN** the lead's outcome is not one treatment and no decision was asked

#### Scenario: A treatment described by what it does to the class's target
- **WHEN** a read names a treatment that is described as releasing GLP-1 and names no drug of the topic
- **THEN** the rule does not apply, because what is left of the name still names something

#### Scenario: One member of a class
- **WHEN** a read names "semaglutide" as the treatment
- **THEN** the rule does not apply and the read goes on to the treatment-kind decision

### Requirement: The read names one condition as a registry files it
The read SHALL be asked for the condition treated by the name a trial registry files it under: the disease or condition alone, never an aim or an outcome, and one condition, the one the article's main result is about when it reports several. Prevention SHALL stay apart from treatment: for an article about preventing a condition in people who do not have it, the read SHALL be asked to say so in the condition.

#### Scenario: An aim reported as the condition
- **WHEN** an article reports a drug for weight loss in people with obesity
- **THEN** the read is instructed to give "obesity", not "weight loss"

#### Scenario: Prevention is not treatment
- **WHEN** one article reports a drug given to people with COVID-19 and another reports the same drug given after exposure to people who do not have it
- **THEN** the read is instructed to give "COVID-19" for the first and "prevention of COVID-19" for the second, so the two are not one claim by name

### Requirement: An article for a claim that exists
When the read names an intervention and an indication that an existing claim covers, the article SHALL be added to that claim as a source article, with its content hash, any archive address and its reported statements, which are checked and approved by the existing rule. The claim's headline, summary, intervention, indication, vertical and review state SHALL NOT change.

#### Scenario: An earlier report of a tracked claim
- **WHEN** a lead's article reports a claim the tracker holds, and was published before the claim's other articles
- **THEN** the claim gains the article, and its first reported date becomes the article's

#### Scenario: A decided claim
- **WHEN** the existing claim is approved
- **THEN** it stays approved, and no field the operator reviewed is changed

### Requirement: The same story in other words
When no existing claim has the read's intervention and indication as written, the claims whose intervention shares a name with the read's, followed by the claims that screening found named in the lead's title, SHALL be candidates, up to a fixed number. A rejected claim SHALL NOT be a candidate. A name is shared when a claim's intervention name or synonym equals one of the names the read gives, or when one sits whole inside the other, word for word. A decision SHALL say whether the article reports one of the candidates or none of them. It SHALL be shown each side's treatment and condition and nothing of the article's text. The article reports a candidate when the treatment is the same and the article's condition is the candidate's condition, a narrower form of it or a wider wording of it; a different condition is a different claim. The article SHALL be added to the candidate the decision gives the highest probability when two things hold: the probability that the article reports one of the candidates, which is one minus the probability the decision gives to none of them, is at or above the configured probability, 0.6 unless set; and that candidate's own probability is more than half. Otherwise a new claim SHALL be drafted. Being added SHALL change nothing of the claim that adding any article does not change: the claim keeps the indication and headline it was first given. The decision SHALL be logged.

#### Scenario: The same story in another outlet's words
- **WHEN** a claim exists for esketamine for major depressive disorder and suicidal thinking, and a lead's read names esketamine for treatment-resistant depression, and the decision gives that claim 0.9 and none of the candidates 0.1
- **THEN** the article is added to that claim, no claim is created, and the lead's detail says what was read and both probabilities

#### Scenario: A wording the decision is less sure of
- **WHEN** the decision gives the one candidate 0.62 and none of the candidates 0.38
- **THEN** the article is added to that claim

#### Scenario: The vote is split between two claims
- **WHEN** the decision gives two candidates 0.51 and 0.43 and none of the candidates 0.06
- **THEN** the article is added to the candidate given 0.51

#### Scenario: Two conditions of one drug
- **WHEN** the decision gives two candidates 0.48 and 0.47
- **THEN** the article is added to neither and a new claim is drafted

#### Scenario: A rejected draft shares the name
- **WHEN** the only claim sharing the read's name was rejected
- **THEN** no decision is asked about it and a new claim is drafted

#### Scenario: A name inside a longer name
- **WHEN** a claim's intervention is esketamine and a read names esketamine nasal spray
- **THEN** that claim is a candidate; a claim whose intervention is ketamine is not

#### Scenario: The same treatment for a different condition
- **WHEN** the decision says the article reports none of the candidates
- **THEN** a new claim is drafted for the read's intervention and indication

#### Scenario: An unsure decision
- **WHEN** the decision gives the one candidate 0.45 and none of the candidates 0.55
- **THEN** the article is not added to it and a new claim is drafted

#### Scenario: No claim shares the name
- **WHEN** no claim's intervention shares a name with the read's and screening linked the lead's title to no claim
- **THEN** no decision is asked and a new claim is drafted

#### Scenario: A claim screening found in the title
- **WHEN** screening linked the lead's title to a claim whose intervention name the read does not share
- **THEN** that claim is a candidate all the same

### Requirement: One read at a time settles which claim
Reads that run side by side SHALL settle which claim an article belongs to one at a time, each holding its turn until what it made is saved, so that a claim one read has just drafted is found by the next.

#### Scenario: Two articles on one story read at once
- **WHEN** one read is settling which claim its article belongs to
- **THEN** no other read can settle the same question until the first has saved its result

### Requirement: An article for a new claim
When no existing claim covers what the read names, a claim SHALL be drafted from the read exactly as extraction drafts one. Its slug SHALL be made by rule from the intervention and the indication. Its vertical SHALL be chosen by a decision among the configured verticals and accepted only at or above the configured probability. A claim whose intervention is a description SHALL be rejected by rule when it is drafted. A claim whose intervention is a name SHALL await review, and so stay out of the export, until it has been prepared.

#### Scenario: A named intervention
- **WHEN** the read names an intervention that is a name, and the vertical decision is confident
- **THEN** a claim is created with that slug and vertical, awaits review, and is not in the export

#### Scenario: A description in place of a name
- **WHEN** the read gives a description where a name is needed
- **THEN** the claim is rejected by rule and kept, as for any draft

#### Scenario: No confident vertical
- **WHEN** the vertical decision is below the configured probability
- **THEN** no claim is created, the lead's outcome is needs a vertical, and the lead is listed for the operator with what the read named

#### Scenario: The slug is taken
- **WHEN** the slug the rule makes belongs to a claim for another intervention or indication
- **THEN** no claim is created and the lead's failure names the slug

### Requirement: A read's claim is decided after it is prepared
`thenwhat prepare` SHALL decide a claim that a lead's read drafted, by the existing rule for drafts, once every step it runs for that claim has succeeded: reading unread articles, searching the registries, reading the registries for approved matches, and reading the stored records. While a step has failed, the claim SHALL keep awaiting review. `thenwhat prepare` SHALL NOT decide a claim that no lead's read drafted. No claim a read drafted is published with a status that no registry search stands behind.

#### Scenario: Prepared and named
- **WHEN** `thenwhat prepare --pending` has run every step without failure for a claim a read drafted
- **THEN** the claim is approved by rule and is published with the next export, with the status its approved evidence gives

#### Scenario: A step that failed
- **WHEN** a step of `thenwhat prepare` fails for a claim a read drafted
- **THEN** the claim keeps awaiting review, and the next `thenwhat prepare --pending` works on it again

#### Scenario: A claim the operator entered
- **WHEN** `thenwhat prepare` runs for a claim that awaits review and that no read drafted
- **THEN** it is prepared and left awaiting the operator, as before

### Requirement: Registry numbers and papers the page gives
Registry numbers and paper DOIs that the article's own page gives SHALL be recorded for the claim as candidates, with the reason that the article names them, without a search. Each SHALL be scored and decided as any candidate is, for the claim's indication. A paper the page gives only by its PubMed number SHALL NOT be recorded. When what the page names cannot be read or scored, the claim and its article SHALL stand, and the lead SHALL say that they were not recorded.

#### Scenario: An article that links its trial
- **WHEN** an article's page gives a registry number
- **THEN** that trial is a candidate match of the claim, scored for the claim's indication, and is not approved by having been named

#### Scenario: The registry cannot be reached
- **WHEN** a lead's article is read into a claim and the registry does not answer for the number its page names
- **THEN** the claim and its source article are kept, and the lead's detail says the named records were not recorded

### Requirement: Enough articles for one claim
A lead linked by its title to a claim that already has the configured number of source articles SHALL be held and not read, unless it was first shared before the claim's first reported date.

#### Scenario: A much-reported claim
- **WHEN** a claim has the configured number of source articles and a lead for it was shared after its first reported date
- **THEN** the lead is held, with the reason that the claim has enough articles

#### Scenario: An earlier article
- **WHEN** a lead for that claim was first shared before the claim's first reported date
- **THEN** the lead is read

### Requirement: Funnel report
`thenwhat backfill funnel` SHALL report how many leads are loaded, in scope, scored, passed, read, could not be read by reason, added to an existing claim, made a new claim approved by rule, made a claim rejected by rule, made a claim that awaits preparation, need a vertical, were not about one treatment for one condition, and were business news on a topic. It SHALL give the model cost recorded for triage and for reading. It SHALL list the outlets whose pages gave no publication date, with how many leads each lost.

#### Scenario: After a limited run
- **WHEN** 200 leads have been through the reading step
- **THEN** the report gives each count and the two costs, and no request is sent
