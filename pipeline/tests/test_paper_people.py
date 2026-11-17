"""No author and no abstract in a stored literature record, of any index; and no person's
keys in any stored payload. Records here are the recorded fixtures and made-up ones."""

import json
import sqlite3
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from test_store_records import STORE, _claim
from thenwhat.db.models import EvidenceEvent
from thenwhat.events.paper_facts import read_paper, reduced
from thenwhat.events.papers import follow_up_event
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.people import (
    PAPER_KEYS,
    REGISTRY_PERSON_KEYS,
    emails_in_text,
    keys_found,
    paper_without_people,
    payload_without_people,
)
from thenwhat.store.people import prove_file, strip_papers

FIXTURES = Path(__file__).parent / "fixtures"


def _europepmc() -> dict[str, Any]:
    page = json.loads((FIXTURES / "europepmc" / "paper_srep39654.json").read_text())
    return page["resultList"]["result"][0]


def test_a_paper_s_facts_are_the_same_without_its_authors_and_abstract():
    record = _europepmc()
    assert keys_found(record, PAPER_KEYS) >= {"abstractText", "authorList", "authorString"}
    kept = paper_without_people(record)
    assert not keys_found(kept, PAPER_KEYS)
    assert read_paper(kept) == read_paper(record) == read_paper(reduced(record))
    for name in ("title", "journalInfo", "pubYear", "doi", "pmid", "source", "id"):
        assert kept.get(name) == record.get(name), name


def test_an_openalex_and_a_crossref_record_lose_their_authors_and_abstract():
    page = json.loads((FIXTURES / "openalex" / "search_median_nerve_tourette.json").read_text())
    work = page["results"][0]
    assert keys_found(work, PAPER_KEYS) & {"authorships", "abstract_inverted_index"}
    kept = paper_without_people(work)
    assert not keys_found(kept, PAPER_KEYS)
    assert kept["title"] == work["title"] and kept.get("doi") == work.get("doi")
    crossref = {"DOI": "10.1/x", "title": ["T"], "author": [{"given": "A", "family": "B"}]}
    assert paper_without_people(crossref) == {"DOI": "10.1/x", "title": ["T"]}


def test_a_follow_up_paper_event_keeps_no_author_or_abstract():
    record = _europepmc()
    citing = SourceRecord(
        "europepmc",
        f"MED:{record['pmid']}",
        "https://europepmc.org/x",
        record,
        datetime(2026, 11, 17, tzinfo=UTC),
    )
    event = follow_up_event(citing, 0.9)
    assert event is not None and not keys_found(event.raw_payload, PAPER_KEYS)


def test_any_payload_loses_a_registry_s_person_keys_wherever_they_are():
    partial = {"study": {"contactsLocationsModule": {"overallOfficials": [{"name": "P"}]}}}
    assert not keys_found(payload_without_people(partial), REGISTRY_PERSON_KEYS)
    assert emails_in_text({"a": ["write to x.y@example.org"], "b": "none"}) == 1


def test_stored_paper_records_are_stripped_once_and_counted(session: Session):
    claim = _claim("drug-q-for-melanoma")
    session.add(claim)
    session.flush()
    session.add(
        EvidenceEvent(
            claim_id=claim.id,
            type="followup_paper",
            event_date=date(2020, 1, 2),
            source_name="europepmc",
            source_url="https://europepmc.org/x",
            external_id="MED:1",
            summary="A paper.",
            confidence=0.9,
            raw_payload=_europepmc(),
            fetched_at=datetime(2026, 11, 17, tzinfo=UTC),
            dedupe_key="followup:MED:1",
        )
    )
    session.flush()
    counted = strip_papers(session, apply=False)
    assert counted.changed[("evidence_event", "europepmc")] == 1
    assert counted.before[("evidence_event", "europepmc", "authorString")] == 1
    applied = strip_papers(session, apply=True)
    assert not +applied.after
    session.expire_all()
    held = session.scalars(select(EvidenceEvent.raw_payload)).one()
    assert not keys_found(held, PAPER_KEYS)
    assert strip_papers(session, apply=True).changed[("evidence_event", "europepmc")] == 0


def test_a_store_file_with_a_paper_s_authors_is_found(tmp_path: Path):
    path = tmp_path / "s.sqlite"
    db = sqlite3.connect(path)
    db.executescript((STORE / "schema.sql").read_text())
    db.execute(
        "INSERT INTO run (id, writer, device, commit_sha, registered_at)"
        " VALUES ('r', 'migration', 'd', 'abc1234', '2026-11-17T00:00:00.000000+00:00')"
    )
    body = json.dumps({"title": "T", "authorString": "A B, C D."})
    db.execute(
        "INSERT INTO payload (sha256, bytes, body, added_run) VALUES (?, ?, ?, 'r')",
        ("a" * 64, len(body), body),
    )
    db.commit()
    assert prove_file(path) == {"payload row: authorString": 1}
