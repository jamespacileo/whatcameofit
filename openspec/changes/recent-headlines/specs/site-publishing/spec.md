# Spec Delta

## ADDED Requirements

### Requirement: Recent reports on the home page
The home page SHALL list the most recently published source articles of published claims, newest first, at most ten. Each entry SHALL show the article's title as the outlet wrote it, marked as a quotation, with the outlet, the publication date and the claim's current status. The title SHALL link to the claim page and the outlet SHALL link to the article.

#### Scenario: Reports from several claims
- **WHEN** three published claims have four source articles between them
- **THEN** the home page lists all four in order of publication date, newest first, each with its claim's status

#### Scenario: Headline wording
- **WHEN** an article's title makes a stronger statement than the claim's status supports
- **THEN** the title is shown in quotation marks with its outlet, next to the status derived from the evidence, and the site adds no wording of its own about the title

#### Scenario: Unpublished claims
- **WHEN** a claim has not been approved in review
- **THEN** none of its articles appears on the home page

### Requirement: Topics are filed under groups
The export SHALL carry, for each vertical, the group it is configured under, or none. When any listed topic has a group, the topic directory SHALL list topics under their groups' names, groups in alphabetical order and topics in alphabetical order within each, with topics that have no group last; its jump links SHALL lead to the groups, and its filter SHALL match a group's name as well as a topic's. When no listed topic has a group, the directory SHALL list topics under their first letters. The site SHALL NOT assign a topic to a group itself.

#### Scenario: Topics with groups
- **WHEN** a listed topic is configured under a group
- **THEN** the topic directory shows the topic under that group's name and offers a jump link to the group

#### Scenario: No topic has a group
- **WHEN** no listed topic has a group
- **THEN** the topic directory lists topics under their first letters, with a jump link for each letter

### Requirement: Topics are listed once they have a published claim
Menus and lists of topics SHALL include a vertical only when at least one published claim belongs to it. The index page of a vertical without published claims SHALL still exist.

#### Scenario: Vertical with no published claims
- **WHEN** a vertical is configured and none of its claims is published
- **THEN** its index page says no claims are tracked, and no menu or list links to it

#### Scenario: One listed topic
- **WHEN** exactly one vertical has published claims
- **THEN** the menu names that topic and links straight to its index
