# source-clients Specification

## Purpose
Gives the pipeline uniform, polite and replayable access to public registries of clinical trials, scientific papers and DOI records.

## Requirements

### Requirement: Common record contract
Every source SHALL return records that carry the source name, the record's external identifier, its canonical public URL, the raw payload as received, and the time the payload was fetched.

#### Scenario: Trial record
- **WHEN** a trial is fetched by its registry identifier
- **THEN** the record carries the registry's name, the identifier, the trial's public URL, the unmodified payload and the fetch time

### Requirement: Trial registry lookups
The trial registry source SHALL support fetching one trial by registry identifier and searching trials by intervention term.

#### Scenario: Search by intervention term
- **WHEN** the registry is searched for an intervention term that three trials use
- **THEN** three trial records are returned

#### Scenario: Search with many results
- **WHEN** a search matches more trials than fit in one page of results
- **THEN** all matching trials are returned

### Requirement: Literature lookups
The literature source SHALL support fetching one paper by DOI and listing the papers that cite a given paper.

#### Scenario: Citing papers
- **WHEN** citing papers are requested for a paper that has 40 citations
- **THEN** 40 paper records are returned, each with title, authors, publication date and DOI when available

### Requirement: DOI registry lookups
The DOI registry source SHALL support fetching metadata for a DOI and listing retraction and correction notices attached to that DOI.

#### Scenario: Retracted paper
- **WHEN** notices are requested for a DOI that has a retraction notice
- **THEN** the notice is returned with its type, date and own DOI

#### Scenario: Paper with no notices
- **WHEN** notices are requested for a DOI that has none
- **THEN** an empty list is returned

### Requirement: Not found
A lookup for an identifier the source does not know SHALL return an explicit not-found result and SHALL NOT be treated as a failure.

#### Scenario: Unknown trial identifier
- **WHEN** a trial is fetched by an identifier the registry does not have
- **THEN** the result is not-found and no error is raised

### Requirement: Response caching
An identical request repeated within the cache lifetime SHALL be answered from the cache without a network call, and SHALL keep the original fetch time. An operator SHALL be able to force a fresh fetch.

#### Scenario: Repeated request
- **WHEN** the same trial is fetched twice within the cache lifetime
- **THEN** only one network request is made and both records carry the same fetch time

#### Scenario: Forced refresh
- **WHEN** an operator forces a refresh of a cached trial
- **THEN** a network request is made and the fetch time is updated

### Requirement: Rate limiting
Requests to a source SHALL NOT exceed that source's configured rate, counted across every client of the source and every process that asks it. The default rate for each source SHALL be at or below the rate the source publishes.

#### Scenario: Burst of requests
- **WHEN** ten requests are issued at once to a source limited to three requests per second
- **THEN** the requests are spread over at least three seconds

#### Scenario: Several clients of one registry at once
- **WHEN** two clients of one source, which share nothing but the source's name, issue requests in turn
- **THEN** each request waits until the source's interval has passed since the request before it, whichever client made that one

#### Scenario: Several processes ask one source
- **WHEN** two processes each issue requests to one source
- **THEN** the turns they take are never closer together than the source's interval

### Requirement: Client identification
Every request SHALL carry a User-Agent that names the project and a contact address taken from configuration. Without a configured contact address the system SHALL NOT send requests.

#### Scenario: Missing contact address
- **WHEN** a fetch is attempted and no contact address is configured
- **THEN** no request is sent and the error names the missing setting

### Requirement: Failure handling
Transient failures SHALL be retried a bounded number of times with increasing delay, honouring any retry delay the source states. When retries are exhausted the fetch SHALL fail as a whole and return no partial records.

#### Scenario: Source asks the client to slow down
- **WHEN** a source answers with a too-many-requests response that states a retry delay
- **THEN** the next attempt is made no sooner than the stated delay

#### Scenario: Source stays down
- **WHEN** a source fails on every allowed attempt
- **THEN** the fetch reports an error and returns no records

### Requirement: A paper is looked up by its PubMed number
The literature client SHALL return a paper's index record for a PubMed number, as it does for a DOI, and SHALL return nothing when the index holds no such paper. A number that is not all digits SHALL cause no request.

#### Scenario: Known PubMed number
- **WHEN** the client is asked for a PubMed number the index holds
- **THEN** it returns that paper's record with the time it was fetched

#### Scenario: Malformed number
- **WHEN** the client is asked for "PMC12345"
- **THEN** it makes no request and returns nothing

