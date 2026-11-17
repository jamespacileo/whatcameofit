"""People removed from the registry records Postgres already holds, and the proof that a
database or a store file holds none (`sources/people.py` says what a person field is).

Two tables hold a whole ClinicalTrials.gov record: `evidence_event.raw_payload`, for an
event read from a trial, and `registry_trial.raw_payload`. No other table does: a trial
read keeps readings, a source record a paper's, term's or organisation's own record,
and leads, shares and ledger entries keep no payload. `http_cache` holds raw answers
too, but stays on the device and is never migrated; `thenwhat cache-prune` empties it.
"""

import json
import sqlite3
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from thenwhat.db.models import EvidenceEvent, PaperRecord, RegistryTrial, TrialPaper
from thenwhat.sources.people import (
    CONTACT_KEYS,
    FIELDS,
    PAPER_KEYS,
    REGISTRY_PERSON_KEYS,
    emails_in_text,
    is_study,
    keys_found,
    payload_without_people,
    people_in,
    without_people,
)

PAGE = 1_000
TABLES = (EvidenceEvent, RegistryTrial)


@dataclass
class Stripped:
    """By table: rows read, rows holding a person, and by field the rows naming one
    before and after."""

    rows: Counter[str] = field(default_factory=Counter)
    changed: Counter[str] = field(default_factory=Counter)
    before: dict[str, Counter[str]] = field(default_factory=dict)
    after: dict[str, Counter[str]] = field(default_factory=dict)


def strip(
    session: Session, *, apply: bool, on_page: Callable[[str, int], None] = lambda *_: None
) -> Stripped:
    """Count the people in each stored registry record and, with `apply`, write each record
    without them, a page at a time, committing each page. Running it again finds none."""
    report = Stripped()
    for model in TABLES:
        name = model.__tablename__
        report.before[name], report.after[name] = Counter(), Counter()
        last = 0
        while True:
            page = session.execute(
                select(model.id, model.raw_payload)
                .where(model.id > last)
                .order_by(model.id)
                .limit(PAGE)
            ).all()
            if not page:
                break
            for row_id, payload in page:
                last = row_id
                if not is_study(payload):
                    continue
                report.rows[name] += 1
                found = people_in(payload)
                report.before[name].update(found)
                if not found:
                    continue
                kept = without_people(payload)
                report.after[name].update(people_in(kept))
                report.changed[name] += 1
                if apply:
                    session.execute(
                        update(model).where(model.id == row_id).values(raw_payload=kept)
                    )
            if apply:
                session.commit()
            on_page(name, last)
    return report


# Tables that hold a literature record, with its column and what names its source.
PAPER_TABLES = (
    (EvidenceEvent, "raw_payload"),
    (PaperRecord, "payload"),
    (TrialPaper, "raw_payload"),
)


@dataclass
class PapersStripped:
    """By table and source: records read, records changed, and by field the records
    holding it before and after."""

    rows: Counter[tuple[str, str]] = field(default_factory=Counter)
    changed: Counter[tuple[str, str]] = field(default_factory=Counter)
    before: Counter[tuple[str, str, str]] = field(default_factory=Counter)
    after: Counter[tuple[str, str, str]] = field(default_factory=Counter)


def strip_papers(session: Session, *, apply: bool) -> PapersStripped:
    """Count the authors, abstracts and person keys in every stored payload that is not a
    registry study (a follow-up paper's record, a retraction notice, a paper's or a trial
    paper's record) and, with `apply`, write each without them, a page at a time."""
    report = PapersStripped()
    keys = PAPER_KEYS | REGISTRY_PERSON_KEYS | CONTACT_KEYS
    for model, column in PAPER_TABLES:
        name = model.__tablename__
        value = getattr(model, column)
        last = 0
        while True:
            page = session.execute(
                select(model.id, model.source_name, value)
                .where(model.id > last)
                .order_by(model.id)
                .limit(PAGE)
            ).all()
            if not page:
                break
            for row_id, source, payload in page:
                last = row_id
                if payload is None or is_study(payload):
                    continue
                report.rows[(name, source)] += 1
                found = keys_found(payload, keys)
                report.before.update((name, source, key) for key in found)
                if not found:
                    continue
                kept = payload_without_people(payload)
                report.after.update((name, source, key) for key in keys_found(kept, keys))
                report.changed[(name, source)] += 1
                if apply:
                    session.execute(update(model).where(model.id == row_id).values({column: kept}))
            if apply:
                session.commit()
    return report


def emails_left(session: Session) -> Counter[str]:
    """How many stored registry studies, once stripped, still hold an email address in
    some text (a description, a criterion, a citation): counted, not changed."""
    found: Counter[str] = Counter()
    last = 0
    while True:
        page = session.execute(
            select(EvidenceEvent.id, EvidenceEvent.raw_payload)
            .where(EvidenceEvent.id > last)
            .order_by(EvidenceEvent.id)
            .limit(PAGE)
        ).all()
        if not page:
            break
        for row_id, payload in page:
            last = row_id
            if is_study(payload):
                found["studies"] += 1
                if emails_in_text(without_people(payload)):
                    found["with an email in a text"] += 1
    return found


# The proof over Postgres: every count is 0 once the records are stripped.
PROOF_SQL = Path(__file__).with_name("no_people.sql")


def prove_file(path: Path) -> Counter[str]:
    """The people a store file names, by field: in each payload row's body, and a trial's
    lead sponsor's name where the sponsor is a person. Empty when there are none."""
    found: Counter[str] = Counter()
    db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        for (body,) in db.execute("SELECT body FROM payload WHERE body IS NOT NULL"):
            found.update(f"payload row: {f}" for f in _people(_json(body)))
        # A registry trial's own columns: its lead sponsor's name when the sponsor is a person.
        for (count,) in db.execute(
            "SELECT count(*) FROM registry_trial WHERE lead_sponsor_name IS NOT NULL"
            " AND sponsor_class IN ('INDIV', 'INDIVIDUAL')"
        ):
            if count:
                found["registry_trial: person lead sponsor's name"] += count
    finally:
        db.close()
    return found


def prove_file_objects(payloads: Path) -> Counter[str]:
    """The people the payload objects in a folder name, by field."""
    found: Counter[str] = Counter()
    for one in payloads.rglob("*"):
        if one.is_file():
            found.update(f"payload object: {f}" for f in _people(_json(one.read_text())))
    return found


def _people(payload: Any) -> set[str]:
    """What a payload names a person in: a study's fields, else any person key."""
    if is_study(payload):
        return people_in(payload) | keys_found(payload, PAPER_KEYS - {"abstract"})
    return keys_found(payload, PAPER_KEYS | REGISTRY_PERSON_KEYS | CONTACT_KEYS)


def _json(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return None


__all__ = [
    "FIELDS",
    "PROOF_SQL",
    "PapersStripped",
    "Stripped",
    "emails_left",
    "prove_file",
    "prove_file_objects",
    "strip",
    "strip_papers",
]
