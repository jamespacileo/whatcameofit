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
