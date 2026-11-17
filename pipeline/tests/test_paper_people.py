"""A paper's byline and abstract stay in a stored literature record (docs/adr/0011); a
registry's person keys and any email or phone go from every payload."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from test_store_records import STORE
from thenwhat.events.papers import follow_up_event
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.people import REGISTRY_PERSON_KEYS, keys_found, payload_without_people
from thenwhat.store.people import prove_file

FIXTURES = Path(__file__).parent / "fixtures"


def _europepmc() -> dict[str, Any]:
    page = json.loads((FIXTURES / "europepmc" / "paper_srep39654.json").read_text())
    return page["resultList"]["result"][0]


def test_a_follow_up_paper_keeps_its_byline_and_abstract():
    """Decided by the operator on 2026-11-17: a paper's authors are its published byline."""
    record = _europepmc()
    citing = SourceRecord(
        "europepmc",
        f"MED:{record['pmid']}",
        "https://europepmc.org/x",
        record,
        datetime(2026, 11, 17, tzinfo=UTC),
    )
    event = follow_up_event(citing, 0.9)
    assert event is not None and event.raw_payload == record
    assert payload_without_people(record) == record


def test_any_payload_loses_a_registry_s_person_keys_and_contacts_wherever_they_are():
    partial = {
        "study": {"contactsLocationsModule": {"overallOfficials": [{"name": "P"}]}},
        "note": {"email": "x@example.org", "phone": "1"},
    }
    kept = payload_without_people(partial)
    assert not keys_found(kept, REGISTRY_PERSON_KEYS | {"email", "phone"})


def test_a_store_file_with_a_byline_passes_and_one_with_a_registry_contact_fails(tmp_path: Path):
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
    assert prove_file(path) == {"payload row: centralContacts": 1}
