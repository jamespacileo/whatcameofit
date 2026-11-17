"""A paper's byline stays in a stored literature record and its abstract goes
(docs/adr/0011); a registry's person keys and any email or phone go from every payload."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from test_store_records import STORE
from thenwhat.events.paper_facts import read_paper
from thenwhat.events.papers import follow_up_event
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.people import (
    ABSTRACT_KEYS,
    REGISTRY_PERSON_KEYS,
    keys_found,
    payload_without_people,
    without_abstract,
)
from thenwhat.store.people import prove_file

FIXTURES = Path(__file__).parent / "fixtures"


def _europepmc() -> dict[str, Any]:
    page = json.loads((FIXTURES / "europepmc" / "paper_srep39654.json").read_text())
    return page["resultList"]["result"][0]


def test_a_follow_up_paper_keeps_its_byline_and_loses_its_abstract():
    """Decided by the operator on 2026-11-17: a paper's authors are its published byline;
    its abstract is not the tracker's to keep."""
    record = _europepmc()
    assert record.get("abstractText") and record.get("authorString")
    citing = SourceRecord(
        "europepmc",
        f"MED:{record['pmid']}",
        "https://europepmc.org/x",
        record,
        datetime(2026, 11, 17, tzinfo=UTC),
    )
    event = follow_up_event(citing, 0.9)
    assert event is not None
    kept = event.raw_payload
    assert not keys_found(kept, ABSTRACT_KEYS)
    assert kept["authorString"] == record["authorString"]
    assert kept["authorList"] == record["authorList"]
    assert kept["fullTextUrlList"] == record["fullTextUrlList"]
    assert payload_without_people(record) == without_abstract(record) == kept


def test_nothing_read_from_a_stored_paper_record_is_its_abstract():
    record = _europepmc()
    assert read_paper(without_abstract(record)) == read_paper(record)
    page = json.loads((FIXTURES / "openalex" / "search_median_nerve_tourette.json").read_text())
    work = page["results"][0]
    assert "abstract_inverted_index" in work
    kept = without_abstract(work)
    assert "abstract_inverted_index" not in kept and kept["authorships"] == work["authorships"]


def test_any_payload_loses_a_registry_s_person_keys_and_contacts_wherever_they_are():
    partial = {
        "study": {"contactsLocationsModule": {"overallOfficials": [{"name": "P"}]}},
        "note": {"email": "x@example.org", "phone": "1"},
    }
    kept = payload_without_people(partial)
    assert not keys_found(kept, REGISTRY_PERSON_KEYS | {"email", "phone"})


def test_a_store_file_s_byline_passes_and_its_abstract_and_registry_contact_fail(tmp_path: Path):
    path = tmp_path / "s.sqlite"
    db = sqlite3.connect(path)
    db.executescript((STORE / "schema.sql").read_text())
    db.execute(
        "INSERT INTO run (id, writer, device, commit_sha, registered_at)"
        " VALUES ('r', 'migration', 'd', 'abc1234', '2026-11-17T00:00:00.000000+00:00')"
    )
    for sha, payload in (
        ("a" * 64, {"title": "T", "authorString": "A B, C D.", "abstractText": "Text."}),
        ("b" * 64, {"centralContacts": [{"name": "P"}]}),
    ):
        body = json.dumps(payload)
        db.execute(
            "INSERT INTO payload (sha256, bytes, body, added_run) VALUES (?, ?, ?, 'r')",
            (sha, len(body), body),
        )
    db.commit()
    assert prove_file(path) == {"payload row: centralContacts": 1, "payload row: abstractText": 1}


def test_stored_abstracts_are_stripped_once_and_counted(session):
    from datetime import date

    from sqlalchemy import select

    from test_store_records import _claim
    from thenwhat.db.models import EvidenceEvent
    from thenwhat.store.people import strip_abstracts

    claim = _claim("drug-r-for-melanoma")
    session.add(claim)
    session.flush()
    session.add(
        EvidenceEvent(
            claim_id=claim.id,
            type="followup_paper",
            event_date=date(2020, 1, 2),
            source_name="europepmc",
            source_url="https://europepmc.org/x",
            external_id="MED:2",
            summary="A paper.",
            confidence=0.9,
            raw_payload=_europepmc(),
            fetched_at=datetime(2026, 11, 17, tzinfo=UTC),
            dedupe_key="followup:MED:2",
        )
    )
    session.flush()
    counted = strip_abstracts(session, apply=False)
    assert counted.before[("evidence_event", "europepmc", "abstractText")] == 1
    assert "abstractText" in session.scalars(select(EvidenceEvent.raw_payload)).one()
    strip_abstracts(session, apply=True)
    session.expire_all()
    held = session.scalars(select(EvidenceEvent.raw_payload)).one()
    assert "abstractText" not in held and held["authorString"]
    assert not strip_abstracts(session, apply=True).changed
