# Spec Delta

## Purpose

Shows, for a news article open in the browser, the tracked claim it reports and where that claim stands.

## ADDED Requirements

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
- **WHEN** fewer than forty characters can be read from the page
- **THEN** nothing is sent and the reader is asked to select the text

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
