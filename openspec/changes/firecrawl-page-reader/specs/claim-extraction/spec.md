# Spec Delta

## MODIFIED Requirements

### Requirement: Robots exclusion
The system SHALL NOT read an article whose address the page reader answers is not allowed, for whatever reason the reader gives. Whether a site's robots.txt is a reason is the reader's to decide. The reason SHALL be shown to the operator.

#### Scenario: Disallowed URL
- **WHEN** an operator requests extraction for a URL and the reader answers that it is not allowed because of the site's robots.txt
- **THEN** the article is not read, the operator is told why, and is asked to supply the text directly

#### Scenario: An address the reader refuses for another reason
- **WHEN** an operator requests extraction for an address the reader answers is not allowed, for a reason other than robots.txt
- **THEN** the operator is told the reader's reason and is asked to supply the text directly

### Requirement: Archived copies
The system SHALL NOT look for an archived snapshot itself. When the page reader says the copy it returned came from an archive, the system SHALL extract from it and record the archive address with the article. When the reader returns no page, the operator SHALL be asked to supply the text directly.

#### Scenario: Dead link with a snapshot
- **WHEN** the reader returns the page and says it came from an archived snapshot
- **THEN** extraction uses it and the article record carries the snapshot URL

#### Scenario: Dead link without a snapshot
- **WHEN** the reader answers that the site did not serve the page
- **THEN** the operator is asked to supply the text directly
