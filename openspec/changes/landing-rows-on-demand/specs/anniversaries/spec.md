# Spec Delta

## ADDED Requirements

### Requirement: The home page fetches the one day it shows
The home page as built SHALL hold no day of the calendar of first reports. It SHALL hold which days have a first report and in which years, and SHALL fetch the reports of the one day the reader's own date picks. If that day does not arrive, the block SHALL be shown with its heading, SHALL say that the day's anniversaries did not load, and SHALL offer a control to ask again.

#### Scenario: Opening the home page on a day with an anniversary
- **WHEN** a reader opens the home page on 13 November 2026 and a claim was first reported on 13 November 2021
- **THEN** the page fetches the reports of 13 November and no other day, and lists the claim under "On this day"

#### Scenario: The day does not arrive
- **WHEN** the reports of the day picked cannot be fetched
- **THEN** the block says "The anniversaries for this day did not load." with a control to try again, and keeps its link to the anniversaries page
