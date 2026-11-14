# Spec Delta

## Purpose

Lets the site tell people on other networks when a tracked claim's status changes and when a claim reaches an anniversary, from accounts the site owns, in the same neutral wording as everything else it shares.

## ADDED Requirements

### Requirement: A status change is posted once
When a published claim's status changes, the site SHALL post it once to each configured account: what the status was, what it is now, the date it changed, the "not medical advice" line and the claim page's address. A claim's first status SHALL NOT be posted. A change more than seven days old when first seen SHALL NOT be posted.

#### Scenario: Claim moves from Phase 1 to Phase 2
- **WHEN** a claim's status changes from Phase 1 trial to Phase 2 trial and the site is deployed
- **THEN** each configured account carries one post saying it was Phase 1 trial and is now Phase 2 trial, with the claim page's address

#### Scenario: Site deployed again
- **WHEN** the site is deployed again with the same change in its history
- **THEN** no second post is made

#### Scenario: Backfilled claim with old history
- **WHEN** a newly published claim's history holds changes from years ago
- **THEN** none of them is posted

### Requirement: An anniversary is posted on its day
On the anniversary of a published claim's first report, the site SHALL post once to each configured account: the claim's share sentence and the claim page's address. Only whole years SHALL be marked, and a claim first reported less than one year ago SHALL NOT be posted.

#### Scenario: Five years since first report
- **WHEN** today is five years after a claim was first reported
- **THEN** each configured account carries one post with that claim's share sentence and address

### Requirement: Posts use the site's wording only
A post SHALL be built from the site's status labels, the share sentence and dates. It SHALL contain no verdict wording, no word that judges the claim, an outlet or a person, no medical advice, and no mention of or reply to any account. The site SHALL NOT repost, like, follow or reply.

#### Scenario: Long-quiet claim reaches an anniversary
- **WHEN** a claim with a no-signal note is posted on its anniversary
- **THEN** the post gives the note in the site's wording and uses no word such as "dead", "abandoned" or "failed"

### Requirement: Posting is capped each day
The site SHALL make no more than four posts per account per day. Status changes SHALL be posted before anniversaries, and what does not fit SHALL be dropped, not carried to the next day.

#### Scenario: Seven anniversaries on one day
- **WHEN** seven claims share an anniversary and nothing else is due
- **THEN** four are posted and three are not posted on any later day

### Requirement: Posting is off until an account is configured
With no account configured, the site SHALL post nothing and SHALL build and deploy as before. A failure to post SHALL NOT fail a deployment or change any page.

#### Scenario: No account configured
- **WHEN** the site is deployed with no account's credentials set
- **THEN** nothing is posted and the deployment succeeds

#### Scenario: Network refuses a post
- **WHEN** an account's network refuses a post
- **THEN** the site's pages are unchanged and the post is not retried on a later day

### Requirement: A preview build posts nothing
A preview build SHALL NOT post to any account.

#### Scenario: Preview deployed
- **WHEN** a preview build is deployed with accounts configured
- **THEN** nothing is posted
