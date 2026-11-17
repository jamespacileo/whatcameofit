# Spec Delta

## ADDED Requirements

### Requirement: A lead a trial route found goes on though its outlet is on no list
A lead that a trial route found (a headline file kept it, the news search returned it, or a search for a trial reported it) SHALL go on to scoring when its outlet is on no list, with its outlet kind unknown. A lead that was only shared SHALL be stopped on such an outlet, as before. A lead on a listed kind that awaits a route SHALL be treated as that kind's rule says. No model SHALL decide an outlet's kind.

#### Scenario: A sponsor's own page a search reported
- **WHEN** a search for a trial reports an address on the sponsor's own website, which is on no list
- **THEN** the lead goes on to scoring with its outlet kind unknown

#### Scenario: The same domain, only shared
- **WHEN** a lead on a domain that is on no list has no reason but that people shared it
- **THEN** its outcome is unlisted outlet and it is not scored or read

#### Scenario: A paper index a search reported
- **WHEN** a search for a trial reports an address on a paper index
- **THEN** the lead is treated as that kind's rule says and is not scored

### Requirement: Screening reports the hosts that hold the most route-found leads
The screening report SHALL list, for leads that went on under this rule, the hosts that hold the most of them with their counts, so that a mirror, an aggregator or a host that republishes other outlets can be seen and listed as such.

#### Scenario: One host holds many
- **WHEN** one unlisted host holds 300 of 3,000 route-found leads
- **THEN** the report lists it first with its count
