"""The approach set by rule from the registry's intervention types: the pure rule, who
set an approach on each way in, then the rule applied to a claim."""

import csv
import io
import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from thenwhat.claims.approach_rule import (
    NOT_LISTED,
    TYPE_APPROACHES,
    TYPE_NOT_MAPPED,
    TYPES_DISAGREE,
    apply_rule,
    approach_from_registry,
)
from thenwhat.claims.csv_import import import_csv
from thenwhat.claims.entry import add_claim, edit_claim
from thenwhat.claims.verticals import APPROACHES
from thenwhat.cli import app
from thenwhat.db.models import Claim, Entity, EntityMatch, EvidenceEvent
from thenwhat.domain import Decider, EventType, ReviewState
from thenwhat.seed.load import load_seed
from thenwhat.terms.kinds import REGISTRY_LISTS_TYPE

NOW = datetime(2026, 11, 17, tzinfo=UTC)
SEED = Path(__file__).resolve().parents[2] / "data" / "seed" / "tooth-regrowth-usag1.json"


def listed(kind: str, trials: int) -> dict[str, Any]:
    return {"code": REGISTRY_LISTS_TYPE, "type": kind, "trials": trials}


# --- the pure rule ---------------------------------------------------------------------


def test_one_mapped_type_gives_its_approach_and_basis():
    answer = approach_from_registry([listed("DRUG", 3)])

    assert answer.approach == "drug"
    assert answer.basis == {"code": REGISTRY_LISTS_TYPE, "type": "DRUG", "trials": 3}
    assert answer.reason is None


def test_types_that_do_not_agree_give_none():
    answer = approach_from_registry([listed("DRUG", 2), listed("BIOLOGICAL", 1)])

    assert (answer.approach, answer.basis, answer.reason) == (None, None, TYPES_DISAGREE)
    assert answer.types == (("DRUG", 2), ("BIOLOGICAL", 1))


def test_a_type_the_table_does_not_map_gives_none():
    answer = approach_from_registry([listed("BIOLOGICAL", 4)])

    assert (answer.approach, answer.reason) == (None, TYPE_NOT_MAPPED)


def test_no_type_found_gives_none():
    assert approach_from_registry([]).reason == NOT_LISTED


def test_every_mapped_approach_is_configured():
    assert set(TYPE_APPROACHES.values()) <= set(APPROACHES)


# --- who set an approach -----------------------------------------------------------------


def new_claim(session: Session, slug: str = "ex1-for-gout", approach: str | None = None) -> Claim:
    return add_claim(
        session,
        slug=slug,
        headline="Drug eases gout",
        vertical="bones-joints-and-muscles",
        intervention="EX-1",
        indication="Gout",
        approach=approach,
    )


def test_an_approach_entered_with_the_claim_is_a_persons(session: Session):
    claim = new_claim(session, approach="vaccine")

    assert (claim.approach_decided_by, claim.approach_basis) == (Decider.HUMAN, None)


def test_a_claim_entered_with_no_approach_records_nobody(session: Session):
    assert new_claim(session).approach_decided_by is None


def test_an_edited_approach_is_a_persons_and_clearing_it_clears_the_record(session: Session):
    claim = new_claim(session)
    claim.approach, claim.approach_decided_by = "drug", Decider.RULE
    claim.approach_basis = listed("DRUG", 1)

    edit_claim(session, claim.slug, approach="vaccine")
    assert (claim.approach, claim.approach_decided_by, claim.approach_basis) == (
        "vaccine",
        Decider.HUMAN,
        None,
    )

    edit_claim(session, claim.slug, approach="")
    assert (claim.approach, claim.approach_decided_by, claim.approach_basis) == (None, None, None)


def test_a_csv_rows_approach_is_a_persons(session: Session):
    columns = {
        "slug": "ex2-for-gout",
        "headline": "Gene therapy eases gout",
        "vertical": "bones-joints-and-muscles",
        "intervention": "EX-2",
        "indication": "Gout",
        "summary": "",
        "article_url": "https://example.org/gout",
        "outlet": "Example",
        "article_title": "Gene therapy eases gout",
        "published_date": "2024-01-02",
        "promise": "",
        "promise_date": "",
        "approach": "gene-therapy",
    }
    text = io.StringIO()
    writer = csv.DictWriter(text, fieldnames=list(columns))
    writer.writeheader()
    writer.writerow(columns)

    import_csv(session, text.getvalue().splitlines())

    claim = session.scalars(select(Claim).where(Claim.slug == "ex2-for-gout")).one()
    assert (claim.approach, claim.approach_decided_by) == ("gene-therapy", Decider.HUMAN)


