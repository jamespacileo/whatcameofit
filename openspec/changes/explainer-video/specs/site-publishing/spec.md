## ADDED Requirements

### Requirement: The method page shows an explainer video
The method page SHALL show the explainer video under its lede as a file served by the site itself. The video SHALL NOT play on its own, and nothing of it except its poster image SHALL be fetched before the reader presses play. The page SHALL state the month the registries were checked for the records the video shows, and SHALL carry the video's narration as text. The video SHALL hold to the site's rules: no verdict wording, no medical advice, an outlet's headline only in quotation marks with the outlet named, and no article text.

#### Scenario: Opening the method page
- **WHEN** a reader opens the method page
- **THEN** the video is shown with its poster and controls, is not playing, and the video file has not been requested

#### Scenario: A reader who cannot play it
- **WHEN** a reader cannot or does not play the video
- **THEN** its narration can be read on the page, and the rest of the page explains the method without it

#### Scenario: A claim in the video has since changed
- **WHEN** a claim shown in the video has a newer status than the video shows
- **THEN** the caption's date tells the reader the video's records are as of that month, and the claim page shows the current status
