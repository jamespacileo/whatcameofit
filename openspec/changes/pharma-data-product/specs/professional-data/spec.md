# Spec Delta

## Purpose

States what the tracker offers to organisations that pay for it, and the conditions under which that offer leaves the public site, its records and its wording exactly as they would be if nobody paid.

## ADDED Requirements

### Requirement: The paid offer holds nothing the public site withholds
Every claim, status, evidence event, score and derived view available to a paying organisation SHALL also be on the public site and in its public data files, under the same licence, no later than it is available to the paying organisation. The paid offer SHALL NOT hold any fact the open data file is required to leave out.

#### Scenario: Claim found by coverage a customer asked for
- **WHEN** a backfill run for a health area a customer named produces a claim that is approved and cleared by its audit
- **THEN** the claim is published on the public site and in the data file in the same export that first serves it to the customer

#### Scenario: Share-alike drug fact
- **WHEN** a claim's drug card rests on a fact the data file leaves out for its licence
- **THEN** the keyed route leaves it out too

### Requirement: Paying changes no record
No payment or customer request SHALL add, remove, hold back, reword or re-score a claim, a status, an evidence event or a match. A customer's report that a record is wrong SHALL be handled by the route open to any reader and decided by the same rule.

#### Scenario: Customer asks for a claim about its own product to be removed
- **WHEN** a paying organisation asks for a published claim to be taken down and the claim's evidence is correct
- **THEN** the claim stays published and unchanged

#### Scenario: Customer reports a wrong match
- **WHEN** a paying organisation reports that a trial does not test the claim's intervention for its indication, and it does not
- **THEN** the operator archives the match as for any reader's report, and the change is published to everyone

### Requirement: Funded coverage is disclosed
When a health area is backfilled at a paying organisation's request, the method page SHALL state that the area's coverage was funded and the month it was done. It SHALL name the organisation only with its agreement.

#### Scenario: Area covered at a customer's request
- **WHEN** a reader opens the method page after a funded backfill of a health area
- **THEN** the page names the area and the month and says its coverage was paid for

### Requirement: Early-stage list
The site SHALL publish a list of every published claim whose status is "preclinical only" or "no trial record found". Each entry SHALL carry the claim's intervention and indication, its status, the date of its first report, the whole years since that date, its no-signal overlay if it has one, its approach and health area where set, and each organisation it names with its roles.

#### Scenario: Claim reported in 2014 with no trial found
- **WHEN** a published claim was first reported in March 2014, its evidence stage is confirmed as animal work and no trial is matched
- **THEN** the list holds it as "preclinical only" with its first-report date, the whole years since, and the organisations its reports name

#### Scenario: Claim gains a registered trial
- **WHEN** a listed claim's status becomes "trial registered"
- **THEN** the next export's list no longer holds it

#### Scenario: Stage read in the lower band
- **WHEN** a claim with no trial has an evidence stage read only in the lower confidence band
- **THEN** the list holds it as "no trial record found", as its status says, and does not use the reading to place it

### Requirement: The early-stage list holds only what status says, in no order of merit
The list SHALL hold no claim with any other status and no fact the claim's own page does not show. It SHALL carry no score, rank or order that expresses merit; its default order SHALL be by date of first report.

#### Scenario: Two listed claims
- **WHEN** the list holds a claim first reported in 2012 and one first reported in 2019
- **THEN** the 2012 claim comes first, and neither carries a score or rank

### Requirement: The early-stage list is worded without verdict or offer
The list and every page, file and route that carries it SHALL be worded by the site and SHALL NOT say or imply that a listed claim's research has stopped, is available, is unlicensed, is unfunded or is an opportunity. It SHALL state what the tracker does not know about a listed claim: its licensing, its funding, unpublished work, and trials in registries not yet asked. It SHALL NOT present any listed intervention as a treatment.

#### Scenario: Verdict wording in a label
- **WHEN** a label or heading for the list contains "abandoned", "stalled", "available" or "opportunity"
- **THEN** the site build fails

#### Scenario: Reader opens the list
- **WHEN** a reader opens the early-stage list
- **THEN** the page says that no trial record found is not a finding that work stopped, and names what the tracker has not checked

### Requirement: Translation counts
The site SHALL publish, for each year of first report, the number of published claims first reported in that year and how many of them stand at each status today. Each figure SHALL be shown with the number of claims it is counted from.

#### Scenario: Archived claim
- **WHEN** a claim is archived
- **THEN** the next export's counts leave it out

### Requirement: Translation counts are not presented as rates or forecasts
The view SHALL state how the tracker's claims were gathered and that they are not a sample of all reports. It SHALL show no percentage for a group smaller than a minimum the operator sets, and SHALL NOT use "probability", "likelihood", "success rate" or any forecast.

#### Scenario: Year with few claims
- **WHEN** a year has fewer published claims than the minimum
- **THEN** the view shows that year's counts and no percentage

#### Scenario: Year above the minimum
- **WHEN** a year has at least the minimum number of published claims
- **THEN** the view may show each status as a share of that year's claims, beside the counts and the number counted

### Requirement: Changes since a date, by key
The site's service SHALL answer a keyed request for the status changes since a given date, for all published claims or for a list of claims the request names, with each change's claim, earlier status, new status, date and explaining events. It SHALL answer only from published records. A request without a valid key SHALL be refused and told where the same records are published openly.

#### Scenario: Watch list of three claims, one changed
- **WHEN** a keyed request names three claims and a date, and one claim's status changed after that date
- **THEN** the answer holds that one change with its explaining events

#### Scenario: No key
- **WHEN** a request to the keyed route carries no valid key
- **THEN** it is refused and the answer names the open data file's address

#### Scenario: Preview build
- **WHEN** the keyed route is asked on a preview build
- **THEN** it answers nothing but that the build is a preview
