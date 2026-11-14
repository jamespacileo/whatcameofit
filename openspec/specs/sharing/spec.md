# sharing Specification

## Purpose
What a reader can take away from a claim page and what another site can show of it: the link-preview card in its shapes, a sentence to copy, and an embed. Everything shared states records and never a verdict.

## Requirements

### Requirement: The card sets the headline beside the status
Each published claim's link-preview card SHALL show the title of the claim's earliest source article as the outlet wrote it, in quotation marks with the outlet named, and beside it the claim's current status in the site's wording. It SHALL show the year the claim was first reported and the month and year the registries were last checked. It SHALL NOT show a count of days or years elapsed, a grade, a tick, a cross, or any word that judges the claim, the outlet or the people behind it. When a no-signal note applies it SHALL be shown in the site's wording. A claim with no source article SHALL show the claim's own headline without quotation marks.

#### Scenario: Headline says more than the status
- **WHEN** a claim's earliest article is titled as a cure and the claim's status is a Phase 1 trial
- **THEN** the card shows the title in quotation marks with the outlet's name, and the status "Phase 1 trial", and adds no wording of its own about the difference

#### Scenario: Card seen a year later
- **WHEN** a card built in one year is viewed in a later year without being rebuilt
- **THEN** every statement on it is still true as dated, because it gives the year first reported and the month the registries were checked, not an elapsed time

#### Scenario: Claim with no article
- **WHEN** a published claim has no source article
- **THEN** its card shows the claim's headline without quotation marks and names no outlet

### Requirement: The card says it is not advice
Every card SHALL carry the words "Not medical advice" and the site's name. A card for a claim whose status is a registered or started trial SHALL NOT use any word that suggests the treatment is available.

#### Scenario: Any card
- **WHEN** any claim's card is built
- **THEN** the image contains "Not medical advice" and the site's name

### Requirement: The card comes in three shapes
The site SHALL build each published claim's card as a wide image of 1200 by 630 pixels, a square image of 1080 by 1080 pixels and a tall image of 1080 by 1920 pixels. All three SHALL state the same facts. The wide image SHALL be the page's link preview. The claim page SHALL offer the square and tall images as downloads, each with a text alternative built from the same facts.

#### Scenario: Three shapes, one set of facts
- **WHEN** a claim's three card images are built
- **THEN** each shows the same headline, outlet, status, first-reported year and checked month, and none is cut off at any edge

#### Scenario: Long headline
- **WHEN** an article's title is 150 characters long
- **THEN** all three shapes show it in full or end it with an ellipsis at a word boundary, and the status remains fully visible

### Requirement: A sentence to copy
The claim page SHALL offer one sentence that a reader can copy, stating when the claim was first reported, its current status in the site's wording, the month the registries were last checked, and the page's address. The sentence SHALL contain no verdict wording and no medical advice. Copying SHALL work from the keyboard, and the page SHALL say when the sentence has been copied.

#### Scenario: Reader copies the sentence
- **WHEN** a reader activates the copy control on a claim first reported in March 2021 whose status is a Phase 1 trial
- **THEN** the clipboard holds a sentence naming March 2021, "Phase 1 trial", the checked month and the page's address, and the page confirms the copy

#### Scenario: Copying is not possible
- **WHEN** the browser refuses access to the clipboard
- **THEN** the sentence is shown as selectable text and nothing claims it was copied

### Requirement: A claim can be embedded
Each published claim SHALL have an embed page, made to be shown inside another site's frame, that shows the claim's headline, its status, the no-signal note when present, the month the registries were last checked, the "not medical advice" line, and a link to the full claim page that opens outside the frame. The embed page SHALL request nothing from any other host, set no cookie, and run no script that reports to anyone. The claim page SHALL give the snippet that embeds it. An embed page SHALL NOT be listed in the sitemap and SHALL ask search engines not to index it.

#### Scenario: Another site embeds a claim
- **WHEN** another site places the snippet from a claim page in its own page
- **THEN** its readers see the claim's status and a link that opens the full claim page in the whole window

#### Scenario: Status changes after embedding
- **WHEN** a claim's status changes and the site is rebuilt
- **THEN** every embed of that claim shows the new status without the embedding site changing anything

#### Scenario: Embed page and privacy
- **WHEN** an embed page loads inside another site
- **THEN** it asks no other host for anything and stores nothing in the reader's browser

### Requirement: A promise on the card is marked as a promise
When a claim has a dated promise, the card SHALL show the year promised by on the site's pale amber with a dashed rule, in all three shapes. No other part of the card SHALL use that colour. A claim with no dated promise SHALL have a card with no amber on it.

#### Scenario: Claim with a dated promise
- **WHEN** a claim's latest promise names 2025
- **THEN** each shape of its card shows "Promised by 2025" on pale amber, and the status in the site's blue

#### Scenario: Claim with no dated promise
- **WHEN** a claim has no promise with a date
- **THEN** its card shows no "Promised by" fact and no amber

### Requirement: The claim page shows the card it offers
The claim page SHALL show the square card beside the sentence to copy, with a text alternative built from the same facts as the card.

#### Scenario: Reader looks before sharing
- **WHEN** a reader reaches "Pass it on" on a claim page
- **THEN** the square card is visible beside the sentence, and a screen reader is given the card's facts as text

### Requirement: A claim can be posted to a network
The claim page SHALL offer links that open a prefilled post on Bluesky, Mastodon, Threads, X, LinkedIn, Reddit, WhatsApp and Telegram, a prefilled email, and a control that copies the page's address. The prefilled text SHALL be the claim's share sentence and the page's address, and nothing else. Every link except Mastodon's SHALL work with no script. The Mastodon link SHALL ask for the reader's server, SHALL remember it only in the reader's own browser, and SHALL send nothing to the site. No share link SHALL load anything from another host before the reader activates it, and no share link SHALL add tracking parameters to the address.

#### Scenario: Reader posts to Bluesky
- **WHEN** a reader activates the Bluesky link on a claim page
- **THEN** a Bluesky post opens with the share sentence and the page's address, and the reader still has to confirm it

#### Scenario: Reader posts to Mastodon for the first time
- **WHEN** a reader activates the Mastodon link and has not named a server before
- **THEN** the page asks for the server, and opens that server's share page with the share sentence and the address

#### Scenario: Page loads
- **WHEN** a claim page loads
- **THEN** no share link has asked another host for anything

### Requirement: An embed can be found from the claim's address
Each published claim SHALL have an oEmbed description, of type `rich`, giving the embed snippet, its width and height, the claim's headline as the title, the site as provider and the wide card as the thumbnail. The claim page SHALL announce it. The description SHALL carry no status wording beyond what the embed itself shows.

#### Scenario: Claim address pasted into a site that reads oEmbed
- **WHEN** a claim page's address is pasted into an editor that reads oEmbed
- **THEN** the editor finds the description from the page and shows the claim's embed
