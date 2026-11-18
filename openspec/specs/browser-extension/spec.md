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

### Requirement: Public privacy disclosure
The site SHALL publish a linked `/privacy` page explaining local address matching, cached public data, hosting, contact messages and the automatic registry search on opening the popup. The disclosure SHALL identify OpenAI and possible provider retention before automatic search is enabled.

#### Scenario: Reader checks extension privacy
- **WHEN** the reader opens the public privacy address
- **THEN** the page explains what opening the popup sends, what stays in the browser, and how to contact the operator

### Requirement: Status of the current article
When the reader activates the extension on a page whose address is a source article of a published claim, the extension SHALL show the claim's headline, its status in the site's wording, the no-signal note when present, the first-reported date, the latest dated promise when present, and a control that opens the claim page.

#### Scenario: Tracked article
- **WHEN** the reader activates the extension on a tracked article
- **THEN** the claim's status is shown with a control that opens its page on the site

#### Scenario: Article reporting two claims
- **WHEN** the article is a source of two published claims
- **THEN** both claims are shown, each with its own status and control

### Requirement: Untracked pages
On a page that is not a source article of a published claim, the extension SHALL say that the page is not a tracked report, SHALL NOT suggest anything about the story's truth, and SHALL offer the site's search.

#### Scenario: Untracked article
- **WHEN** the reader activates the extension on an article no claim cites
- **THEN** the extension says the page is not a tracked report and links to the site's search

#### Scenario: Not a web page
- **WHEN** the current tab is not an http or https page
- **THEN** the extension asks the reader to open an article first

### Requirement: The site's own pages (added 2026-11-13)
On a page of the site itself the extension SHALL NOT read the page or start a registry search. On a published claim's page it SHALL show that claim as it does for a tracked article, and SHALL NOT add the page to the reader's list of checked pages. On any other page of the site it SHALL ask the reader to open an article first.

#### Scenario: Claim page on the site
- **WHEN** the reader activates the extension on a published claim's page on the site
- **THEN** the extension shows that claim's status from the lookup file, and nothing is sent

#### Scenario: Another page on the site
- **WHEN** the reader activates the extension on the site's home, method or privacy page
- **THEN** the extension asks the reader to open an article first, and nothing is sent

### Requirement: The page address stays in the browser
The extension SHALL decide whether a page is tracked by comparing its address with the lookup file inside the browser. It SHALL NOT send the current page's address to any server. It SHALL read the current tab only when the reader opens the popup, and SHALL NOT monitor or read pages while the popup is closed. It SHALL retain the existing activeTab, scripting and storage permission scope.

#### Scenario: Reviewed match
- **WHEN** the reader activates the extension on a tracked report
- **THEN** its reviewed claim is shown and no page-text or model request is made

### Requirement: Automatic registry search on opening the popup (updated 2026-11-12)
For an untracked page, and only where the site's lookup file enables registry searches, the extension SHALL start one lookup when the popup opens without a second search click. It SHALL show a loading state with visible OpenAI processing and retention disclosure and a privacy link. It SHALL NOT look up every visited page or add background browsing permissions. A non-web tab, a tracked report and a disabled lookup service SHALL start no model request.