### Requirement: Stored paper records are refreshed when old
A fetch SHALL ask the index again for a stored paper record only when the stored record is older than the configured age, thirty days by default. A paper whose stored record is younger SHALL cause no request.

#### Scenario: Record fetched last week
- **WHEN** a fetch runs for a claim whose paper record was stored seven days ago
- **THEN** no request is made for that paper

#### Scenario: Record fetched two months ago
- **WHEN** a fetch runs for a claim whose paper record was stored sixty days ago
- **THEN** the record is fetched again and the stored record and its time are replaced

### Requirement: Optional substance enrichment uses shorter network waits
GSRS development-code requests SHALL default to two attempts with a five-second network inactivity timeout per phase. They SHALL retain the existing contact client, source pacing, thirty-day successful-response cache and stated retry delay. Other source clients SHALL retain their existing default waits and attempt counts.

#### Scenario: Substance service asks for a longer delay
- **WHEN** the first response asks the client to wait longer than five seconds before retrying
- **THEN** the second attempt is made no sooner than that stated delay
- **AND** the timeout is not presented as a whole-operation deadline; shared pacing and separate successful requests can also extend elapsed time

### Requirement: Optional substance failures remain explicit and recoverable
An exhausted GSRS lookup SHALL remain an explicit source error, not an empty successful listing, and SHALL NOT cache a failure. A later lookup SHALL be able to recover through the ordinary successful-response path.

#### Scenario: Optional substance service does not answer
- **WHEN** both attempts time out while resolving a substance name
- **THEN** the optional lookup reports its refusal after those two attempts, records no empty success, and lets normal preparation continue with its existing warning

#### Scenario: Substance service recovers
- **WHEN** the failed lookup is asked again and the source now answers successfully
- **THEN** the source is contacted again and only the successful response becomes reusable

### Requirement: Registry searches retain the evidence needed to judge treatment roles
Both ClinicalTrials.gov clients SHALL request study type, intervention descriptions and arm membership, arm types and arm descriptions in name and trial-title search responses. They SHALL preserve existing query, page, pacing and cache bounds and SHALL NOT add individual-record requests solely to obtain those fields.

#### Scenario: Search response is projected to requested fields
- **WHEN** the registry returns only the requested fields for an experimental arm and its comparator
- **THEN** both clients retain their types, intervention membership and descriptions in the same search response

#### Scenario: Search finds expanded access
- **WHEN** a name search returns an expanded-access record
- **THEN** the scorer receives its study type without fetching that record separately

### Requirement: A refused condition has one bounded discovery fallback
When ClinicalTrials.gov explicitly refuses the condition field of a condition-scoped search, the client SHALL try the existing distinct condition-keyword wording once, if available. Both broad-name and search-phrase discovery SHALL use this behavior. The intervention name SHALL remain unchanged and no unscoped search SHALL replace it.

#### Scenario: Long precise condition is refused
- **WHEN** the registry refuses the full condition but accepts the existing keyword wording
- **THEN** the client returns only the bounded candidate set from that condition-scoped fallback, with the treatment name unchanged

### Requirement: Condition fallback preserves discovery limits and clinical scope
The candidate limit and source pacing SHALL remain unchanged. The claim's complete indication SHALL remain the input to match scoring; discovery wording SHALL NOT replace it.

#### Scenario: Fallback remains too broad
- **WHEN** the accepted fallback returns more than one hundred trials
- **THEN** it contributes no candidates and no further page or broader query is requested

### Requirement: Unusable searches remain explicit refusals
A refused fallback, or an initial refusal with no distinct fallback, SHALL remain an explicit search error rather than an empty successful result. An intervention-field refusal, an unknown-field refusal, or another source error SHALL NOT trigger this fallback.

#### Scenario: No usable condition wording
- **WHEN** the fallback is also refused, or no distinct keyword wording exists
- **THEN** the search refusal is reported and no further query is sent

#### Scenario: Refused treatment or unknown field
- **WHEN** the registry refuses the intervention field or names an unknown field
- **THEN** the error is reported without rewriting the treatment or condition

### Requirement: Expired answers can be deleted
An operator SHALL be able to delete every cached answer whose lifetime has passed, and SHALL be told how many were deleted. An answer still within its lifetime SHALL be kept.

#### Scenario: One expired and one fresh
- **WHEN** the cache holds one answer that expired yesterday and one that expires tomorrow, and the operator deletes the expired answers
- **THEN** the first is deleted, the second is kept, and the operator is told that one was deleted

#### Scenario: A deleted answer is asked for again
- **WHEN** a request whose cached answer was deleted is made again
- **THEN** it is sent to the source, as it would have been had the expired answer been kept

