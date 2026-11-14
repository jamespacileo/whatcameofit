## ADDED Requirements

### Requirement: A topic has a card
A topic page's link preview SHALL be a card for that topic: the topic's name with its drawing, where its claims stand in the words of the topic's summary, the month the registries were checked, and "Not medical advice". It SHALL carry no claim's headline, no outlet's title and no word that judges a claim. Its text alternative SHALL be built from the same facts.

#### Scenario: A topic link in a forum post
- **WHEN** a link to a topic with seven claims is posted where previews are drawn
- **THEN** the preview shows the topic's name, a sentence counting its claims by status, and the checked month

#### Scenario: A topic with one claim
- **WHEN** a topic has one published claim
- **THEN** its card says one reported breakthrough is tracked and where it stands
