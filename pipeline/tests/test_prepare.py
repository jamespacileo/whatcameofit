"""Preparing many claims with `thenwhat prepare`, the rule that decides a read's draft
once it is prepared, and the audit of a prepared batch. The steps themselves are tested
in test_claim_steps.py; here the command runs them on the test session with their
sources faked (claim_support.py). Scenario names are from openspec claim-extraction,
entity-resolution and lead-reading."""

from collections.abc import Generator
from contextlib import contextmanager

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from backfill_support import same_session
from claim_support import (
    NOW,
    Registry,
    Sources,
    drafted_by_a_read,
    new_claim,
    trial,
)
from thenwhat.claims.corrections import rename_intervention
from thenwhat.claims.entry import awaiting_audit, find_claim
from thenwhat.cli import app
from thenwhat.db.models import Entity, LinkLead, SourceArticle
from thenwhat.domain import Decider, OutletKind, ReadOutcome, ReviewState
from thenwhat.extract.retrieve import NotNow
from thenwhat.prepare import decide_prepared_lead_claim
from thenwhat.review.decisions import record_decision


@pytest.fixture
def sources() -> Sources:
    return Sources(Registry([trial("NCT00000001")]))


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch, sources: Sources):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.claim_steps.claim_sources", sources.claim_sources)
    sources.open_session = same_session(session)
    runner = CliRunner()
    # The settings are read for the steps; the database they name is never opened,
    # because the session above stands in for it.
    env = {
        "COLUMNS": "200",
        "DATABASE_URL": "postgresql+psycopg://unused/unused",
        "MATCH_ACCEPT_ABOVE": "0.8",
        "APPROVE_DRAFTS_BY_RULE": "true",
    }
    return lambda *arguments: runner.invoke(app, list(arguments), env=env)


def said(result) -> str:
    return " ".join(result.output.split())


# --- the command -----------------------------------------------------------------------


def test_prepare_works_through_every_step_and_decides_a_reads_draft(run, session: Session):
    """Scenarios: Prepared and named; Unfinished parts of a published claim are completed"""
    new_claim(session, "drafted-one")
    drafted_by_a_read(session, "drafted-one")
    published = new_claim(session, "published-one")
    record_decision(published, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)

    result = run("prepare", "--pending", "--workers", "1")

    assert result.exit_code == 0, result.output
    # Each step says how many claims it did, put off, left needing a fix and failed.
    assert "claim_trials: 2 done, 0 found nothing, 0 put off, 0 need a fix, 0 failed" in said(
        result
    )
    assert (
        "drafted-one: approved by rule, now that its registries have been searched; held off"
        " the site until audited" in said(result)
    )
    drafted = find_claim(session, "drafted-one")
    assert drafted is not None and drafted.review_state is ReviewState.APPROVED
    assert drafted.awaiting_audit_at is not None


def test_prepare_with_no_claims_named_explains_and_exits_1(run):
    result = run("prepare")

    assert result.exit_code == 1
    assert "--pending" in result.output


def test_prepare_of_an_unknown_claim_is_refused(run):
    result = run("prepare", "no-such-claim")

    assert result.exit_code == 1
    assert "no-such-claim" in result.output


def test_an_article_of_a_held_outlet_is_left_for_later_and_its_claim_waits(
    run, session: Session, sources: Sources
):
    """Scenario: Prepare comes to an article of a stopped outlet"""
    new_claim(session, "waiting", "https://held.example.org/a")
    drafted_by_a_read(session, "waiting")

    class Stopped:
        def retrieve(self, url: str):
            raise NotNow(url, "the outlet is stopped", 3600)

    sources.retriever = Stopped()

    result = run("prepare", "waiting", "--workers", "1")

    assert result.exit_code == 0, result.output
    assert "waiting: claim_articles put off until" in said(result)
    # Its registries were still searched, and it is not decided before the article is read.
    assert "claim_trials: 1 done" in said(result)
    claim = find_claim(session, "waiting")
    assert claim is not None and claim.review_state is ReviewState.PENDING


def test_prepare_due_searches_only_the_claims_whose_search_is_due(
    run, session: Session, sources: Sources
):
    """Scenario: Search due after a rename (openspec claims)"""
    for slug in ("not-due", "renamed"):
        claim = new_claim(session, slug)
        record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    assert run("prepare", "--pending", "--workers", "1").exit_code == 0
    renamed = find_claim(session, "renamed")
    assert renamed is not None
    old = session.scalars(select(Entity.name).where(Entity.claim_id == renamed.id)).one()
    rename_intervention(session, "renamed", old, "EX-2 antibody", by=Decider.HUMAN, now=NOW)
    sources.registry.asked.clear()

    result = run("prepare", "--due", "--workers", "1")

    assert result.exit_code == 0, result.output
    assert "EX-2 antibody" in sources.registry.asked
    assert not any("not-due" in term for term in sources.registry.asked)


