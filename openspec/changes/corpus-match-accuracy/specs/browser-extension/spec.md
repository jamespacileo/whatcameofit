## ADDED Requirements

### Requirement: LinkedIn safety redirects retain the article
The shared address reader SHALL unwrap an HTTP(S) article URL carried by LinkedIn's `/safety/go/` redirect. The extension SHALL retain that article as an outgoing source link rather than discard it as a link within LinkedIn. The existing tracked-linked-article path SHALL remain available without a page read or model request. This SHALL NOT change post identity boundaries or condition equivalence rules.

#### Scenario: Current LinkedIn post wraps a tracked article
- **WHEN** an identity-bound post links to a tracked article through `https://www.linkedin.com/safety/go/?url=...`
- **THEN** request composition retains the decoded article URL and the service returns its published card through the linked-article path

#### Scenario: Redirect target is not HTTP or HTTPS
- **WHEN** the safety redirect carries an invalid or unsupported target scheme
- **THEN** no article target is recovered from that parameter

### Requirement: Current carousel slide stays within its post
Visual fallback for an identity-bound social carousel SHALL capture only its currently visible media within ancestor clipping boundaries. A hidden metadata image MAY establish carousel identity but SHALL NOT supply invisible pixels. Missing, conflicting or ambiguous slide identity SHALL fail closed. No automatic slide navigation or extra screenshot SHALL be required.

#### Scenario: Second slide names the medicine
- **WHEN** a carousel's first metadata image is clipped out and only its second slide is visible
- **THEN** capture uses the second slide inside the same bound carousel

#### Scenario: Another post is visible nearby
- **WHEN** recommendations contain larger images or a lone unrelated video
- **THEN** they cannot supply the screenshot boundary

#### Scenario: Carousel is moving
- **WHEN** two slides are visible and a unique current slide cannot be established
- **THEN** automatic capture declines instead of mixing slides

#### Scenario: Media is partially clipped
- **WHEN** an ancestor clips an eligible media element
- **THEN** the screenshot crop excludes pixels outside that ancestor

### Requirement: Signed-in post reading excludes account context
LinkedIn and Bluesky reading SHALL bind text, links and screenshot scope to the addressed post. Profile sidebars, analytics, replies and other posts SHALL not supply its reading. Missing or ambiguous post identity SHALL fail closed. Explicit selected text SHALL retain precedence.

#### Scenario: Public LinkedIn exposes distinct post and activity identities
- **GIVEN** a public LinkedIn article explicitly binds its activity URN and attributed post URN, one of which equals the requested URL, and its canonical and Open Graph URLs do not conflict
- **WHEN** the public article and its caption are visible and outside an accessibility-hidden overlay
- **THEN** only that article's own caption and links are read, excluding comments and nested posts
- **AND** only one visible, owned image matching the public preview image may supply screenshot scope

#### Scenario: Public LinkedIn identity is ambiguous or inaccessible
- **WHEN** public cards duplicate or conflict with the requested identity, disagree with the page metadata, or are accessibility-hidden
- **THEN** the reader returns no post text or screenshot scope, while retaining explicit selected-text precedence

#### Scenario: LinkedIn shows the reader's profile sidebar
- **WHEN** the requested post is displayed next to account details and comments
- **THEN** only the identity-bound post contributes text, links and media

#### Scenario: Bluesky shows a reply
- **WHEN** a thread contains the addressed post and a reply about another treatment
- **THEN** the reply does not contribute to the lookup

#### Scenario: Post has not finished loading
- **WHEN** the URL identifies a post but no matching post container exists
- **THEN** the reader does not fall back to the signed-in page or a stale post

### Requirement: Boundary corrections replace local answers
The extension SHALL reject local answers produced before the signed-in post-boundary correction. Independently verified public article answers MAY retain their existing shared-cache version because they contain no browser-derived account context.

#### Scenario: Reopening a previously broad post reading
- **WHEN** a version-five local result exists for a LinkedIn or Bluesky post
- **THEN** the corrected reader does not reuse it

### Requirement: Facebook detail reading uses the requested public post
Facebook detail reading SHALL require public metadata matching the current post identity. A unique visible caption matching that preview MAY supply full text and links; otherwise only the public preview MAY be read. Comments and neighbouring posts SHALL NOT supply text. Only unique visible media matching the preview image MAY authorize a screenshot. Missing or stale identity SHALL fail closed; video/reel aliases for one ID SHALL remain supported.

#### Scenario: A neighbouring post is longer
- **WHEN** a Facebook detail page includes a longer recent post and comments below the requested report
- **THEN** the requested caption is read without neighbouring posts or comments

#### Scenario: Facebook redirects video metadata to its reel
- **WHEN** the current video URL and public reel URL identify the same video ID
- **THEN** the public caption remains readable, without authorizing unrelated media

#### Scenario: Public preview is stale
- **WHEN** the public preview identifies a different post
- **THEN** neither its caption nor its media is used
