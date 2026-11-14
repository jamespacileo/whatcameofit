# browser-extension Specification

## Purpose
What the browser extension tells a reader about the page they have open: the tracked claim when there is one, or a registry search they ask for, with its confidence and limits stated.

## Requirements

### Requirement: Safari startup without optional notifications
The extension SHALL start and refresh its lookup index when the browser does not provide notifications. It SHALL NOT mark undelivered notifications as sent or discard saved reminders. It SHALL offer extension reminder choices only when notifications are supported; following and recent checks SHALL remain available.

#### Scenario: Safari lacks the notifications API
- **WHEN** Safari loads the extension's background script
- **THEN** startup succeeds, the lookup refresh can run, and unsupported notification controls are omitted

### Requirement: Current YouTube video lookup
Opening the extension on a YouTube watch page or Short SHALL read only the current video's title, loaded description, source links and any loaded captions/transcript. It SHALL exclude comments, recommendations and inactive videos. A missing or stale video renderer SHALL NOT fall back to the surrounding page. Explicit selected text SHALL retain precedence and suppress links and automatic screenshot capture.

#### Scenario: Video describes a medical claim
- **WHEN** the current video's title or loaded description identifies a reported intervention and indication
- **THEN** automatic lookup sends those words with platform YouTube and eligible description links through the existing lookup path

#### Scenario: Short navigation is still loading
- **WHEN** the address identifies a different video from the available active renderer
- **THEN** no previous video's content or unrelated page content is used

### Requirement: Video-frame fallback
YouTube screenshot fallback SHALL capture only the current visible video frame using existing size, consent, private-window, sensitive-field, navigation and spending controls. It SHALL NOT capture advertisements, unrelated thumbnails or the whole page when no eligible player is visible. It SHALL NOT record audio, download video or request transcripts from an API.

#### Scenario: Text misses a visible claim
- **WHEN** the existing fallback criteria are met and the current video is visible
- **THEN** one bounded frame can be sent, with any result labelled automatic under the existing result presentation

### Requirement: Stable video identity and private reuse
Valid watch, share, Shorts and live links for one video SHALL share an address key. Source URLs SHALL retain the video ID but omit playback position, playlist context and sharing tokens; unknown query parameters SHALL make the source URL ineligible. Text-answer fingerprints SHALL NOT change solely because playback time or the temporary media URL changes. Visual answers SHALL still compare a fresh local capture digest. Browser-derived YouTube answers SHALL NOT enter the shared public cache.

#### Scenario: Timestamped share link
- **WHEN** a reader opens a timestamped share link for a previously tracked video
- **THEN** the local address check recognises the same video without exposing the timestamp or sharing token in its source URL

### Requirement: Saved checks preserve search limitations
A recently checked entry with no trial candidate SHALL preserve the generated answer's distinction between a registry search with no matching record and content from which a treatment could not be identified. Older entries without that distinction SHALL use neutral wording about no saved trial match. The additional limitation SHALL remain in browser-local storage alongside the existing answer; no article text or screenshot SHALL be retained for this purpose.

#### Scenario: Registry not searched
- **WHEN** a check could not identify a treatment and condition
- **THEN** its recent entry says that the registry was not searched, without claiming no record was found

#### Scenario: Registry searched without a match
- **WHEN** a check searched the registry but found no matching trial record
- **THEN** its recent entry preserves that outcome and the limitation that other records may exist

#### Scenario: Older entry
- **WHEN** an existing entry has no saved limitation
- **THEN** it says no trial match is saved and offers to open the original page

### Requirement: A wait is marked by the mark, and never delays the answer
While the popup checks a page, searches the registry or reads an image, it SHALL show one line: the mark, then what is being waited for. For a reader who has not asked for reduced motion the capsule SHALL pass beneath the glass for as long as the wait lasts; with reduced motion the mark SHALL be still. The answer SHALL replace the line as soon as it is ready and SHALL NOT wait for the motion.

#### Scenario: Checking a page
- **WHEN** the popup is opened and the page is being checked
- **THEN** the view is one line holding the mark and "Checking this page…"

### Requirement: The tick is drawn for a claim just followed
When a reader presses "Keep me up to date", the line that replaces the control SHALL show a tick that is drawn, for a reader who has not asked for reduced motion. When the popup is opened on a claim already followed, the tick SHALL be shown without motion.

#### Scenario: Just followed
- **WHEN** a reader presses "Keep me up to date" on a tracked claim
- **THEN** the line reads "You follow this claim." and its tick is marked to be drawn

#### Scenario: Already followed
- **WHEN** the popup is opened on a claim the reader follows
- **THEN** the tick is not marked to be drawn

### Requirement: Candidate-first results
An automatic answer SHALL show its automatic/unreviewed provenance, identified treatment and indication when available, and individual candidate cards before lengthy explanations. Each card SHALL retain its complete linked title, model match confidence, phase and registry state. Missing confidence SHALL remain unavailable; reviewed claims SHALL have no invented score. Icons and colour SHALL support visible labels and SHALL NOT imply treatment effectiveness.

#### Scenario: Image post produces candidates
- **WHEN** a lookup returns one or more candidates
- **THEN** the first card is visible in a 360 by 600 pixel popup using representative long titles, without first expanding or scrolling past explanatory paragraphs

### Requirement: Accessible supporting detail
Source provenance, registry identifiers, match explanations, confidence limitations, OpenAI processing and retention details SHALL remain available through labelled keyboard-operable disclosures. Automatic/unreviewed provenance, cached-result date, lack-of-evidence uncertainty and a short medical limitation SHALL remain visible. The explicit first-use permission screen SHALL continue to identify the recipients and shared content before consent.

#### Scenario: Reader checks a candidate
- **WHEN** the reader opens that card's details
- **THEN** its registry identifier, reason when supplied, and model-confidence limitation are available without leaving the result

#### Scenario: Reader checks sources or privacy
- **WHEN** the reader opens Sources and privacy
- **THEN** full source context, additional search details, OpenAI disclosure and the privacy link are available

#### Scenario: Reused answer or unsuccessful identification
- **WHEN** an earlier answer is reused or no treatment or candidate can be identified
- **THEN** the checked date or uncertainty remains visible without expanding details, and retry remains available

### Requirement: Stable initial popup size
The desktop extension SHALL report a 360px content width independently of the host's provisional viewport width, so its host can size the popup to display the content. The compact results and existing lookup behaviour SHALL remain unchanged.

#### Scenario: Narrow provisional viewport
- **WHEN** the host initially lays out the popup at 100px before measuring its content
- **THEN** the content measures 360px and remains 360px when the host expands to fit it

#### Scenario: Native Safari reopening
- **WHEN** the reader repeatedly closes and opens the extension on a reviewed article and an untracked public post
- **THEN** the popup shows its readable content at normal width, including after expanding and collapsing details
