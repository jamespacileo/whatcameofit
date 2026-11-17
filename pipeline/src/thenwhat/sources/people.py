"""People in a ClinicalTrials.gov record, and the record without them. Pure.

The project keeps no personal data beyond subscriber emails (CLAUDE.md). A trial's full
record, as the registry gives it by identifier, names people: its officials and contacts,
each site's contacts, the investigator a responsible party is, a sponsor or collaborator
who is a person, and the results' point of contact. `without_people` removes each of
them and nothing else.

What reads a stored record, and that none of it is removed:

- `events/trial.py`: `statusModule`, `designModule.phases`, `hasResults`.
- `events/trial_facts.py` (the export's trial facts): `identificationModule.briefTitle`,
  `statusModule`, `designModule`, `eligibilityModule` (the count, not the criteria),
  `armsInterventionsModule`, `outcomesModule`, `referencesModule`, `resultsSection`'s
  outcome measures, and `sponsorCollaboratorsModule`'s lead sponsor's name and class
  and the responsible party's `type`. A sponsor who is a person is shown with no name
  there already.
- `lookup/details.py` and `decide/steps.py`: the lead sponsor's and collaborators' names,
  which are kept where the party is an organisation.
- `readings/service.py`: the outcome measures.

A site's facility, city and country are kept: they are places, not people.
"""

import re
from typing import Any

PERSON_CLASSES = frozenset({"INDIV", "INDIVIDUAL"})
SPONSOR_INVESTIGATOR = "SPONSOR_INVESTIGATOR"
# What a responsible party says of the person it is.
INVESTIGATOR_FIELDS = (
    "investigatorFullName",
    "investigatorTitle",
    "investigatorAffiliation",
    "oldNameTitle",
)
# Keys that hold a person's means of contact, wherever they appear.
CONTACT_KEYS = frozenset({"email", "phone", "phoneExt"})


def is_study(value: Any) -> bool:
    """Whether a payload is a ClinicalTrials.gov record."""
    return isinstance(value, dict) and isinstance(value.get("protocolSection"), dict)


def sponsored_by_a_person(sponsors: dict[str, Any]) -> bool:
    """Whether a record's lead sponsor is a person: the registry classes it as an
    individual, or the responsible party is a sponsor-investigator, whom the registry
    often classes as "other"."""
    lead = sponsors.get("leadSponsor")
    party = sponsors.get("responsibleParty")
    return (isinstance(lead, dict) and lead.get("class") in PERSON_CLASSES) or (
        isinstance(party, dict) and party.get("type") == SPONSOR_INVESTIGATOR
    )


def _without_contact_keys(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _without_contact_keys(v) for k, v in value.items() if k not in CONTACT_KEYS}
    if isinstance(value, list):
        return [_without_contact_keys(item) for item in value]
    return value


def without_people(study: dict[str, Any]) -> dict[str, Any]:
    """The registry's record with every person removed, and nothing else. The record given
    is not changed; one with no people is given back equal to it."""
    if not is_study(study):
        return study
    protocol = dict(study["protocolSection"])

    contacts = protocol.get("contactsLocationsModule")
    if isinstance(contacts, dict):
        kept = {
            k: v for k, v in contacts.items() if k not in ("centralContacts", "overallOfficials")
        }
        if isinstance(contacts.get("locations"), list):
            kept["locations"] = [
                {k: v for k, v in site.items() if k != "contacts"}
                if isinstance(site, dict)
                else site
                for site in contacts["locations"]
            ]
        protocol["contactsLocationsModule"] = kept

    sponsors = protocol.get("sponsorCollaboratorsModule")
    if isinstance(sponsors, dict):
        kept = dict(sponsors)
        lead = sponsors.get("leadSponsor")
        if isinstance(lead, dict) and sponsored_by_a_person(sponsors):
            kept["leadSponsor"] = {k: v for k, v in lead.items() if k != "name"}
        if isinstance(sponsors.get("collaborators"), list):
            kept["collaborators"] = [
                {k: v for k, v in party.items() if k != "name"}
                if isinstance(party, dict) and party.get("class") in PERSON_CLASSES
                else party
                for party in sponsors["collaborators"]
            ]
        party = sponsors.get("responsibleParty")
        if isinstance(party, dict):
            kept["responsibleParty"] = {
                k: v for k, v in party.items() if k not in INVESTIGATOR_FIELDS
            }
        protocol["sponsorCollaboratorsModule"] = kept

    stripped: dict[str, Any] = {**study, "protocolSection": protocol}
    results = study.get("resultsSection")
    if isinstance(results, dict) and isinstance(results.get("moreInfoModule"), dict):
        more = {k: v for k, v in results["moreInfoModule"].items() if k != "pointOfContact"}
        stripped["resultsSection"] = {**results, "moreInfoModule": more}
    return _without_contact_keys(stripped)


def _has_key(value: Any, keys: frozenset[str]) -> bool:
    if isinstance(value, dict):
        return any(k in keys or _has_key(v, keys) for k, v in value.items())
    if isinstance(value, list):
        return any(_has_key(item, keys) for item in value)
    return False


# The fields a record can name a person in, as the proof counts them.
FIELDS = (
    "centralContacts",
    "overallOfficials",
    "location contacts",
    "investigator name, title or affiliation",
    "person lead sponsor's name",
    "person collaborator's name",
    "results point of contact",
    "email",
    "phone",
)


