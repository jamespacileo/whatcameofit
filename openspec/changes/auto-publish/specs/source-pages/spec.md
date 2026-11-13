# Spec Delta

## Purpose

Gives every article or post the pipeline read a page of its own, saying which claim it reports or, when no single claim is clear, which candidates it might and how sure the pipeline is about each.

## ADDED Requirements

### Requirement: A page per source
Each article or post the pipeline read SHALL have a page at `/source/{outlet}-{slug}` showing its headline, outlet, date and a link to the original. The page SHALL NOT show any text from the article or post.

#### Scenario: Reader opens a source page
- **WHEN** a reader opens the page of an article the pipeline read
- **THEN** it shows the headline, outlet, date and a link to the article, and no text from it

### Requirement: One claim or ranked candidates
When exactly one claim is approved for a source, its page SHALL name that claim, its status and its confidence, and link to the claim page. Otherwise the page SHALL list up to five candidates ranked by score, each with its confidence as a word and a percentage and its reasons. When no candidate is above the low band, the page SHALL say "No close match found" before the list.

#### Scenario: Source with one claim
- **WHEN** a source has one approved claim
- **THEN** its page names the claim with its status and confidence and links to the claim page

#### Scenario: Source with seven candidates
- **WHEN** a source has no approved claim and seven candidates
- **THEN** its page lists the five highest-scored, each with its confidence and reasons

#### Scenario: Only weak candidates
- **WHEN** every candidate for a source is in the low band
- **THEN** the page says "No close match found" and lists them

### Requirement: Source pages carry the site's notices
A source page SHALL carry the notice that a registered trial is not a treatment option and SHALL word no candidate as a verdict.

#### Scenario: Candidate is a registered trial
- **WHEN** a source page lists a registered trial as a candidate
- **THEN** the trial notice is shown and the trial is described by its phase and state only
