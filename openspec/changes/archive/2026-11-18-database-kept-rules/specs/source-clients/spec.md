# Source clients: changes

## ADDED Requirements

### Requirement: Expired answers can be deleted
An operator SHALL be able to delete every cached answer whose lifetime has passed, and SHALL be told how many were deleted. An answer still within its lifetime SHALL be kept.

#### Scenario: One expired and one fresh
- **WHEN** the cache holds one answer that expired yesterday and one that expires tomorrow, and the operator deletes the expired answers
- **THEN** the first is deleted, the second is kept, and the operator is told that one was deleted

#### Scenario: A deleted answer is asked for again
- **WHEN** a request whose cached answer was deleted is made again
- **THEN** it is sent to the source, as it would have been had the expired answer been kept
