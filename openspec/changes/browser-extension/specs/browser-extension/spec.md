# Spec Delta

## Purpose

Shows, for a news article open in the browser, the tracked claim it reports and where that claim stands.

## ADDED Requirements

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
The extension SHALL decide whether a page is tracked by comparing its address with the lookup file inside the browser. It SHALL NOT send the address of any page to any server, and SHALL read the current tab only when the reader activates it. Unless the reader asks for a registry search of the page (below), it SHALL NOT send the title or content of any page either.

#### Scenario: Lookup
- **WHEN** the reader activates the extension
- **THEN** the only network request it may make is for the site's lookup file

### Requirement: A registry search of the open page, when the reader asks (decided 2026-11-12)
For a page that is not tracked, and only where the site's lookup file says the site answers registry searches, the extension SHALL offer a search of the open page, with words beside the button that say what is read and sent. Nothing SHALL be read from the page until the reader presses it. The extension SHALL then read the page inside the browser and send the site's lookup service the text read, the addresses that text links to (thirty at most, none on the page's own site), and, for a post, the platform's name. It SHALL NOT send the page's address. For a post it SHALL send the post's own words and leave out the lines that are only links within the platform: the writer's name and handle, the time, the counts. For any other page it SHALL read the page as the site reads an article. When the reader has selected text on the page, only that text SHALL be sent of the page's words. When too little can be read, the extension SHALL say so and send nothing. The answer SHALL be shown in the site's own wording, marked first as an automatic search.

#### Scenario: Post on a platform the site cannot read
- **WHEN** the reader asks for a search on a post whose platform does not offer posts to software
- **THEN** the post's words and its links are sent with the platform's name, and neither the writer's name nor the page's address is

#### Scenario: Text the reader selected
- **WHEN** the reader has selected text on the page and asks for a search
- **THEN** only the selected text is sent of the page's words

#### Scenario: Too little to read
- **WHEN** fewer than forty characters can be read from the page
- **THEN** nothing is sent and the reader is asked to select the text

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
