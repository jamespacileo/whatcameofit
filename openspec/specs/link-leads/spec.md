# link-leads Specification

## Purpose
Records the addresses of articles that people shared on social platforms, loaded from bulk files, as unreviewed leads kept apart from article leads, source articles, claims and evidence.

## Requirements

### Requirement: Link lead record
A link lead SHALL be kept once per article address. It SHALL store the address, the outlet's domain, the outlet kind, the title the article was first shared under, and each share of it: the platform, the community, the time shared and the score. A share SHALL be stored once.

#### Scenario: One article shared in two places
- **WHEN** the same article address is shared on Hacker News and in a Reddit community
- **THEN** one link lead exists with two shares

#### Scenario: The same file loaded twice
- **WHEN** a file that has already been loaded is loaded again
- **THEN** no lead and no share is added

### Requirement: Addresses are compared as the site compares them
Two addresses SHALL be the same link lead when the site's address comparison treats them as the same article: differences of letter case in the host, a leading `www.`, a trailing slash, a fragment and tracking parameters SHALL NOT make a second lead.

#### Scenario: A tracking parameter
- **WHEN** one share gives an article's address and another gives it with a `utm_source` parameter
- **THEN** both shares belong to one link lead

#### Scenario: An address that cannot be an article
- **WHEN** a shared link is not an `http` or `https` address, or has no host
- **THEN** no lead is made for it and the load counts it as unusable

### Requirement: Loading from a file
`thenwhat backfill load-links` SHALL read one bulk file of one platform from the operator's disk and store its link leads. It SHALL send no request to any platform or outlet. It SHALL finish by reporting how many posts were read, how many gave a new lead, how many added a share to an existing lead, and how many were skipped for each reason.

#### Scenario: A file of stories
- **WHEN** the operator loads a file of 10,000 Hacker News stories of which 7,000 link to an address
- **THEN** leads and shares are stored for those 7,000, the report gives the counts, and no request is sent

#### Scenario: Stopped part way
- **WHEN** a load is stopped and started again on the same file
- **THEN** every post in the file is stored once

#### Scenario: A staged GDELT article listing
- **WHEN** the operator loads a GDELT Global Article List JSONL file containing a source, URL, headline and UTC date per row
- **THEN** each valid row becomes an unreviewed link lead with a GDELT share dated to that UTC day, malformed rows are counted, and a repeated load adds no duplicate lead or share
- **AND** the publication date of a source article still comes from the publisher's page during reading

#### Scenario: A platform with no reader
- **WHEN** the operator names a platform the pipeline has no reader for
- **THEN** the command fails, lists the platforms it can read, and stores nothing

### Requirement: Only posts that link to an address
A post with no outside link, a post whose link leads to the platform itself, and a post the file marks as deleted or removed SHALL be skipped and counted.

#### Scenario: A text post
- **WHEN** a post has text and no link
- **THEN** it makes no lead and is counted as having no link

#### Scenario: A removed post
- **WHEN** the file marks a post as removed
- **THEN** it makes no lead and no share, and is counted as removed

### Requirement: Chosen communities
For a platform divided into communities, only posts from the communities named in the configuration SHALL be loaded. The load SHALL refuse to start while none is named.

#### Scenario: A post from another community
- **WHEN** a Reddit file holds a post from a community that is not configured
- **THEN** the post is skipped and counted as out of the chosen communities

#### Scenario: No community configured
- **WHEN** the operator loads a Reddit file and no community is configured
- **THEN** the command fails, names the missing setting and stores nothing

### Requirement: Nothing about the person who shared
A link lead and its shares SHALL NOT hold who shared the link, the post's text, its comments, or for Reddit the post's id or address. These SHALL NOT be written to the database, a log or a fixture. The Hacker News item number SHALL be kept with its share.

#### Scenario: A Reddit submission
- **WHEN** a Reddit submission is loaded
- **THEN** what is stored is the article's address, the community, the time, the score and the title, and nothing else from the submission

### Requirement: Link leads are not published
A link lead SHALL NOT be a source article or an article lead, SHALL NOT by itself create or change a claim, a match, an evidence event or a status, and SHALL NOT appear in the export or on the site. The export SHALL NOT say on which platform an article was shared.

#### Scenario: Export after a load
- **WHEN** link leads are loaded and the export is produced
- **THEN** the export is identical to the one produced before the load
