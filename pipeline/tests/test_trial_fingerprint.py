import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest
from typer.testing import CliRunner

from thenwhat.backfill.trial_fingerprint import AcronymContext, fingerprint_of
from thenwhat.backfill.trial_terms import words_of
from thenwhat.cli import app
from thenwhat.measure.files import days_held, read_day


@pytest.mark.parametrize(
    ("acronym", "reason"),
    [
        ("HOPE", "word_or_name"),
        ("VOLGA", "word_or_name"),
        ("OSAKA", "word_or_name"),
        ("chair-soccer", "word_or_name"),
        ("NSCLC", "condition_term"),
        ("AB-12", "too_short"),
        ("CXA-12", None),
        ("EM-MAT", None),
        ("ANTHIR", None),
        ("KEYNOTE-789", None),
        ("CXD-123", "too_many_other_titles"),
    ],
)
def test_acronym_fit(acronym, reason):
    context = AcronymContext(
        {("hope",), ("chair",), ("soccer",), ("keynote",), ("em",), ("mat",)},
        {("nsclc",)},
        {words_of("CXD-123"): 4},
        max_other_titles=3,
    )
    terms = fingerprint_of(
        "NCT09999999",
        interventions=[],
        protocol={"identificationModule": {"acronym": acronym}},
        lead_sponsor_name=None,
        context=context,
    )
    assert terms[1].value == acronym
    assert terms[1].reason == reason
    assert terms[1].fit is (reason is None)


def test_stored_identifiers_codes_and_verified_names_are_rebuilt():
    protocol = {
        "identificationModule": {
            "orgStudyIdInfo": {"id": "ACME-002"},
            "secondaryIdInfos": [{"id": "XYZ", "type": "OTHER"}],
        }
    }
    context = AcronymContext(set(), set(), {}, 3)
    interventions = [{"type": "DRUG", "name": "Exavir", "otherNames": []}]
    before = fingerprint_of(
        "NCT09999999",
        interventions=interventions,
        protocol=protocol,
        lead_sponsor_name="Example Labs",
        context=context,
    )
    assert [term.value for term in before if term.fit] == ["NCT09999999"]
    assert [(term.kind, term.value, term.identifier_type) for term in before if not term.fit] == [
        ("sponsor_identifier", "ACME-002", None),
        ("secondary_identifier", "XYZ", "OTHER"),
        ("lead_sponsor", "Example Labs", None),
    ]

    interventions[0]["otherNames"] = ["TARA-002", "tara002", "Examplevir"]
    protocol["sponsorCollaboratorsModule"] = {"responsibleParty": {"type": "SPONSOR_INVESTIGATOR"}}
    after = fingerprint_of(
        "NCT09999999",
        interventions=interventions,
        protocol=protocol,
        lead_sponsor_name="Example Person",
        context=context,
        telling_names={("examplevir",)},
    )
    assert [term.value for term in after if term.fit] == ["NCT09999999", "TARA-002", "Examplevir"]
    assert "Example Person" not in [term.value for term in after]


def _make_store(path: Path, *, with_trials: bool) -> None:
    with closing(sqlite3.connect(path)) as db, db:
        db.executescript("""
            CREATE TABLE registry_trial (
                id INTEGER, external_id TEXT, registry_name TEXT, acronym TEXT, title TEXT,
                conditions TEXT, interventions TEXT, lead_sponsor_name TEXT, payload_sha256 TEXT
            );
            CREATE TABLE payload (sha256 TEXT, body TEXT);
        """)
        if with_trials:
            records = [
                (1, "Own trial CXZ-123", "Own trial CXZ-123", [], "CXZ-123"),
                (2, "Another trial", "Another trial CXZ-123", ["NSCLC"], None),
                (3, "", "", [], "NSCLC"),
                (4, "Own trial ABC-999", "Own trial ABC-999", [], "ABC-999"),
            ]
            for trial_id, title, official, conditions, acronym in records:
                key = str(trial_id)
                payload = {
                    "protocolSection": {
                        "identificationModule": {
                            "officialTitle": official,
                            "acronym": acronym,
                        }
                    }
                }
                db.execute("INSERT INTO payload VALUES (?, ?)", (key, json.dumps(payload)))
                db.execute(
                    "INSERT INTO registry_trial VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        trial_id,
                        f"NCT{trial_id:08}",
                        "clinicaltrials.gov",
                        acronym,
                        title,
                        json.dumps(conditions),
                        "[]",
                        None,
                        key,
                    ),
                )


def test_fingerprints_command_counts_other_titles_and_records_metrics(tmp_path):
    store = tmp_path / "bulk.sqlite"
    _make_store(store, with_trials=True)
    word_list = tmp_path / "words.txt"
    word_list.write_text("ordinary\n", encoding="utf-8")
    output = tmp_path / "run"
    result = CliRunner().invoke(
        app,
        [
            "backfill",
            "trial-fingerprints",
            str(store),
            str(output),
            "--word-list",
            str(word_list),
            "--max-other-titles",
            "0",
        ],
    )
    assert result.exit_code == 0, result.output
    records = [
        json.loads(line)
        for line in (output / "fingerprints.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert records[0]["terms"][1]["reason"] == "too_many_other_titles"
    assert records[2]["terms"][1]["reason"] == "condition_term"
    assert records[3]["terms"][1]["fit"]
    summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
    assert summary["fingerprints"] == 4
    assert summary["registry_number_only"] == {"all": 3}
    spans = list(read_day(output, days_held(output)[0]))
    assert sum(span.rows_written for span in spans) == 4
    assert all(span.outcome == "done" for span in spans)


def test_empty_store_refused_and_failure_recorded(tmp_path):
    store = tmp_path / "bulk.sqlite"
    _make_store(store, with_trials=False)
    word_list = tmp_path / "words.txt"
    word_list.write_text("ordinary\n", encoding="utf-8")
    output = tmp_path / "run"
    result = CliRunner().invoke(
        app,
        ["backfill", "trial-fingerprints", str(store), str(output), "--word-list", str(word_list)],
    )
    assert result.exit_code == 1
    assert "no registry trials" in result.output
    assert not (output / "fingerprints.jsonl").exists()
    spans = list(read_day(output, days_held(output)[0]))
    assert any(span.step == "trial_fingerprint.run" and span.outcome == "failed" for span in spans)