def test_a_claim_never_searched_is_reported_by_prepare_and_the_audit_list(
    run, session: Session, sources: Sources
):
    """Scenario: A claim with no search record"""
    new_claim(session, "unsearched")
    sources.registry.down = True

    prepared = run("prepare", "--pending", "--workers", "1")
    listed = run("audit", "list")

    assert prepared.exit_code == 0, prepared.output
    assert "unsearched: claim_trials put off until" in said(prepared)
    assert "Never searched: 1 claim(s) have no record of a registry search: unsearched." in (
        said(prepared)
    )
    assert "unsearched never searched" in said(listed)


# --- the rule for drafts and the audit -----------------------------------------------------


def test_a_claim_a_read_drafted_is_approved_by_rule_once_it_is_prepared(session: Session):
    """Scenario: Prepared and named"""
    new_claim(session, "one")
    drafted_by_a_read(session, "one")

    assert decide_prepared_lead_claim(session, "one", now=NOW) is ReviewState.APPROVED

    claim = find_claim(session, "one")
    assert claim is not None
    assert (claim.review_state, claim.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)
    # Held off the site until the audit of its batch clears it.
    assert claim.awaiting_audit_at == NOW
    # Decided once: asking again changes nothing.
    assert decide_prepared_lead_claim(session, "one", now=NOW) is None


def test_a_pending_claim_no_read_drafted_keeps_waiting_for_the_operator(session: Session):
    """Scenario: A claim the operator entered"""
    new_claim(session, "one")

    assert decide_prepared_lead_claim(session, "one", now=NOW) is None

    claim = find_claim(session, "one")
    assert claim is not None and claim.review_state is ReviewState.PENDING


# --- the audit of a prepared batch --------------------------------------------------------


def test_audit_clear_releases_held_claims_and_refuses_one_not_held(run, session: Session):
    """Scenarios: Audit passed, Not awaiting audit"""
    for slug in ("held", "also-held", "never-held"):
        new_claim(session, slug)
    for slug in ("held", "also-held"):
        drafted_by_a_read(session, slug)
        decide_prepared_lead_claim(session, slug, now=NOW)

    refused = run("audit", "clear", "held", "never-held")

    assert refused.exit_code == 1
    assert "never-held" in refused.output and "Nothing was cleared" in refused.output
    assert [claim.slug for claim in awaiting_audit(session)] == ["also-held", "held"]

    cleared = run("audit", "clear", "held")

    assert cleared.exit_code == 0, cleared.output
    assert [claim.slug for claim in awaiting_audit(session)] == ["also-held"]
    listed = run("audit", "list")
    assert "also-held" in listed.output and "1 claim awaits audit" in listed.output


def test_audit_list_shows_reads_that_overlap_a_claim(run, session: Session):
    """Scenarios: A read that overlaps an archived claim, A read that overlaps a claim
    that is not archived"""
    from thenwhat.backfill.link_read import NAMES_OVERLAP
    from thenwhat.claims.entry import archive_claim

    for slug in ("archived-one", "live-one"):
        new_claim(session, slug)
    archive_claim(session, "archived-one", reason="missed trial", now=NOW)
    for number, slug in enumerate(("archived-one", "live-one")):
        session.add(
            LinkLead(
                url=f"https://news.example.org/overlap-{number}",
                url_key=f"news.example.org/overlap-{number}",
                outlet="news.example.org",
                outlet_kind=OutletKind.GENERAL_NEWS,
                title="words a person wrote when sharing the link",
                first_shared_at=NOW,
                read_outcome=ReadOutcome.IDENTITY_UNRESOLVED,
                read_detail=f"X for Y; {NAMES_OVERLAP} {slug}, but the same treatment and"
                " condition were not established",
            )
        )
    session.flush()

    listed = run("audit", "list")

    assert listed.exit_code == 0, listed.output
    said = " ".join(listed.output.split())
    assert "overlaps archived archived-one https://news.example.org/overlap-0" in said
    assert "1 read overlaps an archived claim" in said
    # A read that overlaps a claim that is not archived is never read again, so it is
    # listed apart, for the operator to attach or leave.
    assert "overlaps live-one (pending) https://news.example.org/overlap-1" in said
    assert "1 read overlaps a claim that is not archived and made no claim" in said
    assert said.index("overlap-0") < said.index("overlap-1")


