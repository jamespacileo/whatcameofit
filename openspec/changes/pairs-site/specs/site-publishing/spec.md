# Spec Delta

## MODIFIED Requirements

### Requirement: Build from the export alone
The site SHALL be built from one bundle of page files only, with no access to a database or to external services. A page rendered on request SHALL read only that bundle's files.

#### Scenario: Offline build
- **WHEN** the site is built on a machine that has the bundle and no network or database
- **THEN** the build succeeds

#### Scenario: A page rendered on request
- **WHEN** the Worker renders a pair page
- **THEN** it reads that pair's file from the deployment's bundle version and nothing else

## REMOVED Requirements

### Requirement: Claim page
**Reason**: The operator dropped claims on 2026-11-19; a pair page replaces the claim page (`pair-pages`).
**Migration**: A claim's address redirects to its pair's address. Headlines, summaries and promises return with the lab's reports.
