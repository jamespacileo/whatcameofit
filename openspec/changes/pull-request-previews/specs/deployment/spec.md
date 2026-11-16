## ADDED Requirements

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

## MODIFIED Requirements

### Requirement: Checks precede production deployment
Pull requests and pushes to main SHALL run the existing project checks and a production dry run. Only a main push or main manual run with successful checks SHALL deploy production. A pull request SHALL NOT change production. Production deployments SHALL be serialized and checked with live HTTP requests.

#### Scenario: A pull request passes
- **WHEN** all checks succeed on a pull request
- **THEN** production is unchanged

#### Scenario: Main passes
- **WHEN** checks succeed for the current main revision
- **THEN** GitHub builds the reviewed snapshot, deploys it to the configured domain, and checks the live site

### Requirement: The site is deployed only to its public address
The deploy command SHALL refuse an address that is missing, local, not HTTPS, or that carries a path. It SHALL build a public build for that address and publish to that address's domain only. A production deployment SHALL NOT create any other public address for the site. The only other public addresses SHALL be pull request previews.

#### Scenario: Address missing
- **WHEN** no public address is given
- **THEN** the command stops and says how to give one

#### Scenario: Address local
- **WHEN** the address given is a local one
- **THEN** the command stops and publishes nothing
