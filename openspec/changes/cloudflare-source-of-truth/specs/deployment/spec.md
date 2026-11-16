# Spec Delta

## MODIFIED Requirements

### Requirement: CI publishes only the staged public snapshot
GitHub SHALL build from a normal export taken from the truth store at the start of the deployment, validated before any build. It SHALL NOT substitute seed or preview data, and SHALL NOT read the store in any other way during the build. Taking the export SHALL NOT approve any review decision and SHALL NOT change the store. The topic slugs published SHALL be added to the committed publication history without removing previous slugs.

#### Scenario: Invalid publication input
- **WHEN** the export taken is malformed, preview, empty, or contains an unchecked claim that the rules do not publish
- **THEN** the deployment stops before building and the site stays as it was

#### Scenario: Topic publication history
- **WHEN** an export is taken for a deployment
- **THEN** its topic slugs are added to the committed publication history without removing previous slugs
- **AND** the already published dental-regeneration address redirects to mouth-and-teeth

#### Scenario: The store cannot be reached
- **WHEN** the export cannot be taken
- **THEN** the deployment stops, says so, and publishes nothing

#### Scenario: A claim held for audit
- **WHEN** the store holds claims awaiting audit
- **THEN** the export leaves them out and the deployment's log says how many were held

## ADDED Requirements

### Requirement: A deployment follows a release from audit
A deployment SHALL be started when claims are released from audit and on a schedule. Two deployments SHALL NOT run at once; a later one SHALL take its own export.

#### Scenario: Claims are cleared
- **WHEN** the operator clears a batch of claims from audit
- **THEN** a deployment is started without a commit being made

### Requirement: What was deployed can be told afterwards
Each deployment SHALL record a checksum of the export it built from, the time the export was taken and the counts of claims and events in it.

#### Scenario: Asking what is live
- **WHEN** the operator asks what the live site was built from
- **THEN** the deployment's record gives the export's checksum, time and counts
