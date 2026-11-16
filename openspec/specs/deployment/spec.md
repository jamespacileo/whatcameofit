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
Pull requests and pushes to main SHALL run the existing project checks and a production dry run. Only a main push or main manual run with successful checks SHALL deploy production. A pull request SHALL NOT change production. Production deployments SHALL be serialized and checked with live HTTP requests.

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
The deploy command SHALL refuse an address that is missing, local, not HTTPS, or that carries a path. It SHALL build a public build for that address and publish to that address's domain only. A production deployment SHALL NOT create any other public address for the site. The only other public addresses SHALL be pull request previews.

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

### Requirement: A pull request has a preview for as long as it is open
A pull request from a branch of this repository SHALL be published to its own Worker, named for the pull request's number, at a workers.dev address. The preview SHALL be replaced when the pull request is pushed to and deleted when it is merged or closed. The pull request SHALL carry one comment giving the address, edited in place. A pull request from a fork SHALL NOT be given the Cloudflare secret and SHALL NOT get a preview. Publishing a preview SHALL NOT wait for the checks and SHALL NOT change production.

#### Scenario: A pull request is opened
- **WHEN** a pull request is opened from a branch of this repository
- **THEN** its site is published to a Worker named for its number, and a comment gives the address

#### Scenario: A pull request is pushed to
- **WHEN** a new commit is pushed to an open pull request
- **THEN** the same Worker serves the new build and the same comment is updated

#### Scenario: A pull request is closed
- **WHEN** a pull request is merged or closed
- **THEN** its Worker is deleted and the comment says the preview was removed

#### Scenario: A pull request from a fork
- **WHEN** a pull request is opened from a fork
- **THEN** no preview is published and no secret is read

#### Scenario: Not a pull request number
- **WHEN** the preview command is given anything but a positive whole number
- **THEN** it stops and publishes nothing

### Requirement: A preview is not mistaken for the site and cannot spend
A preview SHALL be built from the pull request's staged public snapshot as a public build for the production address. Every file of a preview SHALL be sent with a header asking search engines not to index it. A preview SHALL NOT be given model settings, provider keys or the saved-results store, so its registry search answers that it is not set up. A preview export SHALL be refused as it is for production.

#### Scenario: A search engine reaches a preview
- **WHEN** a page of a preview is requested
- **THEN** the response asks not to be indexed, and the page's canonical link names the production address

#### Scenario: A lookup is sent to a preview
- **WHEN** a registry search is requested from a preview
- **THEN** it answers that the search is not set up, and no model or literature provider is asked
