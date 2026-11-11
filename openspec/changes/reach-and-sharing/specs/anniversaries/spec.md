# Spec Delta

## Purpose

A dated list and feed of the anniversaries of claims' first reports, so that each day offers something true to look back on without anyone writing new words.

## ADDED Requirements

### Requirement: Anniversaries page
The site SHALL have a page that lists published claims by the month and day of their first report, in calendar order, each with the year first reported and the claim's current status. A claim with no first-reported date SHALL NOT be listed. The page SHALL state facts only: the date, the claim's headline and its status. It SHALL NOT describe an anniversary with any word that judges the claim.

#### Scenario: Claims on a calendar
- **WHEN** two published claims were first reported on 31 March 2021 and 31 March 2024
- **THEN** the page lists both under 31 March, each with its year and its current status

#### Scenario: Claim without a first-reported date
- **WHEN** a published claim has no first-reported date
- **THEN** it does not appear on the anniversaries page

#### Scenario: Reader opens the page today
- **WHEN** a reader with scripting on opens the page on a date that has entries
- **THEN** that date's entries are brought into view and marked as today's

### Requirement: Anniversaries feed
The site SHALL publish a feed, in a standard syndication format, with one item for each anniversary that fell within the thirty days up to the day the site was built, newest first. Each item SHALL give the claim's headline, the number of whole years since the first report as of the anniversary date, the claim's current status, and the claim page's address. An item's date SHALL be the anniversary date, never the build date. First reports less than one year old SHALL NOT produce an item.

#### Scenario: An anniversary last week
- **WHEN** the site is built on 5 April 2026 and a claim was first reported on 31 March 2021
- **THEN** the feed holds an item dated 31 March 2026 saying five years have passed, with the claim's current status and address

#### Scenario: Reported this year
- **WHEN** a claim was first reported three months before the build
- **THEN** the feed holds no item for it

#### Scenario: Feed between builds
- **WHEN** the site has not been rebuilt for forty days
- **THEN** the feed's items are still true as dated, because each states the years passed as of its own date
