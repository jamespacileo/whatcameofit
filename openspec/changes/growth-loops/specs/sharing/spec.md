# Spec Delta

## ADDED Requirements

### Requirement: A changed status has its own card
Each published claim whose status has changed at least once SHALL have a card, in the wide and square shapes, that shows the claim's headline or quoted title as its status card does, the status before, the status now, and the date of the change. It SHALL carry "Not medical advice" and the site's name, and SHALL use no word, tick, cross, arrow colour or other mark that judges the change as good or bad.

#### Scenario: Claim moved from Phase 1 to Phase 2
- **WHEN** a claim's latest change is from Phase 1 trial to Phase 2 trial on 3 October 2025
- **THEN** its change card shows "Was Phase 1 trial", "Now Phase 2 trial" and "3 Oct 2025", in the site's status wording

#### Scenario: Claim whose status has never changed
- **WHEN** a claim has only its first status
- **THEN** it has no change card and its page offers none

#### Scenario: Status moved back along the path
- **WHEN** a claim's status changes from Phase 2 trial to Trial registered
- **THEN** the card states both in the same type and colour as for any other change

### Requirement: The claim page offers the change card
A claim page whose claim has a change card SHALL offer it as a download in "Pass it on", with a text alternative stating the same facts.

#### Scenario: Reader passes on a change
- **WHEN** a reader opens "Pass it on" on a claim whose status has changed
- **THEN** a control downloads the change card, and a screen reader is given its facts as text

### Requirement: Year and topic pages have their own card
Each year page and each topic page SHALL have a wide link-preview card showing the page's title, the number of claims it lists, the number of those with an approval on record as a count, the month the registries were last checked, "Not medical advice" and the site's name. The card SHALL NOT show a percentage, a rank, a comparison with another year or topic, or any adjective about the count.

#### Scenario: Year page shared
- **WHEN** the page for claims first reported in 2019 is shared and it lists six claims, none approved
- **THEN** its preview card reads "First reported in 2019", "6 claims" and "Approvals on record: 0 of 6"

#### Scenario: Topic with one claim
- **WHEN** a topic page lists one claim
- **THEN** its card reads "1 claim"

### Requirement: A line to cite
Each claim page SHALL offer one line a reader can copy to cite the page: the site's name, the claim's headline, the status in the site's wording, the date the registries were last checked and the page's address. Copying SHALL work from the keyboard and the page SHALL say when the line has been copied.

#### Scenario: Reader copies the citation
- **WHEN** a reader activates the cite control on a claim checked on 11 November 2026 whose status is a Phase 1 trial
- **THEN** the clipboard holds a line naming the site, the headline, "Phase 1 trial", "11 Nov 2026" and the page's address

#### Scenario: Copying is not possible
- **WHEN** the browser refuses access to the clipboard
- **THEN** the line is shown as selectable text and nothing claims it was copied
