# Spec Delta

## MODIFIED Requirements

### Requirement: Robots exclusion
The system SHALL NOT read an article whose address the page reader answers is not allowed, whether because the site's robots.txt disallows it for the project's client or for any other reason the reader gives. The reason SHALL be shown to the operator.

#### Scenario: Disallowed URL
- **WHEN** an operator requests extraction for a URL that the site's robots.txt disallows
- **THEN** the page is not fetched, the operator is told why, and is asked to supply the text directly

#### Scenario: A platform that is not read
- **WHEN** an operator requests extraction for an address on a platform the reader does not allow
- **THEN** nothing is fetched, the operator is told the reader's reason, and is asked to supply the text directly

### Requirement: Archived copies
The system SHALL NOT look for an archived snapshot itself. When the page reader says the copy it returned came from an archive, the system SHALL extract from it and record the archive address with the article. When the reader returns no page, the operator SHALL be asked to supply the text directly.

#### Scenario: Dead link with a snapshot
- **WHEN** the reader returns the page and says it came from an archived snapshot
- **THEN** extraction uses it and the article record carries the snapshot URL

#### Scenario: Dead link without a snapshot
- **WHEN** the reader answers that the site did not serve the page
- **THEN** the operator is asked to supply the text directly
