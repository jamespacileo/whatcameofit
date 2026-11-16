# Spec Delta

## ADDED Requirements

### Requirement: The site follows the reader's appearance and lets them choose
The site SHALL draw every page in a light theme or a dark theme. With no choice stored, it SHALL follow the device's appearance, including with no script. A control in the masthead SHALL let the reader choose light, dark or the device's appearance; the choice SHALL be kept in the reader's browser only, sent nowhere, and applied before the first paint. A printed page, the embed and the drawn extension popup SHALL stay light. The dark theme SHALL keep the light theme's meanings: amber for what was promised and nothing else, no colour for any status, and text contrast of at least 4.5:1.

#### Scenario: A device set to dark
- **WHEN** a reader with a device set to dark opens a claim page for the first time
- **THEN** the page is drawn dark, and the control names the device's appearance as the choice in force

#### Scenario: The reader chooses light
- **WHEN** that reader presses the control
- **THEN** the page is drawn light, and a later page of the site opens light from its first paint

#### Scenario: The device changes while the page is open
- **WHEN** no choice is stored and the device switches from dark to light
- **THEN** the open page follows it without a reload

#### Scenario: An embed on a dark device
- **WHEN** a claim's embed is shown inside another site to a reader whose device is set to dark
- **THEN** the embed is drawn light

#### Scenario: Printing in the dark theme
- **WHEN** a reader prints a claim page while it is drawn dark
- **THEN** the printed page is light, with no appearance control
