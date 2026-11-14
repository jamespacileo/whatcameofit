# Spec Delta

## ADDED Requirements

### Requirement: The statement check is a decision step
Checking a reported statement against its article SHALL go through the decision interface as its own step, with the three options the reported-statements capability defines. Its log record SHALL refer to the article and to the statement's place among that article's proposed statements, and SHALL NOT hold the article's text or the statement's text.

#### Scenario: Six statements from one article
- **WHEN** six statements from one article are checked
- **THEN** six log records exist for the step, each referring to the article and a place from one to six, and none holds text from the article

#### Scenario: Backend failure
- **WHEN** the backend fails for one statement
- **THEN** the failure is logged and that statement is not stored
