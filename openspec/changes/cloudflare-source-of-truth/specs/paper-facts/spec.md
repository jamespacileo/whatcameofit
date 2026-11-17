## MODIFIED Requirements

### Requirement: The stored record holds no abstract and no author
The record a paper's facts are read from SHALL be stored with the time it was fetched. Before any literature index's record of a paper is stored, whether for its facts, as a follow-up paper's evidence event or as a retraction notice, its abstract, author names, author identifiers and affiliations and its full-text links SHALL be removed, for every index the pipeline asks (Europe PMC, OpenAlex, Crossref, PubMed). Paper facts SHALL NOT carry an author, an affiliation or any text from an abstract. A paper's authors and abstract MAY be read from the record as fetched, before it is stored, to judge whether it follows up an origin paper.

#### Scenario: Record with an abstract and eleven authors
- **WHEN** a paper's record is stored for its facts
- **THEN** the stored record has no abstract and names no author

#### Scenario: A follow-up paper's event
- **WHEN** a citing paper that shares an author and names the intervention in its abstract is stored as a follow-up event
- **THEN** the event's payload names no author and holds no abstract, and the paper's facts read from it are the same as from the record as fetched
