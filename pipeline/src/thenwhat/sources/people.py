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
