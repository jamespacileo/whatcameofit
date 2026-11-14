## ADDED Requirements

### Requirement: A topic page opens for a reader who arrives from a shared link
Under its title a topic page SHALL say in one line what the page is and link the method page. Directly under the sentence that summarises where its claims stand, it SHALL offer to share the page, link the feed of the topic's status changes, and, where copying works, offer to copy that sentence with the month the registries were checked and the page's address. Where a suggestion address is configured, the page SHALL end with the link to suggest a headline.

#### Scenario: Arriving from a forum
- **WHEN** a reader opens a topic page with seven claims at 375 pixels wide
- **THEN** the line saying what the page is, the summary, Share, the feed link and "Copy sentence" all come before the first claim

#### Scenario: Copying the sentence
- **WHEN** the reader presses "Copy sentence" on a topic checked in November 2026
- **THEN** the copied text is the summary sentence, "Checked November 2026." and the topic page's address

#### Scenario: Copying is not possible
- **WHEN** the browser cannot copy
- **THEN** no copy control is shown and the sentence stays readable on the page
