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
