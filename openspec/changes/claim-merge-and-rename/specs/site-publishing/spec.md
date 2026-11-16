# Site publishing: moved addresses

## ADDED Requirements

### Requirement: Moved addresses lead to the claim
The export SHALL list each published address that no longer has a page of its own because its claim was merged into another or given a new slug, with the slug of the published claim it leads to. Such an address SHALL answer with a permanent redirect to that claim's page, and SHALL NOT be listed as archived. When the claim it leads to is archived, the address SHALL answer 410 like that claim's. When the claim it leads to is off the site for another reason (awaiting audit, or not approved), the address SHALL be listed nowhere and SHALL answer not found, as that claim's own address does, until the claim is published again. The reason for a merge or a rename SHALL NOT be exported. A moved address SHALL NOT appear in any feed, the sitemap, the lookup file or the data file.

#### Scenario: Merged claim's address
- **WHEN** a reader opens the address of a published claim that was merged into another published claim
- **THEN** the response is a permanent redirect to the kept claim's page

#### Scenario: Renamed claim's old address
- **WHEN** a reader opens the address a published claim had before its slug was made again
- **THEN** the response is a permanent redirect to the claim's page at its new address

#### Scenario: Kept claim awaiting audit
- **WHEN** the claim a moved address leads to is awaiting audit
- **THEN** the address is in neither list of the export and answers not found, like the claim's own address

#### Scenario: Kept claim taken down
- **WHEN** the claim a moved address leads to has been archived
- **THEN** the address answers 410
