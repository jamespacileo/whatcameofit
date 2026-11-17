# Spec Delta

## ADDED Requirements

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
