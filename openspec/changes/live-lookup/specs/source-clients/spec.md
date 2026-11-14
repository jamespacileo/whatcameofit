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
