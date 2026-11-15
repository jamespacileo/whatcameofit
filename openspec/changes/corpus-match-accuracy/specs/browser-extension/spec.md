## ADDED Requirements

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
