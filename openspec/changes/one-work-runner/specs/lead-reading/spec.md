# Spec Delta

## ADDED Requirements

### Requirement: A site that cannot serve a page now is asked again
When the page reader asked a site and the site answered that it is busy, throttling or failing, a status of 202, 408, 425, 429 or any from 500 up, the lead SHALL be put off, not recorded as unreadable. It SHALL be due again after the wait the site stated, or after a configured wait, six hours unless set. No attempt SHALL be counted. A status that says the page is gone or was never there, 404 or 410, SHALL stay final.

#### Scenario: A site answers 503
- **WHEN** a site answers 503 for a lead's page
- **THEN** the lead is put off with that status as its reason, and a run after the wait asks for the page again

#### Scenario: A site answers 404
- **WHEN** a site answers 404 for a lead's page
- **THEN** the lead cannot be read, and is not asked for again

### Requirement: A refusal that can be put right is recorded as one
A lead that could not become a claim for a cause outside its article SHALL be recorded as needing a fix, with the cause as its reason: the site refused the reader (401, 403), the page gave no publication date or no headline, the page had too little text, the outlet has no display name, or no vertical was likely enough. It SHALL keep the read outcome it has today, and SHALL be read again when it is made due by that reason.

#### Scenario: A page with no date
- **WHEN** a lead's page gives no publication date
- **THEN** the lead cannot be read, its reason is the missing date, and requeuing that reason reads it again

#### Scenario: An outlet given a name
- **WHEN** an outlet with no display name is given one, and its reason is requeued
- **THEN** its leads are read

### Requirement: What the article is stays final
A lead refused for what its article is SHALL stay final: a class of treatments, not one treatment for one condition, business news on a topic, or enough articles for its claim. A lead left identity unresolved SHALL stay with the operator as today.

#### Scenario: A class of treatments
- **WHEN** a read names a class of treatments
- **THEN** the lead is finished, and requeuing a reason that can be put right does not take it

### Requirement: Every lead's reason is a code
The reason a lead was not read, or made no claim, SHALL be stored as a code with the values it carries, such as the status a site answered. The words shown for it SHALL be made from the code. Leads read before this change SHALL be given the code their stored words stand for, and none SHALL be left without one.

#### Scenario: A lead from an earlier run
- **WHEN** a lead's stored detail says the site answered 403
- **THEN** after migration its reason is the code for a site's refusal, carrying 403

#### Scenario: The funnel report
- **WHEN** the funnel report lists why leads could not be read
- **THEN** it counts them by code, in the words made from each code

### Requirement: Records a page names are looked up apart from the join
The registry numbers and papers an article's page names SHALL be recorded as candidates of its claim by a step of their own, after the article is joined or its claim drafted. A failure of that step SHALL leave the article and the claim as they are and SHALL be due again. No request to a registry or a literature index SHALL be made while the read holds the turn that settles which claim an article reports.

#### Scenario: The registry is down when an article is joined
- **WHEN** an article is added to a claim and the registry cannot be asked about the number its page names
- **THEN** the article is a source article of the claim, and the lookup of that number is due again

#### Scenario: Two reads at once
- **WHEN** two reads reach the point of settling which claim their article reports, and one article's page names five registry numbers
- **THEN** the second read does not wait for those five lookups
