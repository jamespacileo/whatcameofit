# Spec Delta

## ADDED Requirements

### Requirement: Only a reviewed export is deployed
The deploy command SHALL refuse to publish when the export is a preview, when it holds no claims, or when any claim in it has not been checked by a person. It SHALL name the claims that are not checked. It SHALL write its own normal export from the pipeline before checking, so that a local preview setting does not decide what is published.

#### Scenario: Reviewed export and a public address
- **WHEN** every claim in a non-preview export is checked by a person and the address is a public HTTPS address
- **THEN** no reason to stop is reported

#### Scenario: Preview export
- **WHEN** the export is a preview
- **THEN** the command stops, says that a preview is never deployed, and publishes nothing

#### Scenario: Claim not checked by a person
- **WHEN** one claim in the export was loaded from a seed file and never approved by the operator
- **THEN** the command stops and names that claim

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
