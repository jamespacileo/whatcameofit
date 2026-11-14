# browser-extension Specification

## Purpose
TBD - created by archiving change youtube-lookup. Update Purpose after archive.

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
