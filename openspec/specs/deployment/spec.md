# deployment Specification

## Purpose
TBD - created by archiving change github-cloudflare-cicd. Update Purpose after archive.

## Requirements

### Requirement: CI publishes only the staged public snapshot
GitHub SHALL build from `site/data/published-export.json`. It SHALL NOT connect to the private database or substitute seed or preview data. The local `publish-data` command SHALL export reviewed data, validate it, and atomically replace the snapshot only on success. It SHALL NOT approve any review decision.

#### Scenario: Invalid publication input
- **WHEN** the input is malformed, preview, empty, or contains an unchecked claim
- **THEN** staging fails and the previously staged file is unchanged

#### Scenario: Topic publication history
- **WHEN** reviewed data is staged for GitHub
- **THEN** its topic slugs are added to the committed publication history without removing previous slugs
- **AND** the already published dental-regeneration address redirects to mouth-and-teeth

### Requirement: Checks precede production deployment
Pull requests and pushes to main SHALL run the existing project checks and a production dry run. Only a main push or main manual run with successful checks SHALL deploy. Pull requests SHALL NOT receive the Cloudflare secret or publish previews. Production deployments SHALL be serialized and checked with live HTTP requests.

#### Scenario: A pull request passes
- **WHEN** all checks succeed on a pull request
- **THEN** production is unchanged

#### Scenario: Main passes
- **WHEN** checks succeed for the current main revision
- **THEN** GitHub builds the reviewed snapshot, deploys it to the configured domain, and checks the live site

### Requirement: Public addresses and contact links work
The production canonical origin SHALL be https://whatcameofit.com. HTTP SHALL redirect to HTTPS, and www SHALL redirect to the apex while preserving path and query. Suggestion and correction addresses SHALL forward to the operator's verified destination before their links are enabled in production.

#### Scenario: A reader arrives by an alternative address
- **WHEN** a reader requests a page over HTTP or on the www host
- **THEN** they are redirected to the same path and query on https://whatcameofit.com
