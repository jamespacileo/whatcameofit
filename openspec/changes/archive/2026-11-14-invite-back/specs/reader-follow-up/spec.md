## ADDED Requirements

### Requirement: Follow is explained and confirmed in sight
Where a claim page offers to follow, it SHALL say in sight, beside a Follow control placed after the status, what following does and that the list is kept in the reader's browser only. Once the reader follows, the same place SHALL say so and SHALL link to the list on the home page. Every Follow control on the page SHALL show the same state.

#### Scenario: Following from a claim page
- **WHEN** a reader presses Follow under the status
- **THEN** every Follow control reads "Following", and the sentence beside it says the claim is listed on the home page, with a link there

### Requirement: A change is said on the claim page
When a reader who follows a claim opens its page and its status differs from the one kept, the page SHALL say once, after the status, the earlier status and the status now, and SHALL then bring the kept status up to date.

#### Scenario: A followed claim has changed status
- **WHEN** a reader who followed a claim at "Phase 2 trial" opens its page and the status is "Approved"
- **THEN** the page reads "Changed. When you last looked: Phase 2 trial. Now: Approved."

### Requirement: The home page says how to keep up
Under its lists the home page SHALL link the feed of status changes by a plain name. To a reader who follows no claim, where the browser can keep a list, it SHALL say what following is, that the day of a visit is noted, and that both are kept in the browser only. The method page SHALL list the ways to keep up: following, the since line, reminders, feeds and showing a status on another page.

#### Scenario: Ways to keep up
- **WHEN** a reader opens the method page
- **THEN** it names each way to keep up and says none needs an account
