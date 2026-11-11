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

### Requirement: Outlets are shown with their own icon
The pipeline SHALL fetch, at most once per outlet domain, the small icon that the outlet's own site serves, and store the image with its address and fetch time. An outlet domain is the host of a source article's URL without a leading `www.`. Before any request to a host the pipeline SHALL read that host's robots.txt and SHALL send nothing further when the rules refuse it or cannot be read. Every request SHALL identify the client with the contact address, and requests SHALL be spaced at least one second apart. Only a raster image (PNG, ICO, GIF, JPEG or WebP, told from the file's own bytes) of at most 100,000 bytes SHALL be stored; a domain with no such image SHALL be recorded as asked and not asked again unless the operator asks for a retry.

The export SHALL carry the stored image itself, as a data URI, for each outlet domain that has an exported article and an icon, and SHALL NOT carry an address for the site to fetch. Wherever the site names an outlet it SHALL show that icon, served as a file of the site, and SHALL draw a letter tile when the export has none. No page SHALL request an icon, or anything else it displays, from another host.

#### Scenario: Outlet with an icon
- **WHEN** an outlet's robots.txt allows it and its site serves a small raster icon
- **THEN** the icon is stored for the outlet's domain with the address it came from and the time it was fetched

#### Scenario: Outlet whose robots.txt refuses
- **WHEN** an outlet's robots.txt disallows the client, or cannot be read
- **THEN** no other request is sent to that host and no icon is stored for it

#### Scenario: Icon over the size cap
- **WHEN** the file an outlet serves is larger than the cap, or is not a raster image
- **THEN** it is not stored

#### Scenario: Outlet asked before
- **WHEN** the icons command runs again
- **THEN** no request is sent for a domain that was asked before

#### Scenario: Export of an outlet's icon
- **WHEN** a published claim has an article from an outlet whose icon is stored
- **THEN** the export lists that outlet's domain with the image as a data URI and its fetch time

#### Scenario: Outlet with a stored icon
- **WHEN** a page names an outlet whose icon is in the export
- **THEN** the page shows the icon from a file of the site itself

#### Scenario: Outlet with no stored icon
- **WHEN** a page names an outlet with no icon in the export
- **THEN** the page shows a letter tile in its place

### Requirement: Topics are listed once they have a published claim
Menus and lists of topics SHALL include a vertical only when at least one published claim belongs to it. The index page of a vertical without published claims SHALL still exist.

#### Scenario: Vertical with no published claims
- **WHEN** a vertical is configured and none of its claims is published
- **THEN** its index page says no claims are tracked, and no menu or list links to it

#### Scenario: One listed topic
- **WHEN** exactly one vertical has published claims
- **THEN** the menu names that topic and links straight to its index
