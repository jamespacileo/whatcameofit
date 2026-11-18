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

### Requirement: Unattended work decides for itself and writes the decision down
When the operator has said they cannot be asked, no session or subagent SHALL stop to ask a question. Where it would have asked, it SHALL take the option that is most practical and can be undone, carry on, and record the decision: what the choice was, what it chose, why, and how to undo it. The record SHALL be where the operator will read it first: the pull request's description for a session, the hand-over note for the session that coordinates.

#### Scenario: A choice between two reasonable approaches
- **WHEN** an unattended session meets a choice its instructions do not settle
- **THEN** it takes the more practical, reversible option, finishes the task, and lists the decision in its pull request under a heading the operator can find

#### Scenario: A blocked step
- **WHEN** an unattended session cannot complete a step
- **THEN** it does the rest of its task, says plainly what was not done and why, and does not wait

### Requirement: What cannot be undone waits, whatever else proceeds
Unattended work SHALL NOT take an action that cannot be undone or that the operator reserved, and SHALL queue it for the operator with what is needed to decide: applying a rekey or any merge of stored records; deleting data; passing a spending or request ceiling; creating accounts or cloud resources; installing or changing a scheduled job beyond pausing and resuming it; sending a message to anyone outside; accepting a source's terms. Publishing claims that passed the audit is not such an action when the operator has already agreed to it. Everything that does not depend on a queued action SHALL go on without it.

#### Scenario: The rekey overnight
- **WHEN** the survey of duplicate leads is ready and the operator is away
- **THEN** the counts are written for the operator, the rekey is not applied, and the trial reload and the pull requests proceed

#### Scenario: A ceiling is reached
- **WHEN** the night's model spend reaches its budget with work still due
- **THEN** the work that spends stops, the rest goes on, and the hand-over says what is still due

### Requirement: A change that needs a migration is merged with its migration
A pull request that adds a migration SHALL NOT be merged while a run is writing to the working database from an older checkout, unless the migration only adds and the older code runs unchanged against it. Its merge, the backup, and the migration SHALL be done together, by the one session that writes to the working database.

#### Scenario: Reads are running
- **WHEN** a pull request with a migration is ready and a read run is in progress
- **THEN** it waits for the run to end, or is merged only after confirming the migration is additive and the running code is unaffected