### Requirement: A subject term is looked up by identifier and by label
The vocabulary client SHALL return a term's record, with its label and definition, for the term's identifier, and SHALL return the terms whose label, or one of whose entry terms, equals a given name, each with the entry term that was equal when it was not the label. A label or entry term that only contains the name SHALL NOT be returned as equal. An unknown identifier SHALL return nothing.

#### Scenario: Name equal to an entry term only
- **WHEN** the client is asked for terms equal to "Ketogenic Diet" and no term has that label but one lists it as an entry term
- **THEN** that term is returned with its own label and the entry term that was equal

#### Scenario: Entry term of a supplementary record
- **WHEN** the client is asked for terms equal to a name that is the entry term of a supplementary record
- **THEN** the supplementary record is returned with its identifier and label

#### Scenario: Supplementary record's definition
- **WHEN** the client is asked for a supplementary record by its identifier
- **THEN** it returns the record's label and its note as the definition

### Requirement: A gene is looked up by symbol
The target client SHALL return, for a word, each human gene whose approved symbol or a listed synonym of it equals the word without regard to case, saying which of the two was equal, with the protein's name and function description. A gene whose symbol or synonyms only resemble the word SHALL NOT be returned.

#### Scenario: Word equal to an approved symbol
- **WHEN** the client is asked for "CXCR3"
- **THEN** it returns the gene with that approved symbol and says the symbol was equal

#### Scenario: Word the search answers with unrelated genes
- **WHEN** the client is asked for a word and the source's search returns genes whose symbols and synonyms are all different from it
- **THEN** it returns nothing

#### Scenario: Known identifier
- **WHEN** the client is asked for a term by an identifier the vocabulary holds
- **THEN** it returns the term's label and definition with the time it was fetched

#### Scenario: Name contained in a longer label
- **WHEN** the client is asked for terms equal to "Obesity" and the vocabulary also holds "Anti-Obesity Agents"
- **THEN** only "Obesity" is returned

### Requirement: A drug and its target are looked up by name
The drug client SHALL return, for a name, the drug whose own name equals it, with its kind of molecule, its mechanisms and each mechanism's target, and SHALL return nothing when no drug's name equals the given name. For a target that is a single human protein it SHALL return the protein's name, gene symbol and function description.

#### Scenario: Named drug
- **WHEN** the client is asked for a drug by a name the source holds exactly
- **THEN** it returns that drug's kind of molecule and mechanisms

#### Scenario: Name that only resembles a drug's
- **WHEN** the client is asked for a procedure's name and the source's search returns unrelated drugs
- **THEN** it returns nothing

### Requirement: A request sent with a body is cached by its body
When a source is asked by a request that carries a body, the stored answer SHALL be kept under the source, the address and the body together, and a second request with the same three SHALL be answered from the store while it is fresh. The request SHALL follow the same pacing, retries, client identification and refusal for an unrecorded source as any other.

#### Scenario: Two queries to one address
- **WHEN** a source is asked two different queries at the same address
- **THEN** each gets its own answer and neither is served the other's

#### Scenario: Same query twice
- **WHEN** the same query is asked again within the time its answer is kept
- **THEN** no request is sent

### Requirement: A source is used only once its terms are recorded
A client for a source SHALL refuse to make a request unless the source is recorded in the project's list of sources with its terms, licence and the date they were read. The refusal SHALL name the source.

#### Scenario: Source not yet recorded
- **WHEN** a lookup is asked of a source with no recorded terms
- **THEN** no request is made and the output says the source's terms must be recorded first

### Requirement: A substance is looked up by an exact name
A substance registry client SHALL return the substances the registry lists under a given name, each with every name the registry lists for it and the kind of each name. A substance SHALL be returned only when one of its listed names equals the name asked for, ignoring letter case and runs of spaces and nothing else. The client SHALL NOT try a part of the name, another spelling or a similar name. The names the registry marks as codes SHALL be readable from the record as the registry writes them, leaving out any it has withdrawn.

#### Scenario: Substance listed under the name
- **WHEN** the registry lists one substance under the name asked for
- **THEN** that substance's record is returned with its identifier, its page, all its names and the fetch time, and the names marked as codes can be read from it

#### Scenario: Name that only resembles a listed name
- **WHEN** the registry's own search answers a name with a substance whose listed names differ from it by punctuation
- **THEN** no substance is returned

#### Scenario: Name the registry does not list
- **WHEN** the registry lists no substance under the name
- **THEN** no substance is returned and nothing else is asked

