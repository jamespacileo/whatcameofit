# Spec Delta

## ADDED Requirements

### Requirement: A subject term is looked up by identifier and by label
The vocabulary client SHALL return a term's record, with its label and definition, for the term's identifier, and SHALL return the terms whose label equals a given name. A label that only contains the name SHALL NOT be returned as equal. An unknown identifier SHALL return nothing.

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

### Requirement: A source is used only once its terms are recorded
A client for a source SHALL refuse to make a request unless the source is recorded in the project's list of sources with its terms, licence and the date they were read. The refusal SHALL name the source.

#### Scenario: Source not yet recorded
- **WHEN** a lookup is asked of a source with no recorded terms
- **THEN** no request is made and the output says the source's terms must be recorded first
