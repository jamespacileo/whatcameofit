# Spec Delta

## ADDED Requirements

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
