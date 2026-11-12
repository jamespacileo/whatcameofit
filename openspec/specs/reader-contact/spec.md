# reader-contact Specification

## Purpose
How a reader tells the operator about a headline worth tracking or a mistake on a page, and what the site does and does not collect when they do.

## Requirements

### Requirement: Suggest a headline
When a suggestion address is configured, the home page and the search's "not tracked" answers SHALL link to it with words that ask for the address of a news article. When a reader has just pasted an article address that the site does not track, the link SHALL carry that address forward so the reader need not type it again. When no suggestion address is configured, no such link SHALL be shown.

#### Scenario: Pasted link is not tracked
- **WHEN** a reader pastes the address of an article that matches no tracked claim and a suggestion address is configured
- **THEN** the answer includes a link to suggest it, already holding the pasted address

#### Scenario: No suggestion address
- **WHEN** the site is built with no suggestion address configured
- **THEN** no page shows a link to suggest a headline

### Requirement: Report an error
When a corrections address is configured, every claim page SHALL link to it with words that ask what is wrong and what source shows it, and the link SHALL carry the claim page's address forward. The site SHALL NOT promise a reply time.

#### Scenario: Reader reports an error
- **WHEN** a reader follows the corrections link on a claim page
- **THEN** the message or form they reach already names that claim page

### Requirement: The site collects nothing from a reader who writes
The site SHALL NOT include a form that sends a reader's words, address or any identifier to a server of the site's own, and SHALL NOT store anything a reader writes. Suggestions and corrections SHALL travel only through the reader's own mail or a public issue tracker that the reader chooses to use. Wherever a contact link appears, the page SHALL say which of the two it opens.

#### Scenario: Reader chooses not to write
- **WHEN** a reader opens any page and never follows a contact link
- **THEN** nothing about them has been sent anywhere by a contact feature

#### Scenario: Link opens the reader's mail
- **WHEN** the configured address is a mail address
- **THEN** the link is labelled as opening the reader's mail, and the message is sent by the reader's own mail service, not by the site
