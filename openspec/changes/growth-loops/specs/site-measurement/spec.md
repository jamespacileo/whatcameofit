# Spec Delta

## ADDED Requirements

### Requirement: The site counts for itself
Page views and downloads SHALL be counted by the site's own service as it answers a request, with no script in the page and no other party. A request from a declared crawler or link-preview fetcher SHALL NOT be counted. A failure to count SHALL NOT change or delay the response.

#### Scenario: Reader opens a claim page from a search result
- **WHEN** a reader's browser requests a claim page having followed a link from a search engine
- **THEN** the count for that page, that day and that referring site rises by one, and the page carries no measuring script

#### Scenario: Crawler fetches a page
- **WHEN** a search engine's crawler requests a page
- **THEN** no count is added

#### Scenario: Card image downloaded
- **WHEN** a reader downloads a claim's square card
- **THEN** the count of downloads for that card and day rises by one

### Requirement: A referring site is counted by its name only
The referring site SHALL be recorded as its host name alone. The referring page's path and query SHALL NOT be stored. A request with no referring site SHALL be counted as direct.

#### Scenario: Visit from a post on a network
- **WHEN** a reader arrives from a post whose address holds the post's identifier
- **THEN** the count names the network's host and nothing of the post's address

### Requirement: Counts are deleted after four hundred days
A page or download count SHALL be deleted once its day is more than four hundred days past.

#### Scenario: Old count
- **WHEN** a count's day is four hundred and one days ago
- **THEN** the next daily clean-up deletes it
