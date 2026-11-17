# Spec Delta

## ADDED Requirements

### Requirement: Headline files and the search by a model have places in the order
Two routes SHALL be added to the fixed order of routes. Headline files SHALL come after the stored leads matched on the fingerprint and before the batched news search. The search by a model SHALL come last, after the mentions index. Both SHALL be off until the operator turns each on, and each SHALL run only under the rules that hold for every route: a dated entry for its source in `docs/sources.md`, a plan printed before it runs, and no start by a load or a daily run.

#### Scenario: Headline files and the batched search are both due
- **WHEN** a trial of the named set is due for the batched news search and headline files for the set's period are not yet loaded
- **THEN** the plan lists the headline files before the batched search

#### Scenario: The search by a model is not turned on
- **WHEN** coverage is looked for and the search by a model is off
- **THEN** no trial is handed to an agent and the plan says the route is off

### Requirement: The search by a model is not asked for a trial an earlier route sufficed for
A trial SHALL NOT be handed to a searching agent when a lead any earlier route gave for it was read and its claim is published.

#### Scenario: A headline file sufficed
- **WHEN** a headline kept on a trial's code was read and its claim is published
- **THEN** that trial is not due for the search by a model

### Requirement: Headline files are loaded for a period, not for a trial
The headline files route SHALL be planned and recorded by source and span of time, since one load serves every stored trial. Its plan SHALL print the spans not yet loaded, their size as the source states it, and what triage of the headlines it expects to keep would cost against the route's share of the ceiling.

#### Scenario: A plan for a month not yet loaded
- **WHEN** the operator asks for the plan and one month of a source is not loaded
- **THEN** the plan names the month, its size and the expected triage cost, and nothing is fetched or loaded