### Requirement: A brand is looked up by its exact name
A client of a source that files brand names under ingredients SHALL return the ingredients the source lists for the brand of a given name, one record for each ingredient, each with the ingredient's identifier, its page, its name, the brand's own record and the source's answer listing the brand's ingredients as fetched, and the fetch time. For a brand of one ingredient the client SHALL also read the brand's branded drugs and the vaccine code (CVX) the source gives each, until one carries a vaccine's code, and SHALL keep those answers as fetched with the record.  A brand SHALL be found only when the source's own exact search answers the name with a concept the source marks as a brand and whose name equals the name asked for, ignoring letter case and runs of spaces and nothing else. The client SHALL NOT use the source's normalised or approximate search, try a part of the name or another spelling, or resolve a name the source lists as anything other than a brand. An answer SHALL be whole or nothing. The client SHALL return nothing only when the source answers that no concept, or no brand, has the name. When the exact search's answer cannot be read, a concept's identifier cannot be read, more concepts carry the name than the client reads, or a concept's own record, its list of ingredients, its list of branded drugs or a branded drug's vaccine code answer is missing, or a brand of one ingredient has more than twenty branded drugs, the client SHALL say that the source could not answer whole, as for a source that cannot be asked, and SHALL return no record: the source has not said the name is no brand. It SHALL use the same shorter network waits as the optional substance lookup.

#### Scenario: Brand listed under one ingredient
- **WHEN** the source lists the name asked for as a brand of one ingredient
- **THEN** one record is returned, for that ingredient, with the brand's record and the list of ingredients as fetched

#### Scenario: Brand the source does not list
- **WHEN** the source's exact search finds no concept under the name
- **THEN** nothing is returned and nothing else is asked

#### Scenario: Brand listed under two ingredients
- **WHEN** the source lists the brand under two ingredients
- **THEN** two records are returned, which do not count as one substance

#### Scenario: Name more concepts carry than are read
- **WHEN** the source's exact search answers the name with more concepts than the client's limit
- **THEN** no concept is read, no record is returned, and the client says the name is listed under too many concepts to identify one

#### Scenario: A name search the client cannot read
- **WHEN** the exact search answers with a body that is not an object, or with a concept identifier that is not a number
- **THEN** no record is returned, and the client says the source could not answer whole

#### Scenario: Part of a brand's answer is missing
- **WHEN** two brand concepts carry the name and the record or the list of ingredients of one is not found, or a brand's branded drugs or one's vaccine code answer is not found, or it has more than twenty branded drugs
- **THEN** no record is returned, and the client says the source could not answer whole

#### Scenario: Name that is not a brand
- **WHEN** the source lists the name as an ingredient and not as a brand
- **THEN** nothing is returned and its ingredients are not asked for

#### Scenario: Name that only resembles a brand
- **WHEN** the source's search answers with a brand whose own name differs from the name asked for
- **THEN** nothing is returned

### Requirement: A stated wait is honoured in either form and bounded
A wait a source states SHALL be honoured whether it is given as a number of seconds or as a time. No single wait inside a fetch SHALL be longer than a configured ceiling, sixty seconds unless set. A source that asks for a longer wait SHALL be treated as one that cannot be asked now: the fetch SHALL end at once, saying until when.

#### Scenario: A wait given as a time
- **WHEN** a source answers too-many-requests and states the time at which it may be asked again, twenty seconds ahead
- **THEN** the next attempt is made no sooner than that time

#### Scenario: A wait longer than the ceiling
- **WHEN** a source states a wait of one hour
- **THEN** the fetch ends without waiting, and its caller is told the source cannot be asked for an hour

### Requirement: A pause is seen by every process
When a source cannot be asked until a time, that time SHALL be kept where every process and every later run reads it, and no request SHALL be sent to that source before it by any command. A command that needs the source SHALL be told the source is paused and until when, without sending a request.

#### Scenario: Two commands and one throttled source
- **WHEN** one command is told by a registry to wait an hour, and a second command starts a minute later
- **THEN** the second sends that registry no request and reports that it is paused and until when

#### Scenario: The pause has passed
- **WHEN** the time a source was paused until has passed
- **THEN** the next command asks it as usual

#### Scenario: A paper search is rolled back after its allowance runs out
- **WHEN** OpenAlex refuses a search because its free allowance is exhausted and the current claim transaction is rolled back
- **THEN** another process that searches before reset reads the stored pause and sends no search

#### Scenario: A pause begins while a client awaits its turn

