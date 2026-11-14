# deployment Specification

## Purpose
How the public site reaches its address: only a public export is built, only for the site's own address, and only after the tests and a deployment rehearsal have passed on `main`.

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

### Requirement: Only a reviewed export is deployed
The deploy command SHALL refuse to publish when the export is a preview or when it holds no claims. Since the operator's decision of 2026-11-13 (change `auto-publish`), a claim decided by a rule or an assistant SHALL be published; the export says which claims a person checked. It SHALL write its own normal export from the pipeline before checking, so that a local setting does not decide what is published.

#### Scenario: Reviewed export and a public address
- **WHEN** a non-preview export holds claims and the address is a public HTTPS address
- **THEN** no reason to stop is reported

#### Scenario: Preview export
- **WHEN** the export is a preview
- **THEN** the command stops, says that a preview is never deployed, and publishes nothing

#### Scenario: Claim not checked by a person
- **WHEN** one claim in the export was approved by a rule and never by the operator
- **THEN** the command does not stop for it, and the claim is published marked as not checked by a person

### Requirement: The site is deployed only to its public address
The deploy command SHALL refuse an address that is missing, local, not HTTPS, or that carries a path. It SHALL build a public build for that address and publish to that address's domain only. The deployment SHALL NOT create any other public address for the site.

#### Scenario: Address missing
- **WHEN** no public address is given
- **THEN** the command stops and says how to give one

#### Scenario: Address local
- **WHEN** the address given is a local one
- **THEN** the command stops and publishes nothing

### Requirement: A deployment can be rehearsed
A dry run SHALL make every check and build the public build, and SHALL publish nothing.

#### Scenario: Dry run
- **WHEN** the operator runs the dry run with a reviewed export and a public address
- **THEN** the site is built for that address, the host's tool reads the built files, and nothing is uploaded
