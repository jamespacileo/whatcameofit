# Spec Delta

## MODIFIED Requirements

### Requirement: Pages can be found and cited
Every public page SHALL state its canonical address, built from the site's configured public address. Every claim page SHALL carry structured data that names the page, describes it, the date the claim was first reported, the date the registries were last checked, its card image and the site as publisher. The home page SHALL carry structured data naming the site and its publisher with a logo. Claim, topic, source and year pages SHALL carry a breadcrumb trail as structured data. The data page SHALL describe the open dataset, its licence and its download. The site SHALL NOT use fact-check, review or rating markup, because each states a verdict. The site SHALL publish a sitemap listing every public page except embed pages, and a `robots.txt` that names the sitemap. Every page SHALL announce the site's feeds. A preview build SHALL ask search engines not to index any page, SHALL publish no sitemap, and its `robots.txt` SHALL disallow every page.

#### Scenario: Claim page read by a search engine
- **WHEN** a search engine reads a claim page of a public build
- **THEN** it finds the canonical address, the first-reported and last-checked dates, a breadcrumb trail, and no rating or review markup

#### Scenario: Crawler arrives
- **WHEN** a crawler reads `robots.txt` of a public build
- **THEN** it is allowed every page and told where the sitemap is

#### Scenario: Preview build
- **WHEN** the site is built as a preview
- **THEN** every page asks not to be indexed, no sitemap is published, and `robots.txt` disallows every page

#### Scenario: Public address not configured
- **WHEN** a public build is made while the configured address is a local one
- **THEN** the build stops and says that the public address must be set

## ADDED Requirements

### Requirement: Every page has a complete link preview
Every page SHALL state, for link previews, its title, description, canonical address, the site's name, the locale `en_GB`, an image with its width, height, type and text alternative, and a large-image card for X with the same alternative. Claim pages SHALL be typed as articles with the date first reported as published time and the date last checked as modified time; every other page SHALL be typed as a website. Every page SHALL state the site's theme colour.

#### Scenario: Claim link pasted into a chat
- **WHEN** a claim page's address is pasted into a messenger that reads link previews
- **THEN** it finds the wide card with its size and alternative, the page's own address and the article's dates

#### Scenario: Home page shared
- **WHEN** the home page's address is shared
- **THEN** its preview is typed as a website and shows the site's card
