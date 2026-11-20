# 11. A paper's byline stays in its stored record; its abstract and a registry's people do not

**Superseded on 2026-11-20.** The operator removed claims and the claims pipeline that day. Nothing in this repository acts on this decision any more; it is kept as the record of why the removed code worked as it did.

Date: 2026-11-17. Status: accepted. Change: `openspec/changes/cloudflare-source-of-truth`.

## Context

The project keeps no personal data beyond subscriber emails (`CLAUDE.md`). On 2026-11-17 a review found two kinds of names in stored payloads.

- **Registry studies.** A trial's whole ClinicalTrials.gov record names its officials and contacts, each site's contacts, the investigator a responsible party is, a sponsor who is a person, and the results' point of contact, with email addresses and phone numbers. 16,858 of 18,155 trial-event payloads held at least one.
- **Literature records.** A follow-up paper's index record carries its authors (`authorString`, `authorList`, `authorships`) and often its abstract. 16,124 of the 16,134 Europe PMC event payloads carried authors and 15,106 carried an abstract.

## Decision

Decided by the operator on 2026-11-17.

- **A registry's people are removed.** They are removed where an event is made, again in the store build, and from what Postgres already held (`thenwhat backfill strip-event-people`). The fields are listed in `pipeline/src/thenwhat/sources/people.py`. Every email address and phone number in any stored payload goes too.
- **A paper's authors stay.** They are its published byline, not personal data the tracker collects. `authorString`, `authorList`, `authorships` and the like are kept in stored literature records, and no proof counts them.
- **A paper's abstract goes, from every stored record and payload.** Amended by the operator later on 2026-11-17. The sources' own terms allow titles and links, not abstracts, whichever table would hold them (`docs/sources.md`: Europe PMC "titles and links only, no abstracts", Crossref "no abstracts"). The abstract is the publisher's text (`events/paper_facts.py`), and OpenAlex's abstract is to stay "in memory and in the HTTP cache only" (`sources/openalex.py`). The abstract keys (`abstractText`, `abstract_inverted_index`, `abstract`) are removed where a follow-up paper's or a retraction notice's event is made, again in the store build, and from what Postgres holds (`thenwhat backfill strip-paper-abstracts`). A paper's full-text links stay, as the terms allow links. That `paper-facts` named only a paper's own record was a gap in that spec, not a licence to keep abstracts elsewhere.

## Consequences

- **Removing a paper's authors needs a new decision.** A later reader should not "fix" this without one. A paper's abstract is read only from the record as fetched, before it is stored (`events/papers.describe`, the intervention named in the abstract). Nothing reads one from a stored payload.
- **222 stripped registry studies still hold an email address inside free text,** such as a description or eligibility text. They are reported, not changed.
- **Registry citations are kept.** A study's `referencesModule` citations are free text that names authors, and the trial facts read the module.
