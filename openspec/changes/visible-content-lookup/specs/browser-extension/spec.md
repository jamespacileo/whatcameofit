## ADDED Requirements

### Requirement: Visible content fallback
Opening an untracked page with visible media and insufficient readable text SHALL automatically use one screenshot to identify the reported intervention and indication. Selected text SHALL suppress automatic capture. A video SHALL provide only its currently visible frame. The popup SHALL explain screenshot use and OpenAI processing.

#### Scenario: Claim embedded in Reddit image
- **WHEN** the caption lacks the claim but visible image text reports a treatment
- **THEN** the screenshot and caption are used without requiring Cloudflare to fetch Reddit, and any answer is labelled automatic and based on visible content

#### Scenario: Tab switches or popup closes
- **WHEN** the active tab changes or the popup closes during capture
- **THEN** no screenshot request is sent

### Requirement: Private bounded reuse
The extension SHALL reuse successful results for unchanged content for at most 24h, keep at most ten, show their checked-at time, and provide Search again to bypass them. It SHALL NOT retain screenshot pixels or submitted text. Clear recent SHALL clear the result cache.

#### Scenario: Opening a previously checked report
- **WHEN** a fresh result matches the current page and content fingerprint
- **THEN** it is shown as an earlier result without a new capture or model call
