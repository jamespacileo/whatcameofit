"""The whole tracker built into one store file, as it is filled and restored in bulk."""

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from test_store_records import STORE, _world
from thenwhat.db.models import RegistryTrial
from thenwhat.store.build import build
from thenwhat.store.form import payload_of


def test_the_whole_database_builds_into_one_store_file(session: Session, tmp_path: Path):
    world = _world(session)
    # A trial loaded before people's names were removed: its sponsor is a person.
    trial = session.scalars(
        select(RegistryTrial).where(RegistryTrial.external_id == "NCT07654321")
    ).one()
    trial.raw_payload = {
        "protocolSection": {
            "sponsorCollaboratorsModule": {
                "leadSponsor": {"name": "Dr Jane Doe", "class": "INDIV"},
                "responsibleParty": {
                    "type": "SPONSOR_INVESTIGATOR",
                    "investigatorFullName": "Jane Doe",
                },
            }
        }
    }
    trial.lead_sponsor_name = "Dr Jane Doe"
    session.flush()

    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    report = build(
        session, file, payloads=payloads, store_sql=STORE, now=datetime(2026, 11, 17, tzinfo=UTC)
    )

    assert report.size == file.stat().st_size > 0
    assert report.handed["claim"] == 4 and report.added["claim"] == 4
    big = payload_of(world["big_payload"])
    assert (payloads / big.r2_key).read_text() == big.text
    assert report.payload_objects == 1

    db = sqlite3.connect(file)
    # The renamed claim is known by the slug it had; the merged one is archived and was
    # public.
    assert db.execute(
        "SELECT c.slug FROM claim_alias a JOIN claim c ON c.id = a.claim_id"
        " WHERE a.slug = 'drug-zz-for-melanoma'"
    ).fetchone() == ("drug-z-for-melanoma",)
    gone = db.execute(
        "SELECT merged_into IS NOT NULL, archived_at IS NOT NULL, published_at IS NOT NULL"
        " FROM claim WHERE slug = 'drug-x-tablets-for-melanoma'"
    ).fetchone()
    assert gone == (1, 1, 1)
    # No person is named.
    sponsor, held = db.execute(
        "SELECT t.lead_sponsor_name, p.body FROM registry_trial t"
        " JOIN payload p ON p.sha256 = t.payload_sha256 WHERE t.external_id = 'NCT07654321'"
    ).fetchone()
    assert sponsor is None and "Jane Doe" not in held
    assert json.loads(held)["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"] == {
        "class": "INDIV"
    }
    # Nothing staged is left behind.
    assert db.execute("SELECT count(*) FROM stg").fetchone() == (0,)