- **WHEN** a request was admitted for 12:00:10 and another worker records a pause until 13:00 during the pacing wait
- **THEN** the client sends no request during the pause and reports the persisted deadline

### Requirement: Every command's requests count against the source's allowance
Requests to a source SHALL be counted against that source's allowance whichever command sends them. A command SHALL send no request to a source whose allowance for the period is used up.

#### Scenario: Preparing claims and a backfill share a registry
- **WHEN** a backfill step and the preparation of claims ask one registry in the same period
- **THEN** the allowance's count holds the requests of both

### Requirement: Try later is told apart from not found
A fetch that ends because the source could not be asked, was paused, or failed on every attempt SHALL give its caller a result that says so and until when, where the source said. It SHALL NOT give an empty result, and SHALL NOT be stored as an answer.

#### Scenario: A search while the registry is down
- **WHEN** a registry fails on every allowed attempt of a search
- **THEN** the caller is told the search did not run, and nothing records that the search found no trial

#### Scenario: A registry refuses access
- **WHEN** a registry returns 401 or 403 for a request
- **THEN** the caller is told that the registry cannot be asked and stops the step with the record still due

#### Scenario: A paper fetch omits a searched PubMed number
- **WHEN** a search returns PubMed numbers and a fetch fails to return their records
- **THEN** the batch stays due and the caller reports that the records could not be fetched

### Requirement: Literature search by words
A literature source SHALL support searching papers by words and SHALL return, in the source's own order of relevance and up to a stated limit, records that carry title, authors with their institutions where the source gives them, publication date, kind of paper and DOI when available.

#### Scenario: Search with results
- **WHEN** the literature is searched for an intervention and a condition that five papers concern, with a limit of twenty
- **THEN** five paper records are returned, most relevant first

#### Scenario: Search with more results than the limit
- **WHEN** a search matches three hundred papers and the limit is twenty
- **THEN** twenty records are returned and no further page is requested

### Requirement: A source that needs a key refuses without it
A source that requires a key SHALL send no request while the key is not configured, and the error SHALL name the missing setting. The key SHALL NOT appear in a cached request, a log line or a recorded fixture.

#### Scenario: Missing key
- **WHEN** a literature search is attempted and the source's key is not configured
- **THEN** no request is sent and the error names the setting

### Requirement: A source's daily allowance is respected
When a source reports that the day's allowance is used up, the client SHALL stop asking that source for the rest of the run and SHALL report it as the reason, without retrying.

#### Scenario: Allowance used up
- **WHEN** a source answers that the daily allowance is exhausted
- **THEN** the fetch fails with that reason and later searches in the same run are not sent

#### Scenario: Another run on the same day
- **WHEN** one run has used the day's allowance up and another run or process searches before it resets
- **THEN** no search is sent and the reason is reported

#### Scenario: Paid credit on the account
- **WHEN** a source's answer shows that the account holds prepaid credit
- **THEN** no further search is sent until the allowance resets, and the reason given names the credit

#### Scenario: Allowance not stated
- **WHEN** a source's answer to a charged search does not state what is left
- **THEN** no further search is sent until the next day

### Requirement: A charged search is not repeated needlessly
A source that charges for each search SHALL be asked once for all the terms of a claim where it can take them together, SHALL NOT be asked a looser search when that one finds nothing, SHALL keep a search's answer for seven days, and SHALL report for each run how many searches it sent, what they cost and what is left of the allowance.

#### Scenario: Intervention with a name and two phrases
- **WHEN** the literature is searched for a claim whose intervention has a name and two search phrases
- **THEN** one search is sent that names all three together with the indication

#### Scenario: The one search finds nothing
- **WHEN** the search for all of a claim's terms finds no paper
- **THEN** the result is empty, no second or looser search is sent, and the run reports that the claim has no related paper

#### Scenario: Claim resolved again within the week
- **WHEN** the same search was answered three days ago
- **THEN** the kept answer is used and no search is sent

#### Scenario: End of a run
- **WHEN** a run that sent one search ends
- **THEN** it reports one search, its cost and what the source said is left of the day

### Requirement: Organisation lookups
An organisation source SHALL support looking an organisation up by name and SHALL return records that carry the organisation's identifier, name, country, website and the source's measure of how well the name matched.

#### Scenario: Known organisation
- **WHEN** an organisation is looked up by a name the source matches
- **THEN** a record is returned with its identifier and match measure

#### Scenario: Unknown organisation
- **WHEN** an organisation is looked up by a name the source does not match
- **THEN** an empty result is returned and no error is raised
