# Spec Delta

## Purpose

Makes each unit of processing work have one key and one stored result, so that a result made by any writer is used by every other and nothing is paid for twice.

## ADDED Requirements

### Requirement: A unit of work has a key
A triage score, a page fetch, an article read, a registry search, a paper search and a match decision SHALL each be identified by a key made from what was asked and the version of the step that answers it. Two writers asking the same thing SHALL arrive at the same key.

#### Scenario: The same article from two places
- **WHEN** a device's run and a reader's lookup both come to read the same article at the same extraction version
- **THEN** both compute the same key

#### Scenario: A tracking parameter
- **WHEN** two addresses differ only by a tracking parameter
- **THEN** work on either has the same key

### Requirement: A stored result is used before the work is done
Before doing a unit of work, a writer SHALL look for a stored result under its key and SHALL use it when it is still current. It SHALL count the work as answered from a stored result.

#### Scenario: Read by a backfill, then asked about by a reader
- **WHEN** a reader asks about an article a backfill read at the current extraction version
- **THEN** the article is not fetched and no extraction call is made

#### Scenario: A match already decided
- **WHEN** a claim's match to a trial was decided at the current version and the trial's record has not changed
- **THEN** the decision is not asked again

### Requirement: A negative result is stored and reused
A result of not health, nothing found, cannot be read or no match SHALL be stored under its key and reused like any other result.

#### Scenario: A page that refused
- **WHEN** an article could not be read an hour ago
- **THEN** no writer asks the page reader for it until its waiting time has passed

#### Scenario: A registry with nothing
- **WHEN** a registry search for an intervention and indication found no trial
- **THEN** the search is not sent again until its time to be asked again

### Requirement: Work is done again only for a stated reason
A stored result SHALL stop being current when its step's version rises, when what it was made from changes, or when its time to be asked again passes, and for no other reason. Each kind of work SHALL state which of these apply to it. A negative result SHALL always have a time after which it is asked again.

#### Scenario: Triage is reworded
- **WHEN** the triage version rises
- **THEN** stored scores at the old version are not used, and leads are scored again

#### Scenario: A trial's record changes
- **WHEN** a registry trial's payload has a new checksum
- **THEN** match decisions made from the old payload are asked again, and others are not

#### Scenario: An unreadable page, later
- **WHEN** a page's waiting time has passed
- **THEN** it is tried once more, and a further refusal sets a longer wait

### Requirement: A stored result holds no text
A stored result of a read SHALL be the structured result of the extraction and SHALL hold no text of the article. A stored result of a page fetch SHALL hold its outcome and time and SHALL NOT hold the page.

#### Scenario: Inspecting a stored read
- **WHEN** the operator reads a stored result of a read
- **THEN** it holds the fields the extraction produced and no passage of the article

### Requirement: A device knows what is stored without asking for each
The reference file a device pulls SHALL carry the keys of stored results a run can use, with what the run needs of each. A run SHALL push the results it made under the same keys.

#### Scenario: A second device, the same month
- **WHEN** a device works a month another device pushed yesterday
- **THEN** it scores and reads nothing the first device scored or read at the current versions

### Requirement: Outlets that refuse are left alone for a while
A writer SHALL keep, for each outlet, how often its pages could be read, and SHALL wait before asking again for a page from an outlet whose recent pages failed, for a time that grows with further failures and ends with a success.

#### Scenario: An outlet behind a wall
- **WHEN** the last ten pages asked of an outlet all failed
- **THEN** its other leads are not read until the outlet's waiting time has passed, and other outlets' leads are read meanwhile
