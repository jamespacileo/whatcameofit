## MODIFIED Requirements

### Requirement: Search settings preserve pages that cannot be searched
Enabling or disabling automatic search on a tracked claim, another page of the service, or a non-web page SHALL return to that page's existing state when no live lookup endpoint is available. Changing settings on the service's own pages SHALL NOT read the page, send a lookup or add the page to recent history.

#### Scenario: Change settings on the privacy page
- **WHEN** the reader changes automatic search from either enabled or disabled on the service's privacy page
- **THEN** the popup returns to “Open an article first”, without a page read, lookup or recent-history entry

### Requirement: Popup controls communicate their behavior
Buttons that open a new tab SHALL carry the external-link indicator and an accessible announcement. The empty following list SHALL name the actual follow control. The follow pill SHALL remain still when reduced motion is requested.

#### Scenario: Reviewed claims only
- **WHEN** an untracked page is opened with automatic search disabled
- **THEN** “Search tracked claims” indicates that it opens a new tab
