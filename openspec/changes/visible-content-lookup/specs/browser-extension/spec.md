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

### Requirement: Bounded popup lookup
Each lookup attempt SHALL leave its loading state within 45 seconds, including page reading, service response consumption and automatic screenshot fallback. Index requests and optional shared-cache probes SHALL have shorter deadlines. A timed-out attempt SHALL be cancelled and described as an incomplete search with an explicit retry, never as no matching research.

#### Scenario: A service request never completes
- **WHEN** the lookup deadline expires before the answer arrives
- **THEN** the popup leaves its loading state, aborts the request and offers Search again

#### Scenario: A late answer arrives after timeout
- **WHEN** an expired operation completes after the timeout or after a new attempt begins
- **THEN** it does not change the display or cache, and the new attempt uses a fresh cancellation signal

#### Scenario: Popup closes during a stalled operation
- **WHEN** the reader closes the popup before its deadline
- **THEN** active work is cancelled without rendering a timeout or sending further requests


### Requirement: Fast completed result reuse
The extension SHALL overlap eligible shared-cache probing with page collection, save complete eligible shared hits locally, and reuse completed non-treatment identifications for unchanged content. Consent, selection, private-window and navigation safeguards SHALL apply before content or context transmission. Provisional outcomes, errors, unchecked papers and incomplete streams SHALL NOT be cached.

#### Scenario: Reopening a completed non-treatment article
- **WHEN** an unchanged readable article previously completed a non-treatment lookup
- **THEN** its dated result is reused without a model request or automatic screenshot

#### Scenario: Ordinary article with a decorative image
- **WHEN** substantial structured article text is readable and no media-only or image-claim indicators require visual reading
- **THEN** a negative text identification completes without automatic screenshot reading and Screenshot remains available

#### Scenario: Claim still exists only in media
- **WHEN** a short or media-dependent report lacks a treatment in readable text
- **THEN** automatic visual fallback still runs and the provisional text answer is not retained

### Requirement: Progressive completed trial result
The extension SHALL display a completed clinical result before optional research enrichment finishes, indicate that additional research is loading, and update that section on completion without starting another paid lookup. It SHALL retain an already completed core answer when only enrichment or the response tail fails, label the incomplete enrichment, and not cache an incomplete stream.

#### Scenario: Enrichment is slow
- **WHEN** the service supplies a completed core result while related papers are pending
- **THEN** the reader sees the core result immediately with additional-research loading text, rather than a blocking spinner

#### Scenario: Popup closes between events
- **WHEN** the popup closes or navigates after a core event
- **THEN** later events cannot render, save or send content