def under_substance(
    session: Session,
    slug: str,
    substance: str,
    *,
    source: str = "gsrs",
    payload: dict | None = None,
) -> None:
    """File the claim's intervention under a substance of the registry of substances,
    or under an ingredient of the source of brands."""
    from thenwhat.db.models import Entity, EntitySubstance
    from thenwhat.domain import EntityType

    claim = find_claim(session, slug)
    assert claim is not None
    entity = session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).one()
    session.add(
        EntitySubstance(
            entity_id=entity.id,
            source_name=source,
            external_id=substance,
            url=f"https://{source}.test/{substance}",
            payload=payload or {"substance": {"_name": "Exampletinib"}},
            fetched_at=NOW,
        )
    )
    session.flush()


def test_a_reads_claim_under_a_live_claims_substance_and_condition_is_rejected(
    session: Session,
):
    """Scenarios: A brand of a live claim's substance, Another form of the substance, The
    other claim is archived"""
    from thenwhat.claims.entry import archive_claim

    new_claim(session, "live-one")
    new_claim(session, "brand-one", "https://news.example.org/brand")
    for slug in ("oral-form", "after-archive"):
        new_claim(session, slug)
    for slug in ("live-one", "brand-one", "oral-form", "after-archive"):
        under_substance(session, slug, "s-1")
    live = find_claim(session, "live-one")
    brand = find_claim(session, "brand-one")
    assert live is not None and brand is not None
    record_decision(live, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    drafted_by_a_read(session, "brand-one")
    [article] = session.scalars(select(SourceArticle).where(SourceArticle.claim_id == brand.id))
    lead = session.scalars(select(LinkLead).where(LinkLead.claim_id == brand.id)).one()
    lead.source_article_id = article.id
    session.flush()

    assert decide_prepared_lead_claim(session, "brand-one", now=NOW) is ReviewState.REJECTED
    # Its article joins the live claim, so it is not lost.
    assert article.claim_id == live.id
    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, live.id)

    # "oral-form" names its intervention in another form: not the same product.
    drafted_by_a_read(session, "oral-form")
    assert decide_prepared_lead_claim(session, "oral-form", now=NOW) is ReviewState.APPROVED

    archive_claim(session, "live-one", reason="missed trial", now=NOW)
    archive_claim(session, "oral-form", reason="audit", now=NOW)
    drafted_by_a_read(session, "after-archive")

    assert decide_prepared_lead_claim(session, "after-archive", now=NOW) is ReviewState.APPROVED


VACCINE = {"propConceptGroup": {"propConcept": [{"propName": "CVX", "propValue": "204"}]}}


VACCINE = {"propConceptGroup": {"propConcept": [{"propName": "CVX", "propValue": "204"}]}}


@pytest.mark.parametrize(
    ("product_codes", "joined"),
    [
        # Two brands of one drug, which RxNorm lists under one ingredient: twins.
        ({"2": {}}, True),
        # Two makers' vaccines filed under one antigen: not one product.
        ({"2": VACCINE}, False),
        # Kept before vaccines were told apart: not known to be no vaccine.
        (None, False),
    ],
)
def test_two_brands_under_one_rxnorm_ingredient_are_twins_only_when_no_vaccine(
    session: Session, product_codes, joined: bool
):
    """Scenario: Two vaccines filed under one antigen"""
    for slug in ("first-vaccine", "second-vaccine"):
        new_claim(session, slug)
        payload: dict = {"substance": {"rxcui": "777", "_name": "examplevirus glycoprotein"}}
        if product_codes is not None:
            payload["product_codes"] = product_codes
        under_substance(session, slug, "777", source="rxnorm", payload=payload)
    first = find_claim(session, "first-vaccine")
    assert first is not None
    record_decision(first, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    drafted_by_a_read(session, "second-vaccine")

    decided = decide_prepared_lead_claim(session, "second-vaccine", now=NOW)

    assert decided is (ReviewState.REJECTED if joined else ReviewState.APPROVED)


def test_a_combination_never_shares_a_single_drugs_substance(session: Session):
    """Scenario: A combination under one substance"""
    from thenwhat.claims.entry import add_claim

    new_claim(session, "single-drug")
    add_claim(
        session,
        slug="bimagrumab-plus-semaglutide-obesity",
        headline="Combination for obesity",
        vertical="mouth-and-teeth",
        intervention="bimagrumab plus semaglutide",
        indication="tooth agenesis",
        summary="A combination.",
    )
    for slug in ("single-drug", "bimagrumab-plus-semaglutide-obesity"):
        under_substance(session, slug, "s-1")
    single = find_claim(session, "single-drug")
    assert single is not None
    record_decision(single, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    drafted_by_a_read(session, "bimagrumab-plus-semaglutide-obesity")

    assert (
        decide_prepared_lead_claim(session, "bimagrumab-plus-semaglutide-obesity", now=NOW)
        is ReviewState.APPROVED
    )
