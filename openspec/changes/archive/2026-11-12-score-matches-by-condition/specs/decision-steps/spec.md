# Spec Delta

## ADDED Requirements

### Requirement: Several items in one backend call
A decision step SHALL be able to make the same choice for several items in one backend call, at most twenty items to a call. Each item SHALL get its own decision log entry, exactly as if it had been decided alone. A backend that cannot answer in batches SHALL be asked item by item. When any item of a batch has no usable answer, the batch SHALL fail after every one of its items is logged.

#### Scenario: Batch of candidates
- **WHEN** three candidates are scored by a backend that answers in batches
- **THEN** the backend is called once and three decision log entries are written

#### Scenario: Item left out
- **WHEN** the model's answer to a batch omits one item
- **THEN** that item is asked alone, and every item still gets its answer

#### Scenario: Usage of a batch
- **WHEN** a batch is answered by one model call
- **THEN** the usage ledger records one call
