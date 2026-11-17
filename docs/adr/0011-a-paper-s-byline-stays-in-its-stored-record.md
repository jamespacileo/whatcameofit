# 11. A paper's byline stays in its stored record; a registry's people do not

Date: 2026-11-17. Status: accepted. Change: `openspec/changes/cloudflare-source-of-truth`.

## Context

The project keeps no personal data beyond subscriber emails (`CLAUDE.md`). On 2026-11-17 a review found two kinds of names in stored payloads.

- **Registry studies.** A trial's whole ClinicalTrials.gov record names its officials and contacts, each site's contacts, the investigator a responsible party is, a sponsor who is a person, and the results' point of contact, with email addresses and phone numbers. 16,858 of 18,155 trial-event payloads held at least one.
- **Literature records.** A follow-up paper's index record carries its authors (`authorString`, `authorList`, `authorships`) and often its abstract. 16,124 of the 16,134 Europe PMC event payloads carried authors and 15,106 carried an abstract.

## Decision

Decided by the operator on 2026-11-17.

- **A registry's people are removed.** They are removed where an event is made, again in the store build, and from what Postgres already held (`thenwhat backfill strip-event-people`). The fields are listed in `pipeline/src/thenwhat/sources/people.py`. Every email address and phone number in any stored payload goes too.
- **A paper's authors stay.** They are its published byline, not personal data the tracker collects. `authorString`, `authorList`, `authorships` and the like are kept in stored literature records, and no proof counts them.
- **A paper's abstract also stays in an event's payload.** The written rule, openspec `paper-facts`, "The stored record holds no abstract and no author", covers the record a paper's facts are read from (`paper_record`). That record is stored without either. The rule does not cover an evidence event's payload, and nothing was built to strip abstracts from one.

## Consequences

- **Removing authors or abstracts from event payloads needs a new decision.** A later reader should not "fix" this without one.
- **222 stripped registry studies still hold an email address inside free text,** such as a description or eligibility text. They are reported, not changed.
- **Registry citations are kept.** A study's `referencesModule` citations are free text that names authors, and the trial facts read the module.