def test_the_seeds_approach_is_the_seeds(session: Session):
    load_seed(session, json.loads(SEED.read_text()), now=NOW)

    seeded = session.scalars(select(Claim).where(Claim.approach.is_not(None))).all()
    assert seeded
    assert {claim.approach_decided_by for claim in seeded} == {Decider.SEED}


# --- the rule applied to a claim -------------------------------------------------------


def trial(number: str, *interventions: tuple[str, str]) -> dict[str, Any]:
    return {
        "protocolSection": {
            "identificationModule": {"nctId": number},
            "armsInterventionsModule": {
                "interventions": [{"type": kind, "name": name} for kind, name in interventions]
            },
        }
    }


def approve_trial(session: Session, claim: Claim, payload: dict[str, Any]) -> EntityMatch:
    number = payload["protocolSection"]["identificationModule"]["nctId"]
    entity = session.scalars(select(Entity).where(Entity.claim_id == claim.id)).one()
    match = EntityMatch(
        entity_id=entity.id,
        source_name="clinicaltrials.gov",
        external_id=number,
        score=0.9,
        review_state=ReviewState.APPROVED,
        reviewed_at=NOW,
        reviewed_by=Decider.RULE,
    )
    session.add(match)
    session.flush()
    session.add(
        EvidenceEvent(
            claim_id=claim.id,
            entity_match_id=match.id,
            type=EventType.TRIAL_REGISTERED,
            event_date=date(2024, 7, 1),
            source_name="clinicaltrials.gov",
            source_url=f"https://clinicaltrials.gov/study/{number}",
            external_id=number,
            summary="Trial registered.",
            confidence=1.0,
            raw_payload=payload,
            fetched_at=NOW,
            dedupe_key=f"registered:{number}",
        )
    )
    session.flush()
    return match


def test_the_rule_fills_an_empty_approach_and_ignores_the_comparator(session: Session):
    claim = new_claim(session)
    for number in ("NCT00000001", "NCT00000002", "NCT00000003"):
        approve_trial(session, claim, trial(number, ("DRUG", "ex-1"), ("OTHER", "Placebo")))

    apply_rule(session, claim)

    assert (claim.approach, claim.approach_decided_by) == ("drug", Decider.RULE)
    assert claim.approach_basis == listed("DRUG", 3)


def test_the_rule_leaves_an_empty_approach_when_no_trial_names_the_intervention(
    session: Session,
):
    claim = new_claim(session)
    approve_trial(session, claim, trial("NCT00000001", ("DRUG", "Another drug")))

    answer = apply_rule(session, claim)

    assert answer.reason == NOT_LISTED
    assert (claim.approach, claim.approach_decided_by, claim.approach_basis) == (None, None, None)


def test_the_rule_reads_only_approved_trials(session: Session):
    claim = new_claim(session)
    match = approve_trial(session, claim, trial("NCT00000001", ("DRUG", "EX-1")))
    match.review_state = ReviewState.PENDING
    match.reviewed_at = match.reviewed_by = None

    apply_rule(session, claim)

    assert claim.approach is None


def test_editor_who_commits_during_a_fetch_keeps_ownership(engine):
    from sqlalchemy import delete

    with Session(engine) as setup:
        claim = new_claim(setup, slug="two-session-owner")
        approve_trial(setup, claim, trial("NCT11111111", ("DRUG", "EX-1")))
        claim_id = claim.id
        setup.commit()
    try:
        with Session(engine) as fetch, Session(engine) as editor:
            held = fetch.get(Claim, claim_id)
            assert held is not None and held.approach is None
            edited = editor.get(Claim, claim_id)
            assert edited is not None
            edited.approach, edited.approach_decided_by = "gene-therapy", Decider.HUMAN
            editor.commit()
            assert apply_rule(fetch, held).approach == "drug"
            fetch.commit()
        with Session(engine) as check:
            final = check.get(Claim, claim_id)
            assert final is not None
            assert (final.approach, final.approach_decided_by, final.approach_basis) == (
                "gene-therapy",
                Decider.HUMAN,
                None,
            )
    finally:
        with Session(engine) as cleanup:
            cleanup.execute(delete(EvidenceEvent).where(EvidenceEvent.claim_id == claim_id))
            cleanup.execute(
                delete(EntityMatch).where(
                    EntityMatch.entity_id.in_(select(Entity.id).where(Entity.claim_id == claim_id))
                )
            )
            cleanup.execute(delete(Entity).where(Entity.claim_id == claim_id))
            cleanup.execute(delete(Claim).where(Claim.id == claim_id))
            cleanup.commit()


