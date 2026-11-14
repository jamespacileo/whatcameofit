## ADDED Requirements

### Requirement: Current brand assets
The site SHALL generate browser and home-screen icons from the selected canonical
artwork, including a conventional multi-size ICO. Changing that artwork SHALL change
the URLs advertised for browser, launcher and share images. Maskable icons SHALL keep
the symbol within the central safe area.

#### Scenario: Returning reader after a rebrand
- **WHEN** new artwork is deployed
- **THEN** the page advertises a new revision of each brand asset

### Requirement: Resilient source icons
Source attribution SHALL use locally stored publisher icons, with a same-size letter
tile when no icon is stored or an image fails to load. Outlet names and domains SHALL
remain distinguishable and wrap within narrow viewports.
Transparent publisher marks SHALL remain legible against light and dark reading
surfaces. Corrected image bytes SHALL produce a new local asset URL. A generic
hosting-platform logo SHALL use the letter fallback until a publisher icon is available.

#### Scenario: An icon request fails
- **WHEN** a stored publisher image cannot load
- **THEN** its letter tile remains and the source name and article link remain usable

#### Scenario: Dark reading surface
- **WHEN** a publisher supplies a transparent dark mark
- **THEN** a light backing preserves the mark's contrast without changing its colours

#### Scenario: Publisher artwork corrected
- **WHEN** the stored image changes
- **THEN** the rendered source uses a different asset URL so a cached image cannot hide the correction
