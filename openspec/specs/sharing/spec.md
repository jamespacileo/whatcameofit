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
