# Spec Delta

## MODIFIED Requirements

### Requirement: Checks precede production deployment
Pull requests and pushes to main SHALL have the existing project checks and a production dry run, each either run or answered by a recorded pass for the same inputs (`delivery-time`). Only a main push or main manual run with successful checks SHALL deploy production. The deployment SHALL publish the build that the dry run checked, or build and check afresh. A pull request SHALL NOT change production. Production deployments SHALL be serialized and checked with live HTTP requests.

#### Scenario: A pull request passes
- **WHEN** all checks succeed on a pull request
- **THEN** production is unchanged

#### Scenario: Main passes
- **WHEN** checks succeed for the current main revision
- **THEN** GitHub builds the reviewed snapshot, deploys it to the configured domain, and checks the live site

#### Scenario: Main has the files a pull request already passed
- **WHEN** a push to main has the same files and settings as a run on a branch of this repository whose checks and dry run passed
- **THEN** the checks are answered by that pass, the build it checked is deployed, and the live site is checked

#### Scenario: The checked build is not available
- **WHEN** the build that the dry run checked is absent or fails its digest
- **THEN** the site is built and checked afresh before anything is deployed

#### Scenario: A check has no recorded pass
- **WHEN** any check has neither run successfully nor a recorded pass for the same inputs
- **THEN** production is not deployed

### Requirement: A pull request has a preview for as long as it is open
A pull request from a branch of this repository SHALL be published to its own Worker, named for the pull request's number, at a workers.dev address. The preview SHALL be replaced when a push changes anything the site or its Worker is made from, and SHALL be left as it is when a push changes none of it. The preview SHALL be deleted when the pull request is merged or closed. The pull request SHALL carry one comment giving the address, edited in place. A pull request from a fork SHALL NOT be given the Cloudflare secret and SHALL NOT get a preview. Publishing a preview SHALL NOT wait for the checks and SHALL NOT change production.

#### Scenario: A pull request is opened
- **WHEN** a pull request is opened from a branch of this repository
- **THEN** its site is published to a Worker named for its number, and a comment gives the address

#### Scenario: A pull request is pushed to
- **WHEN** a new commit that changes a file the site is built from is pushed to an open pull request
- **THEN** the same Worker serves the new build and the same comment is updated

#### Scenario: A push changes nothing the site is made from
- **WHEN** a new commit is pushed whose site files, Worker files and build settings are those the published preview says it was made from
- **THEN** nothing is built or sent, the Worker is unchanged, and the comment names the new commit

#### Scenario: The preview cannot say what it was made from
- **WHEN** the preview is absent, cannot be reached, or carries no record of what it was made from
- **THEN** the site is built and published

#### Scenario: A pull request is closed
- **WHEN** a pull request is merged or closed
- **THEN** its Worker is deleted and the comment says the preview was removed

#### Scenario: A pull request from a fork
- **WHEN** a pull request is opened from a fork
- **THEN** no preview is published and no secret is read

#### Scenario: Not a pull request number
- **WHEN** the preview command is given anything but a positive whole number
- **THEN** it stops and publishes nothing