def test_the_rule_keeps_an_approach_a_person_set(session: Session):
    claim = new_claim(session, approach="gene-therapy")
    approve_trial(session, claim, trial("NCT00000001", ("DRUG", "EX-1")))

    apply_rule(session, claim)

    assert (claim.approach, claim.approach_decided_by) == ("gene-therapy", Decider.HUMAN)


def test_the_rule_keeps_an_approach_stored_with_no_record_of_who_set_it(session: Session):
    claim = new_claim(session)
    claim.approach = "vaccine"
    approve_trial(session, claim, trial("NCT00000001", ("DRUG", "EX-1")))

    apply_rule(session, claim)

    assert (claim.approach, claim.approach_decided_by) == ("vaccine", None)


def test_a_rule_set_approach_follows_the_trials(session: Session):
    claim = new_claim(session)
    approve_trial(session, claim, trial("NCT00000001", ("DRUG", "EX-1")))
    approve_trial(session, claim, trial("NCT00000002", ("DRUG", "EX-1")))
    apply_rule(session, claim)

    approve_trial(session, claim, trial("NCT00000003", ("DRUG", "EX-1")))
    apply_rule(session, claim)
    assert (claim.approach, claim.approach_basis) == ("drug", listed("DRUG", 3))

    approve_trial(session, claim, trial("NCT00000004", ("BIOLOGICAL", "EX-1")))
    apply_rule(session, claim)
    assert (claim.approach, claim.approach_decided_by, claim.approach_basis) == (None, None, None)


def test_a_basis_without_a_rule_is_refused(session: Session):
    claim = new_claim(session, approach="drug")
    claim.approach_basis = listed("DRUG", 1)

    with pytest.raises(Exception, match="approach_basis_is_a_rules"):
        session.flush()


# --- the command ---------------------------------------------------------------------


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)

    def invoke(*arguments: str) -> Result:
        return CliRunner().invoke(app, ["claim", "approaches", *arguments], env={"COLUMNS": "300"})

    return invoke


def test_the_command_sets_approaches_and_lists_what_it_left(run, session: Session):
    filled = new_claim(session)
    approve_trial(session, filled, trial("NCT00000001", ("DRUG", "EX-1")))
    mixed = add_claim(
        session,
        slug="ex3-for-gout",
        headline="Cells ease gout",
        vertical="bones-joints-and-muscles",
        intervention="EX-3",
        indication="Gout",
    )
    approve_trial(session, mixed, trial("NCT00000005", ("BIOLOGICAL", "EX-3")))
    kept = add_claim(
        session,
        slug="ex4-for-gout",
        headline="Device eases gout",
        vertical="bones-joints-and-muscles",
        intervention="EX-4",
        indication="Gout",
        approach="drug",
    )
    approve_trial(session, kept, trial("NCT00000006", ("DEVICE", "EX-4")))

    result = run("--unset")

    assert result.exit_code == 0, result.output
    assert "3 claims: 1 given an approach, 0 updated, 0 cleared, 1 unchanged." in result.output
    assert "The rule answers for 1 of them and agrees with 0." in result.output
    assert "ex4-for-gout: stored drug, the rule answers device" in result.output
    assert (
        "ex3-for-gout: the table maps this registry type to no approach (BIOLOGICAL in 1 trial)"
        in result.output
    )
    assert (filled.approach, kept.approach, mixed.approach) == ("drug", "drug", None)


def test_a_dry_run_writes_nothing(run, session: Session):
    claim = new_claim(session)
    approve_trial(session, claim, trial("NCT00000001", ("DRUG", "EX-1")))

    result = run("--dry-run")

    assert result.exit_code == 0, result.output
    assert "1 claim: 1 would be given an approach" in result.output
    assert (claim.approach, claim.approach_decided_by, claim.approach_basis) == (None, None, None)


def test_the_command_refuses_an_unknown_claim(run):
    result = run("no-such-claim")

    assert result.exit_code == 1
    assert "no-such-claim" in result.output
