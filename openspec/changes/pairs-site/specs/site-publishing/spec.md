# Spec Delta

## MODIFIED Requirements

### Requirement: Build from the export alone
The site SHALL be built from one bundle of page files only, with no access to a database or to external services. A page rendered on request SHALL read only that bundle's files.

#### Scenario: Offline build
- **WHEN** the site is built on a machine that has the bundle and no network or database
- **THEN** the build succeeds

#### Scenario: A listing rendered on request
- **WHEN** a reader opens an intervention's, a clinical category's or a topic's page, none of which the build makes
- **THEN** the Worker reads, from the deployment's bundle version only, the lab's page file for that listing, which of the pairs it names have a pair row and, for a category, which of its broader and narrower categories have a page, and never joins the pair rows themselves
- **AND** the page lists only pairs with a page in that version and links only categories with a page, a narrower one with the count of pairs beneath it, and a category's page credits MeSH
- **AND** the counts the built topics page, clinical index and home page show are the counts of the pages they link
- **AND** an address no listing could have is refused before any read

#### Scenario: A page rendered on request
- **WHEN** the Worker renders a pair page
- **THEN** it reads, from the deployment's bundle version only, that pair's file, the page file of the pair's intervention, and the addresses of that intervention's pairs, and nothing else
- **AND** with no intervention page file in that version the page names no narrower pairs, and an intervention page file that fails its check gives the error page

## ADDED Requirements

### Requirement: A styleguide for staging and previews only
The site SHALL offer a styleguide at `/styleguide` that draws every shared building block of the pages (`site/src/lib/blocks.ts`) and the whole pieces the renderers make of them, with the bundle the build reads. It SHALL be built only for staging and pull request previews, never for production, and SHALL never be indexed.
Listing examples SHALL use a bounded sample from that bundle. Their individual listing pages keep the full published list.

#### Scenario: Staging and previews
- **WHEN** staging or a pull request's preview is built
- **THEN** `/styleguide` draws each block and piece with that build's bundle, marked noindex in the page and in its headers
- **AND** with no pair page in the bundle it still builds, saying it has none to draw with

#### Scenario: Production
- **WHEN** production is built, whatever the shell running it holds
- **THEN** the build has no styleguide, and a production deploy whose built site holds one stops before publishing

## REMOVED Requirements

### Requirement: Claim page
**Reason**: The operator dropped claims on 2026-11-19; a pair page replaces the claim page (`pair-pages`).
**Migration**: A claim's address redirects to its pair's address. Headlines, summaries and promises return with the lab's reports.
