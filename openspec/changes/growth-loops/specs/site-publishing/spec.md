# Spec Delta

## ADDED Requirements

### Requirement: A claim's title ends with its status
A claim page's title, as a browser tab and a search result show it, SHALL give the intervention, the indication and then the claim's status in the site's wording. When the whole is too long, the intervention and indication SHALL be shortened at a word and the status SHALL be kept whole. The title shared in a link preview SHALL remain the claim's headline.

#### Scenario: Claim in a search result
- **WHEN** a search engine reads the page of a claim about an anti-USAG-1 antibody for congenital tooth agenesis whose status is a Phase 1 trial
- **THEN** the page's title ends with "Phase 1 trial"

#### Scenario: Long names
- **WHEN** the intervention and indication together run to ninety characters
- **THEN** they are cut at a word with an ellipsis and the status label is not cut

### Requirement: Search engines may show large previews
Every page of a public build SHALL tell search engines that they may show its preview image at large size. A preview build SHALL NOT say so, and SHALL keep asking not to be indexed.

#### Scenario: Claim page of a public build
- **WHEN** a search engine reads a claim page of a public build
- **THEN** it finds permission to show a large image preview

### Requirement: The sitemap dates claim pages
The sitemap SHALL give, for each claim page, the date the claim's status was last set. A page with no such date SHALL be listed without one. The sitemap SHALL NOT give the build date as a page's date.

#### Scenario: Status set last month
- **WHEN** a claim's status was last set on 10 November 2026
- **THEN** its sitemap entry carries that date

#### Scenario: Rebuilt with nothing changed
- **WHEN** the site is rebuilt a week later and the claim's status is unchanged
- **THEN** the claim's sitemap date is unchanged

### Requirement: The site can be installed and shared to
The site SHALL be installable from a browser that offers it. An installed copy SHALL appear among the places an article can be shared to, on systems that support it, and sharing an article to it SHALL open the home page with that article's address in the lookup box and the lookup run. The shared address SHALL NOT appear in the page's address.

#### Scenario: Article shared from a phone's browser
- **WHEN** a reader with the site installed shares a tracked article to it
- **THEN** the home page opens with that claim's status shown, and the page's address carries no part of the article's address

#### Scenario: Shared text with no address
- **WHEN** what is shared holds no web address
- **THEN** the home page opens with the lookup box empty and no error shown

#### Scenario: Browser that cannot install the site
- **WHEN** a reader uses a browser with no install or share-target support
- **THEN** every page works as before

### Requirement: The site says where to get the extension
When a store address for the browser extension is configured, the home page and the method page SHALL link to it, naming the browser. With none configured, no such link SHALL be drawn. The link SHALL load nothing from the store until the reader follows it.

#### Scenario: Chrome store address configured
- **WHEN** the site is built with the Chrome store address set and no Safari address
- **THEN** the home page links to the Chrome listing and shows no Safari link

#### Scenario: No store address configured
- **WHEN** the site is built with no store address
- **THEN** no page shows an install link
