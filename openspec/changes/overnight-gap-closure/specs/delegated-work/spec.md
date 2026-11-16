# Spec Delta

## Purpose
How work that an assistant hands to another session or a subagent is assigned a model, reviewed, and merged, so that parallel work lands quickly without lowering what may reach the site or the database.

## ADDED Requirements

### Requirement: A delegated task is given a model by the kind of work it is
A task whose instructions settle what is to be done, and whose cost is mostly in the reading or writing of many tokens, SHALL be given the cheaper of the operator's two models. A task that needs design, a decision between approaches, or a judgement the instructions cannot settle, or that may prove harder than it looks, SHALL be given the stronger model. When it is unclear which a task is, it SHALL be treated as the second kind. The model a task ran on SHALL be stated wherever its result is reported.

#### Scenario: An audit under a written brief
- **WHEN** drafted claims are audited against a brief that lists each ground for archiving
- **THEN** the auditors run on the cheaper model, and the pass that decides the cases they flag as judgement calls runs on the stronger one

#### Scenario: A design document
- **WHEN** a session is asked for a schema, a specification or a plan
- **THEN** it runs on the stronger model

### Requirement: A delegated pull request is reviewed once and merged when clean
Every pull request from a delegated session SHALL be read once by a reviewer that did not write it, before it is merged. A pull request with no blocking finding SHALL be brought up to date with the main branch and merged as soon as its checks pass, without waiting for the operator. A finding that is not blocking SHALL NOT hold the merge: it SHALL be recorded as a follow-up in the pull request and merged around. No pull request SHALL stay open for a second round of non-blocking remarks.

#### Scenario: A clean review
- **WHEN** the reviewer reports no blocking finding and the checks pass
- **THEN** the pull request is merged in that hour and its session is archived

#### Scenario: Remarks that do not block
- **WHEN** the reviewer reports only findings outside the blocking list
- **THEN** the pull request is merged, and each finding is listed as a follow-up with the file it concerns

### Requirement: Only named risks block a merge
A finding SHALL block a merge only when it is one of these: records could be lost or wrongly merged; a claim could reach the site without its audit, or with a status no rule produced; an outlet the page reader has stopped could be asked; a secret or a private address could be written to the repository, a log or a world-readable file; article text could be stored or logged; a migration could run by itself or conflict with one on the main branch; a spending or request ceiling could be passed; a source could be asked outside its recorded terms. A blocking finding SHALL be sent back to the session that wrote the change with the file and the fix wanted, and the change SHALL be read again before it is merged.

#### Scenario: A hold that can be bypassed
- **WHEN** a review finds that a request can still reach an outlet the page reader has stopped
- **THEN** the pull request is not merged, the finding goes back to its session, and the fix is read again before the merge

### Requirement: A change that needs a migration is merged with its migration
A pull request that adds a migration SHALL NOT be merged while a run is writing to the working database from an older checkout, unless the migration only adds and the older code runs unchanged against it. Its merge, the backup, and the migration SHALL be done together, by the one session that writes to the working database.

#### Scenario: Reads are running
- **WHEN** a pull request with a migration is ready and a read run is in progress
- **THEN** it waits for the run to end, or is merged only after confirming the migration is additive and the running code is unaffected
