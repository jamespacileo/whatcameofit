# Spec Delta

## ADDED Requirements

### Requirement: The bundle holds page files, their schemas and a manifest
A bundle SHALL hold one JSON file for each page, at `<page model>/<key>.json`, one JSON Schema for each page model, a file of moved addresses, and a manifest. The manifest SHALL state the bundle's checksum, the count of files by page model, the versions of the steps that made the pages, and when it was made. A bundle SHALL hold no article text and nothing the lab marks private.

#### Scenario: A bundle is read
- **WHEN** the site reads a bundle whose manifest counts 120 pair pages
- **THEN** it finds 120 files under the pair page model, each fitting that model's schema

#### Scenario: A file is missing
- **WHEN** the manifest counts 120 pair pages and 119 files are present
- **THEN** the build stops and names the page model and both counts

### Requirement: The site is built from one bundle version
The build SHALL read the version the pointer names, check the bundle's checksum against its manifest, and record that version in the built site. Pages built ahead and pages rendered on request SHALL read the same version for the life of a deployment.

#### Scenario: A newer bundle is published after a deployment
- **WHEN** a bundle is published and the pointer moved while a deployment is live
- **THEN** the live site's pages, built and on request, still show the version it was built from

#### Scenario: The checksum does not match
- **WHEN** the files' checksum differs from the manifest's
- **THEN** the build stops before any page is written

### Requirement: A bundle the site does not know is refused
The build SHALL generate its types and validators from the bundle's schemas and SHALL stop when a page model the site renders is absent, when a file does not fit its schema, or when a status code has no wording in the site.

#### Scenario: A status code without wording
- **WHEN** a pair's file carries a status code the site has no label for
- **THEN** the build stops and names the code

#### Scenario: A page model the site does not render
- **WHEN** the bundle holds a page model the site has no page for
- **THEN** the build succeeds, publishes none of its files, and says so in its summary

### Requirement: The build needs no database and no outside service but the bundle
The site SHALL be built from a bundle on disk with no network, and tests SHALL build a small bundle of real page files kept with the tests.

#### Scenario: Offline build
- **WHEN** the site is built on a machine that holds a bundle and has no network
- **THEN** the build succeeds
