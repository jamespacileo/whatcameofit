"""No person in a stored registry record: removed where an event is made, removed from
what Postgres already holds, and proved absent from a store file. Studies are synthetic."""

import copy
import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from test_store_records import STORE, _claim
from thenwhat.db.models import EvidenceEvent
from thenwhat.events.trial import trial_events
from thenwhat.events.trial_facts import read_trial
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.people import FIELDS, people_in, without_people
from thenwhat.store.people import prove_file, strip

FIXTURES = Path(__file__).parent / "fixtures" / "clinicaltrials"


def _study() -> dict[str, Any]:
    """A made-up record naming a person in every field `FIELDS` names."""
    return {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "briefTitle": "A trial"},
            "statusModule": {
                "overallStatus": "COMPLETED",
                "studyFirstPostDateStruct": {"date": "2020-01-02"},
                "completionDateStruct": {"date": "2021-03-04", "type": "ACTUAL"},
            },
            "designModule": {"phases": ["PHASE2"], "enrollmentInfo": {"count": 40}},
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": "Dr A Made-up Person", "class": "OTHER"},
                "responsibleParty": {
                    "type": "SPONSOR_INVESTIGATOR",
                    "investigatorFullName": "A Made-up Person",
                    "investigatorTitle": "Professor",
                    "investigatorAffiliation": "Example University",
                },
                "collaborators": [
                    {"name": "Example Pharma", "class": "INDUSTRY"},
                    {"name": "B Made-up Person", "class": "INDIV"},
                ],
            },
            "contactsLocationsModule": {
                "centralContacts": [{"name": "C Person", "email": "c@example.org"}],
                "overallOfficials": [{"name": "D Person", "role": "PRINCIPAL_INVESTIGATOR"}],
                "locations": [
                    {
                        "facility": "Example Hospital",
                        "city": "Leeds",
                        "country": "United Kingdom",
                        "contacts": [{"name": "E Person", "phone": "+44 0000"}],
                    }
                ],
            },
        },
        "resultsSection": {
            "moreInfoModule": {
                "pointOfContact": {"title": "F Person", "email": "f@example.org", "phone": "1"},
                "certainAgreement": {"piSponsorEmployee": False},
            }
        },
        "hasResults": True,
    }


def test_every_person_field_is_removed_and_nothing_else():
    study = _study()
    given = copy.deepcopy(study)
    assert people_in(study) == set(FIELDS)
    kept = without_people(study)
    assert study == given, "the record given is not changed"
    assert people_in(kept) == set()
    text = json.dumps(kept)
    for name in ("Made-up Person", "C Person", "D Person", "E Person", "F Person", "@example"):
        assert name not in text
    # Kept: what a status, a page and a lookup read, and the places.
    protocol = kept["protocolSection"]
    assert protocol["statusModule"] == given["protocolSection"]["statusModule"]
    assert protocol["designModule"] == given["protocolSection"]["designModule"]
    assert protocol["sponsorCollaboratorsModule"]["leadSponsor"] == {"class": "OTHER"}
    assert protocol["sponsorCollaboratorsModule"]["responsibleParty"] == {
        "type": "SPONSOR_INVESTIGATOR"
    }
    assert protocol["sponsorCollaboratorsModule"]["collaborators"][0]["name"] == "Example Pharma"
    assert protocol["contactsLocationsModule"]["locations"] == [
        {"facility": "Example Hospital", "city": "Leeds", "country": "United Kingdom"}
    ]
    assert kept["resultsSection"]["moreInfoModule"] == {
        "certainAgreement": {"piSponsorEmployee": False}
    }
    assert without_people(kept) == kept


def test_a_trial_s_facts_are_the_same_without_its_people():
    for path in sorted(FIXTURES.glob("study_*.json")):
        study = json.loads(path.read_text())
        assert read_trial(without_people(study)) == read_trial(study), path.name


def test_an_event_read_from_a_trial_keeps_no_person():
    record = SourceRecord(
        "clinicaltrials.gov",
        "NCT00000001",
        "https://clinicaltrials.gov/study/NCT00000001",
        _study(),
        datetime(2026, 11, 17, tzinfo=UTC),
    )
    events = trial_events(record)
    assert events
    for event in events:
        assert people_in(event.raw_payload) == set()


def test_stored_records_are_stripped_once_and_counted(session: Session):
    claim = _claim("drug-p-for-melanoma")
    session.add(claim)
    session.flush()
    session.add(
        EvidenceEvent(
            claim_id=claim.id,
            type="trial_registered",
            event_date=date(2020, 1, 2),
            source_name="clinicaltrials.gov",
            source_url="https://clinicaltrials.gov/study/NCT00000001",
            external_id="NCT00000001",
            summary="Registered.",
            confidence=1.0,
            raw_payload=_study(),
            fetched_at=datetime(2026, 11, 17, tzinfo=UTC),
            dedupe_key="trial_registered:NCT00000001",
        )
    )
    session.flush()
    counted = strip(session, apply=False)
    assert counted.changed["evidence_event"] == 1
    assert counted.before["evidence_event"]["overallOfficials"] == 1
    held = session.scalars(select(EvidenceEvent.raw_payload)).one()
    assert people_in(held) == set(FIELDS), "counting writes nothing"

    applied = strip(session, apply=True)
    assert applied.changed["evidence_event"] == 1 and not applied.after["evidence_event"]
    session.expire_all()
    assert people_in(session.scalars(select(EvidenceEvent.raw_payload)).one()) == set()
    assert strip(session, apply=True).changed["evidence_event"] == 0


def test_a_store_file_naming_a_person_is_found(tmp_path: Path):
    path = tmp_path / "s.sqlite"
    db = sqlite3.connect(path)
    db.executescript((STORE / "schema.sql").read_text())
    db.execute(
        "INSERT INTO run (id, writer, device, commit_sha, registered_at)"
        " VALUES ('r', 'migration', 'd', 'abc1234', '2026-11-17T00:00:00.000000+00:00')"
    )
    for study in (_study(), without_people(_study())):
        body = json.dumps(study)
        db.execute(
            "INSERT INTO payload (sha256, bytes, body, added_run) VALUES (?, ?, ?, 'r')",
            (f"{len(body):064d}", len(body), body),
        )
    db.commit()
    found = prove_file(path)
    assert found["payload row: overallOfficials"] == 1
    assert set(found) == {f"payload row: {name}" for name in FIELDS}