def people_in(study: Any) -> set[str]:
    """The fields of `FIELDS` a record names a person in; empty for one without people
    or a payload that is not a registry record."""
    if not is_study(study):
        return set()
    found: set[str] = set()
    protocol = study["protocolSection"]
    contacts = protocol.get("contactsLocationsModule") or {}
    if isinstance(contacts, dict):
        if contacts.get("centralContacts"):
            found.add("centralContacts")
        if contacts.get("overallOfficials"):
            found.add("overallOfficials")
        sites = contacts.get("locations") or []
        if any(isinstance(site, dict) and site.get("contacts") for site in sites):
            found.add("location contacts")
    sponsors = protocol.get("sponsorCollaboratorsModule") or {}
    if isinstance(sponsors, dict):
        party = sponsors.get("responsibleParty") or {}
        if isinstance(party, dict) and any(party.get(k) for k in INVESTIGATOR_FIELDS):
            found.add("investigator name, title or affiliation")
        lead = sponsors.get("leadSponsor") or {}
        if isinstance(lead, dict) and lead.get("name") and sponsored_by_a_person(sponsors):
            found.add("person lead sponsor's name")
        for one in sponsors.get("collaborators") or []:
            if isinstance(one, dict) and one.get("name") and one.get("class") in PERSON_CLASSES:
                found.add("person collaborator's name")
    more = (study.get("resultsSection") or {}).get("moreInfoModule") or {}
    if isinstance(more, dict) and more.get("pointOfContact"):
        found.add("results point of contact")
    if _has_key(study, frozenset({"email"})):
        found.add("email")
    if _has_key(study, frozenset({"phone", "phoneExt"})):
        found.add("phone")
    return found


# --- a literature index's record of a paper ------------------------------------------
#
# The rule is openspec paper-facts, "The stored record holds no abstract and no author":
# before a paper's record is stored, its abstract, author names, author identifiers and
# affiliations are removed. `events/paper_facts.reduced` applies it to a paper's record
# (`paper_record`); this applies it to every literature record, a follow-up paper's
# event and a retraction notice's included, of each index the pipeline asks:
#
# - Europe PMC: `abstractText`, `authorList`, `authorString`, `authorIdList`,
#   `affiliation`, `investigatorList`, and the full-text links (`fullTextUrlList`,
#   `fullTextIdList`), as `paper_facts.NOT_STORED`;
# - OpenAlex: `authorships` (names, ORCIDs, institutions, raw affiliation strings),
#   `abstract_inverted_index`, `corresponding_author_ids`, `corresponding_institution_ids`;
# - Crossref: `author`, `editor`, `abstract`;
# - PubMed: already kept without abstract and author (`sources/pubmed.py`); `authors` and
#   `abstract` are removed if present.
#
# What reads a stored paper record, and that none of it is removed: paper facts
# (`events/paper_facts.py`: title, journal, year, publication types, open access,
# retraction, subject headings, DOI, PubMed number, the index's source and number), the
# export's papers, which read paper facts, and `events/fetch.py`'s `_index_record`, which
# needs the source and number. The authors and the abstract are read once, when a
# follow-up paper is found (`events/papers.describe`: a shared author, the intervention
# named in the abstract), from the record as fetched and before it is stored.

PAPER_KEYS = frozenset(
    {
        "abstractText",
        "authorList",
        "authorString",
        "authorIdList",
        "affiliation",
        "investigatorList",
        "fullTextUrlList",
        "fullTextIdList",
        "authorships",
        "abstract_inverted_index",
        "corresponding_author_ids",
        "corresponding_institution_ids",
        "author",
        "authors",
        "editor",
        "abstract",
    }
)
# A registry's person keys, wherever they appear: a guard for a record that is not shaped
# as a whole study (`protocolSection`) but carries part of one.
REGISTRY_PERSON_KEYS = frozenset(
    {
        "centralContacts",
        "overallOfficials",
        "investigatorFullName",
        "investigatorTitle",
        "investigatorAffiliation",
        "oldNameTitle",
        "pointOfContact",
        "contacts",
    }
)


def _without_keys(value: Any, keys: frozenset[str]) -> Any:
    if isinstance(value, dict):
        return {k: _without_keys(v, keys) for k, v in value.items() if k not in keys}
    if isinstance(value, list):
        return [_without_keys(item, keys) for item in value]
    return value


def paper_without_people(record: Any) -> Any:
    """A literature record without its authors, their identifiers and affiliations, its
    abstract and its full-text links, at any depth; anything else as it is."""
    return _without_keys(record, PAPER_KEYS)


def payload_without_people(payload: Any) -> Any:
    """Any stored payload without the people it names: a registry study by
    `without_people`; any other payload without a literature record's person and abstract
    keys, a registry's person keys and every email and phone, wherever they are."""
    if is_study(payload):
        return paper_without_people(without_people(payload))
    return _without_keys(payload, PAPER_KEYS | REGISTRY_PERSON_KEYS | CONTACT_KEYS)


def keys_found(value: Any, keys: frozenset[str]) -> set[str]:
    """Which of these keys appear anywhere in a value."""
    found: set[str] = set()
    if isinstance(value, dict):
        for k, v in value.items():
            if k in keys:
                found.add(k)
            found |= keys_found(v, keys)
    elif isinstance(value, list):
        for item in value:
            found |= keys_found(item, keys)
    return found


# An email address written in a text, as a proof counts it; nothing is changed by it.
EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")


def emails_in_text(value: Any) -> int:
    """How many strings in a value hold something shaped as an email address."""
    if isinstance(value, dict):
        return sum(emails_in_text(v) for v in value.values())
    if isinstance(value, list):
        return sum(emails_in_text(item) for item in value)
    return int(isinstance(value, str) and EMAIL.search(value) is not None)
