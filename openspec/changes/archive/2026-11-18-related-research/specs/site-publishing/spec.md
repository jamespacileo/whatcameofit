# Spec Delta

## ADDED Requirements

### Requirement: Related research on the claim page
A claim page SHALL list the claim's approved papers under a heading of their own, apart from the evidence events. Each paper SHALL show its title, year, kind, a link to it, its confidence score and its reasons in the site's words. The section SHALL say that a paper is not a trial record and does not set the status. A claim with no approved paper SHALL show no such section.

#### Scenario: Claim with no trial and two approved papers
- **WHEN** a reader opens a claim whose status is "No trial record found" and which has two approved papers
- **THEN** the page shows that status and, apart from it, two papers with scores, reasons and links

#### Scenario: Claim with no approved paper
- **WHEN** a reader opens a claim that has no approved paper
- **THEN** the page has no related research section

### Requirement: Related research is worded without a verdict
The wording of the related research section and of each reason SHALL describe what was found and SHALL NOT say that a paper supports, confirms or refutes the claim. A reason code the site has no wording for SHALL fail the site build.

#### Scenario: Unknown reason code
- **WHEN** the export carries a reason code the site does not know
- **THEN** the site build fails and names the code
