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
- **THEN** it is shown as an earlier result without a new model call; visual results compare a fresh local capture digest before reuse, and no pixels are retained or transmitted on a cache hit

### Requirement: Informed automatic-search choice
Before reading or transmitting untracked page content, the extension SHALL ask once for explicit permission identifying OpenAI, the cleaned page address, page text and screenshot fallback. Declining SHALL retain reviewed-claim lookup. Automatic search settings SHALL allow withdrawal; accepted permission SHALL permit automatic lookup on subsequent popup openings without another click.

#### Scenario: First opening before permission
- **WHEN** the reader opens an untracked page without having enabled automatic search
- **THEN** no page content is read or sent, and the reader can allow automatic search or use reviewed claims only
