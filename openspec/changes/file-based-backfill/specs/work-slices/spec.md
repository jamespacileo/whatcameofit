# Spec Delta

## Purpose

Records in the truth store which part of a platform's files each device has taken to work on, so two devices do not pay to score and read the same links. It saves cost and never decides correctness.

## ADDED Requirements

### Requirement: Work slice
A work slice SHALL be one platform, one community and one calendar month. The truth store SHALL keep, for each slice anyone has taken, the device's name, when it was taken, when the taking lapses, and the run that finished it if one has.

#### Scenario: Listing slices
- **WHEN** the operator runs `thenwhat backfill slices list`
- **THEN** each slice is shown as free, taken by a device until a time, or done by a run

### Requirement: Taking and releasing
`thenwhat backfill slices take` SHALL take a free slice for the device and SHALL be refused, naming the holder, when another device holds it. Two devices asking at once SHALL NOT both be given it. A taking SHALL lapse after `SLICE_HOURS`, which has no default, after which the slice is free. A device MAY release a slice early.

#### Scenario: Two devices ask for the same month
- **WHEN** two devices ask for the same slice at the same moment
- **THEN** one is given it and the other is refused with the holder's name

#### Scenario: A laptop that never came back
- **WHEN** a taking's time has passed and no run finished the slice
- **THEN** the slice is listed as free

### Requirement: A run takes the slices its files cover
`thenwhat backfill run start` SHALL take the slices its input files cover and SHALL warn, naming the device, for each one another device holds. It SHALL start all the same when the operator says so.

#### Scenario: A month another device is working
- **WHEN** a run is started over a month another device holds
- **THEN** the operator is warned before any stage runs

### Requirement: A slice never blocks a merge
A merge SHALL apply a run whether or not its device held the slices its leads come from, and its report SHALL note each slice worked without being held. A merge SHALL mark a slice done when the run states that the whole of that slice's file was processed.

#### Scenario: Work done without taking
- **WHEN** a run for a month no device had taken is pushed
- **THEN** it is merged, the slice is marked done, and the report notes it was not held
