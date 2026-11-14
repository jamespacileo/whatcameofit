# Spec Delta

## ADDED Requirements

### Requirement: Each claim has its own data file
Each published claim SHALL have a data file at a stable address holding that claim exactly as the full download holds it, with the same licence, credit line, sources, method address and dates. The claim page SHALL name the file as its alternate in a machine-readable form and link to it in the page. The file SHALL leave out whatever the full download leaves out.

#### Scenario: Software reads one claim
- **WHEN** a program requests a claim's data file
- **THEN** it receives that claim's status, records, source reports and promises, with the licence and credit line

#### Scenario: Claim archived
- **WHEN** the operator archives a claim and the site is rebuilt
- **THEN** the claim's data file is no longer published

### Requirement: The site describes itself for software that reads sites
The site SHALL publish a plain-text description at `/llms.txt` giving what the site is, what a status means and does not mean, that it gives no medical advice and that a registered trial is not a treatment option, where the method is explained, where the full download and the per-claim files are, and the data's licence and credit line. It SHALL state no claim's status itself. A preview build SHALL say in it that its claims are unchecked.

#### Scenario: Assistant looks for how to cite the site
- **WHEN** software reads `/llms.txt`
- **THEN** it finds the addresses of the data, the licence, the credit line and the two notices
