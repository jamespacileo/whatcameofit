## ADDED Requirements

### Requirement: Stable initial popup size
The desktop extension SHALL report a 360px content width independently of the host's provisional viewport width, so its host can size the popup to display the content. The compact results and existing lookup behaviour SHALL remain unchanged.

#### Scenario: Narrow provisional viewport
- **WHEN** the host initially lays out the popup at 100px before measuring its content
- **THEN** the content measures 360px and remains 360px when the host expands to fit it

#### Scenario: Native Safari reopening
- **WHEN** the reader repeatedly closes and opens the extension on a reviewed article and an untracked public post
- **THEN** the popup shows its readable content at normal width, including after expanding and collapsing details
