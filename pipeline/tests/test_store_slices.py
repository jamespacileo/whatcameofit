"""The trial target set in slices: the plan, its stages, coverage, and a slice pushed after
the base load sending nothing the load held."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from test_store_records import STORE, _world
from thenwhat.db.models import RegistryTrial, TrialPaper, WorkEntry
from thenwhat.store.build import build
from thenwhat.store.push import increment
from thenwhat.store.slices import (
    GROUPS,
    Plan,
    SliceRefused,
    coverage,
    group_of,
    plan,
    pubmed_stage,
    record_stage,
    slice_records,
)

NOW = datetime(2026, 11, 18, tzinfo=UTC)
TODAY = NOW.date()
RULE = RegistryTrial.external_id.in_(["NCT01234567", "NCT07654321"])


def test_a_trial_s_group_is_read_from_its_record():
    year, today = 2026, TODAY
    assert group_of("COMPLETED", "2026-03", True, None, year=year, today=today) == GROUPS[0]
    assert group_of("TERMINATED", "2026-01-02", False, None, year=year, today=today) == GROUPS[1]
    assert group_of("RECRUITING", "2027-01", True, None, year=year, today=today) == GROUPS[2]
    assert (
        group_of("RECRUITING", None, False, date(2026, 5, 1), year=year, today=today) == GROUPS[3]
    )
    assert (
        group_of("RECRUITING", None, False, date(2024, 5, 1), year=year, today=today) == GROUPS[4]
    )


def test_a_plan_keeps_its_slices_and_puts_new_trials_after_them(session: Session, tmp_path: Path):
    _world(session)
    first = plan(session, RULE, name="test-set", year=2025, today=TODAY, size=1)
    assert [one.trials for one in first.slices] == [
        ["clinicaltrials.gov|NCT01234567"],
        ["clinicaltrials.gov|NCT07654321"],
    ]
    assert first.slices[0].group == GROUPS[0]  # terminated in 2025, results posted
    path = tmp_path / "plan.json"
    first.write(path)
    session.add(
        RegistryTrial(
            registry_name="clinicaltrials.gov",
            external_id="NCT00000002",
            title="New",
            conditions=[],
            interventions=[],
            phases=[],
            overall_status="RECRUITING",
            raw_payload={"protocolSection": {}},
            fetched_at=NOW,
        )
    )
    session.flush()
    wider = RegistryTrial.external_id.in_(["NCT01234567", "NCT07654321", "NCT00000002"])
    again = plan(
        session, wider, name="test-set", year=2025, today=TODAY, before=Plan.read(path), size=1
    )
    assert [one.number for one in again.slices] == [1, 2, 3]
    assert again.slices[2].trials == ["clinicaltrials.gov|NCT00000002"]


def test_the_record_and_pubmed_stages_say_what_is_held(session: Session):
    _world(session)
    made = plan(session, RULE, name="test-set", year=2025, today=TODAY)
    ended, active = made.slices  # one trial each: ended with results, and under way
    for one in made.slices:
        record_stage(session, one, NOW)
    assert ended.counts == {"trials": 1, "with_results": 1} and "record" in ended.done
    trial = session.scalars(
        select(RegistryTrial).where(RegistryTrial.external_id == "NCT01234567")
    ).one()
    session.add(
        WorkEntry(
            record_kind="registry_trial",
            record_id=trial.id,
            step="pubmed_papers",
            step_version=1,
            outcome="done",
            attempts=1,
            requests_used=1,
            fingerprint="p",
            last_attempt_at=NOW,
        )
    )
    session.add(
        TrialPaper(
            registry_trial_id=trial.id,
            source_name="pubmed",
            pubmed_id="1",
            raw_payload={"pmid": "1"},
            fetched_at=NOW,
        )
    )
    session.flush()
    # PubMed was asked about the first slice's trial, not the second's: that one waits.
    assert pubmed_stage(session, ended, NOW) and "pubmed_papers" in ended.done
    assert ended.due() == "registry_papers"  # the first stage not done, in order
    assert ended.counts["pubmed_asked"] == 1 and ended.counts["pubmed_found"] == 1
    assert not pubmed_stage(session, active, NOW) and "pubmed_papers" not in active.done
    counted = coverage(made).total
    assert counted["trials"] == 2 and counted["trials pubmed_papers"] == 1
    assert counted["trials in_store"] == 0


def test_a_slice_with_a_trial_not_stored_is_refused(session: Session):
    _world(session)
    made = plan(session, RULE, name="test-set", year=2025, today=TODAY)
    made.slices[0].trials.append("clinicaltrials.gov|NCT99999999")
    with pytest.raises(SliceRefused, match="not stored"):
        record_stage(session, made.slices[0], NOW)


def test_a_slice_after_the_base_load_sends_its_trials_and_nothing_the_load_held(
    session: Session, tmp_path: Path
):
    """The base load is the hot file: the push state a build seeds holds the hot tier's
    records only, so a slice sends its trials, their payloads, papers and state, and no
    record the load already put in D1 (a paper's record is hot)."""
    _world(session)
    file, payloads = tmp_path / "store.sqlite", tmp_path / "payloads"
    report = build(session, file, payloads=payloads, store_sql=STORE, now=NOW)
    assert "registry_trial\tclinicaltrials.gov|NCT01234567" not in report.hot_state
    assert "registry_trial\tclinicaltrials.gov|NCT01234567" in report.state
    trial = session.scalars(
        select(RegistryTrial).where(RegistryTrial.external_id == "NCT01234567")
    ).one()
    session.add(
        TrialPaper(
            registry_trial_id=trial.id,
            source_name="pubmed",
            pubmed_id="77",
            raw_payload={"pmid": "77", "authorString": "A B.", "abstract": "Text."},
            fetched_at=NOW,
        )
    )
    session.flush()
    one_trial = RegistryTrial.external_id == "NCT01234567"
    made = plan(session, one_trial, name="test-set", year=2025, today=TODAY)
    (one,) = made.slices
    record_stage(session, one, NOW)
    records, _ = slice_records(session, one, rule="test-set", year=2025)
    sent = increment(records, report.hot_state, actions=False).records
    assert {record.kind for record in sent} == {
        "registry_trial",
        "payload",
        "trial_paper",
        "trial_slice",
    }
    # The paper keeps its byline and loses its abstract (docs/adr/0011).
    (paper,) = [record for record in sent if record.kind == "trial_paper"]
    (body,) = [
        r.body for r in sent if r.kind == "payload" and r.key == paper.body["payload_sha256"]
    ]
    assert "abstract" not in body["body"] and "authorString" in body["body"]
    # A store loaded afresh: the slice is taken as not in it, and pushed again.
    one.done["in_store"], one.store = "2026-11-18T00:00:00.000000+00:00", "old-build"
    one.forget_store()
    assert "in_store" not in one.done and one.store == ""


def test_slices_commands_refuse_a_stage_they_do_not_work():
    from typer.testing import CliRunner

    from thenwhat.cli import app

    run = CliRunner().invoke(app, ["backfill", "slices", "run", "--stage", "page"])
    assert run.exit_code == 1 and "--stage is one of" in run.output
    mark = CliRunner().invoke(app, ["backfill", "slices", "mark", "--stage", "record", "1"])
    assert mark.exit_code == 1 and "Only the page stage" in mark.output


def test_a_build_gathers_a_trial_s_papers_without_their_abstracts(session: Session):
    from thenwhat.store.gather import gather

    _world(session)
    trial = session.scalars(
        select(RegistryTrial).where(RegistryTrial.external_id == "NCT01234567")
    ).one()
    session.add(
        TrialPaper(
            registry_trial_id=trial.id,
            source_name="pubmed",
            pubmed_id="88",
            raw_payload={"pmid": "88", "authorString": "A B.", "abstract": "Text."},
            fetched_at=NOW,
        )
    )
    session.flush()
    records = gather(session).records
    (paper,) = [r for r in records if r.kind == "trial_paper"]
    assert paper.key == "clinicaltrials.gov|NCT01234567|pubmed|88"
    (payload,) = [
        r for r in records if r.kind == "payload" and r.key == paper.body["payload_sha256"]
    ]
    assert "abstract" not in payload.body["body"] and "authorString" in payload.body["body"]