The extension SHALL read the page inside the browser and send the lookup service the text read, the addresses that text links to (thirty at most, none on the page's own site), and, for a post, the platform's name. It SHALL NOT send the page's address. For a post it SHALL send the post's own words and leave out lines that are only links within the platform, including the writer's name and handle, time and counts. It SHALL recognise semantic article elements and elements with the article role, and unwrap known outgoing article links before filtering platform navigation. For another page it SHALL use the site's article reader. Selected text SHALL replace the page's words. Too little readable text SHALL produce a clear refusal without sending a search request. A navigation during reading SHALL produce a page-changed refusal.

Repeated actions while a lookup is running SHALL share that lookup. Closing the popup SHALL cancel pending fetches and suppress late rendering. Failures SHALL offer an explicit retry and SHALL NOT trigger automatic paid retries. The answer SHALL retain the automatic, unchecked marking and the OpenAI disclosure.

#### Scenario: Fresh article opens
- **WHEN** an enabled extension popup opens on an untracked article
- **THEN** a loading state appears and one search starts without a second click

#### Scenario: Popup closes during a lookup
- **WHEN** the popup closes while reading or fetching
- **THEN** its pending fetch is cancelled, no later fetch is started, and late results are ignored

#### Scenario: Concurrent actions
- **WHEN** multiple opening or retry actions occur during one lookup
- **THEN** they share the in-flight request

#### Scenario: Wrapped outgoing article
- **WHEN** a Facebook or Reddit post wraps an external article address on its own host
- **THEN** the outgoing address and the card's headline are retained while profile links are filtered

#### Scenario: Hacker News story or comment
- **WHEN** the popup opens on a Hacker News item
- **THEN** only the requested story row or comment body is read, and a missing item does not cause unrelated discussion to be read

A post on X links out only through X's own shortener, which does not let the site's server follow its links. For such a link, three at most per search, the extension SHALL ask the shortener for its page, without cookies and without a referrer, read from it the address the link leads to, and send that address in the link's place. It SHALL NOT go on to the article itself, and SHALL hold permission for that shortener's host and the site's own, and no other. A link it cannot resolve SHALL be sent as it was.

#### Scenario: Post on X that links through its shortener
- **WHEN** the reader asks for a search on a post whose link goes through X's shortener
- **THEN** the browser opens that link, the address it leads to is sent in its place, and the article itself is not fetched by the extension

#### Scenario: Post on a platform the site cannot read
- **WHEN** the reader asks for a search on a post whose platform does not offer posts to software
- **THEN** the post's words and its links are sent with the platform's name, and neither the writer's name nor the page's address is

#### Scenario: Text the reader selected
- **WHEN** the reader has selected text on the page and asks for a search
- **THEN** only the selected text is sent of the page's words

#### Scenario: Too little to read
- **WHEN** fewer than forty characters can be read and there is no useful outgoing article or shortened link from a post
- **THEN** nothing is sent and the reader is asked to select the text

#### Scenario: Short or link-only post
- **WHEN** a post has fewer than forty characters, including no body text, and links to an article
- **THEN** its actual text and outgoing link are sent without invented post text so the service can read the linked article

### Requirement: Each potential match is one visual item
Every displayed registry candidate SHALL occupy its own visual card, grouping the title and source link, phase, state, registry identifier, reasons for the match and match-confidence label. Confidence SHALL be taken from the shared answer's model score. Missing confidence SHALL be shown as unavailable. The explanation SHALL describe confidence as an estimate of the match to the report. It SHALL NOT imply treatment effectiveness or trial quality. Cards SHALL remain identifiable without colour. Reviewed-claim links SHALL use the same grouped presentation with reviewed provenance and no invented confidence score.

#### Scenario: Multiple candidate records
- **WHEN** a lookup returns multiple displayed candidates
- **THEN** each has a separate card containing its own confidence and registry details

#### Scenario: Missing score
- **WHEN** an older or incomplete answer contains a candidate without confidence
- **THEN** its card says confidence is unavailable and still shows its source details

### Requirement: Works from its saved copy
The extension SHALL keep a copy of the lookup file and reuse it for up to six hours. When the site cannot be reached it SHALL use the saved copy and say when that copy was saved; with no saved copy it SHALL say the site could not be reached.

#### Scenario: Site unreachable with a saved copy
- **WHEN** the lookup file cannot be fetched and a copy was saved earlier
- **THEN** the status is shown from the saved copy with the date it was saved

### Requirement: Notices and wording
Every view that shows a status SHALL carry the site's medical-advice and trial notices and the date the registries were last checked. All status wording SHALL come from the lookup file.

#### Scenario: Tracked article
- **WHEN** a status is shown
- **THEN** both notices and the last-checked date are visible in the same view

### Requirement: Popup checks the current published card index
Each web-page popup SHALL revalidate the published index before source matching or clinical-answer reuse. Conditional requests SHALL avoid an unchanged body. Failure SHALL retain the dated offline fallback and five-second bound. This static request SHALL send no source-page URL, text or image. Clinical-answer lifetimes and background refresh frequency SHALL remain unchanged.

#### Scenario: A card was published after the previous popup
- **GIVEN** a recent saved index lacks the page's exact-source card and an earlier clinical answer exists
- **WHEN** the server supplies the updated index
- **THEN** the popup displays the exact-source card without reading the page or requesting a clinical search
- **AND** a recent saved index does not suppress the check within its former six-hour lifetime

#### Scenario: Published index has not changed
- **WHEN** the server answers the saved ETag with 304
- **THEN** the popup reuses the saved index without parsing a response body and retains normal clinical-answer reuse

#### Scenario: A published mapping has been removed
- **WHEN** a fresh index no longer contains the saved index's exact-source card
- **THEN** the old source card is not shown as current

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

### Requirement: Addressed social post boundary
Instagram, Threads, Telegram and TikTok detail-page reading SHALL bind collected words and any screenshot scope to the requested post identity. Replies, login forms, neighbouring messages and recommended videos SHALL NOT supply the claim. Missing or stale identity metadata SHALL fail closed. Explicit selected text SHALL retain precedence.

#### Scenario: TikTok recommends a longer unrelated video
- **WHEN** a requested video has a short caption beside a longer recommendation
- **THEN** the reader uses the requested video's bound caption and media scope, including its matching public caption metadata when playback fails

#### Scenario: Telegram opens a channel around the linked message
- **WHEN** the channel page contains several messages
- **THEN** only the message matching the channel and numeric message ID contributes text, links or pixels

#### Scenario: Instagram or Threads metadata belongs to another post
- **WHEN** public metadata is missing or names a different post identity
- **THEN** the reader returns no automatic post reading rather than falling back to surrounding page text

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
