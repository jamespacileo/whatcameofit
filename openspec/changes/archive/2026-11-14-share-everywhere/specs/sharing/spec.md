# Spec Delta

## ADDED Requirements

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
