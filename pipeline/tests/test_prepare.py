"""Preparing many claims for review in one command: which steps each claim needs
(`plan_claims`, on a real database) and the `prepare` command with its steps faked."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner

from thenwhat.backfill.outlet_hold import LEFT_FOR_LATER
from thenwhat.claims.entry import (
    ClaimNotFound,
    add_article,
    add_claim,
    awaiting_audit,
    find_article,
    find_claim,
)
from thenwhat.cli import app
from thenwhat.db.models import LinkLead, SourceArticle
from thenwhat.domain import Decider, OutletKind, ReadOutcome, ReviewState
from thenwhat.prepare import decide_prepared_lead_claim, plan_claims, steps_for
from thenwhat.review.decisions import record_decision

NOW = datetime(2026, 11, 20, tzinfo=UTC)


def claim_with_articles(session: Session, slug: str, *urls: str) -> None:
    add_claim(
        session,
        slug=slug,
        headline="Antibody regrows teeth in mice",
        vertical="mouth-and-teeth",
        intervention=f"EX-1 antibody {slug}",
        indication="tooth agenesis",
        summary="An antibody restored missing teeth in mice.",
    )
    for number, url in enumerate(urls, 1):
        add_article(
            session,
            slug,
            url=url,
            outlet="Example News",
            title=f"Report {number}",
            published_date=date(2018, 3, number),
        )


def test_a_claim_needs_its_unread_articles_read_then_a_search_then_a_fetch(session: Session):
    claim_with_articles(session, "one", "https://news.example.org/a", "https://news.example.org/b")
    one = find_claim(session, "one")
    assert one is not None
    read = find_article(session, one, "https://news.example.org/a")
    assert read is not None
    read.content_hash = "already read"
    session.flush()

    [plan] = plan_claims(session, ["one"])

    assert plan.unread_articles == ["https://news.example.org/b"]
    assert steps_for(plan) == [
        [
            "extract",
            "article",
            "one",
            "--article-url",
            "https://news.example.org/b",
            "--unless-held",
        ],
        ["resolve", "one"],
        ["fetch", "one"],
        ["readings", "one"],
        ["terms", "one"],
    ]


def test_a_decided_claim_is_searched_and_fetched_but_its_articles_are_not_read(session: Session):
    claim_with_articles(session, "one", "https://news.example.org/a")
    one = find_claim(session, "one")
    assert one is not None
    record_decision(one, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    session.flush()

    [plan] = plan_claims(session, ["one"])

    assert plan.unread_articles == []
    assert steps_for(plan) == [
        ["resolve", "one"],
        ["fetch", "one"],
        ["readings", "one"],
        ["terms", "one"],
    ]


def test_without_names_every_claim_awaiting_review_is_planned(session: Session):
    claim_with_articles(session, "pending-one", "https://news.example.org/a")
    claim_with_articles(session, "decided-one", "https://news.example.org/b")
    decided = find_claim(session, "decided-one")
    assert decided is not None
    record_decision(decided, ReviewState.REJECTED, by=Decider.HUMAN, now=NOW)
    session.flush()

    assert [plan.slug for plan in plan_claims(session, None)] == ["pending-one"]


def test_an_unknown_claim_is_refused_before_anything_runs(session: Session):
    with pytest.raises(ClaimNotFound, match="no-such-claim"):
        plan_claims(session, ["no-such-claim"])


# --- the command -----------------------------------------------------------------------


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    ran: list[list[str]] = []

    def fake_step(arguments: list[str]) -> tuple[int, str]:
        ran.append(arguments)
        address = arguments[4] if arguments[0] == "extract" else ""
        if address.endswith("/held"):
            return (LEFT_FOR_LATER, "Left for later. Its outlet cannot be asked yet.")
        failed = address.endswith("/blocked") or (
            arguments[0] == "terms" and arguments[-1].endswith("no-terms")
        )
        return (1 if failed else 0, "could not be read" if failed else "done")

    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.prepare.run_step", fake_step)
    runner = CliRunner()
    # The settings are read for the rule that decides a read's claim; the database they
    # name is never opened, because the session above stands in for it.
    env = {"COLUMNS": "200", "DATABASE_URL": "postgresql+psycopg://unused/unused"}
    return lambda *arguments: (runner.invoke(app, list(arguments), env=env), ran)


def test_prepare_runs_every_step_and_carries_on_after_an_article_that_cannot_be_read(
    run, session: Session
):
    claim_with_articles(session, "one", "https://news.example.org/blocked")

    result, ran = run("prepare", "one")

    assert result.exit_code == 0, result.output
    assert [step[0] for step in ran] == ["extract", "resolve", "fetch", "readings", "terms"]
    assert "one" in result.output and "could not be read" in result.output


def test_prepare_due_prepares_the_claims_whose_registry_search_is_due(run, session: Session):
    """Scenario: Search due after a rename (openspec claims)"""
    claim_with_articles(session, "not-due", "https://news.example.org/a")
    due = find_claim(session, "not-due")
    assert due is not None
    record_decision(due, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    claim_with_articles(session, "renamed", "https://news.example.org/b")
    renamed = find_claim(session, "renamed")
    assert renamed is not None
    record_decision(renamed, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    renamed.registry_search_due_at = NOW
    session.flush()

    result, ran = run("prepare", "--due")

    assert result.exit_code == 0, result.output
    assert {step[1] for step in ran if step[0] == "resolve"} == {"renamed"}


def test_prepare_with_no_claims_named_explains_and_exits_1(run):
    result, ran = run("prepare")

    assert result.exit_code == 1
    assert "--pending" in result.output
    assert ran == []


# --- a claim that a link lead's read drafted ---------------------------------------------


def drafted_by_a_read(session: Session, slug: str) -> None:
    """Mark the claim as the new claim of a link lead's read."""
    claim = find_claim(session, slug)
    assert claim is not None
    session.add(
        LinkLead(
            url=f"https://news.example.org/{slug}",
            url_key=f"news.example.org/{slug}",
            outlet="news.example.org",
            outlet_kind=OutletKind.GENERAL_NEWS,
            title="words a person wrote when sharing the link",
            first_shared_at=NOW,
            read_outcome=ReadOutcome.NEW_CLAIM,
            claim_id=claim.id,
        )
    )
    session.flush()


def test_a_claim_a_read_drafted_is_approved_by_rule_once_it_is_prepared(session: Session):
    """Scenario: Prepared and named"""
    claim_with_articles(session, "one")
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
    claim_with_articles(session, "one")

    assert decide_prepared_lead_claim(session, "one", now=NOW) is None

    claim = find_claim(session, "one")
    assert claim is not None and claim.review_state is ReviewState.PENDING


# --- the audit of a prepared batch --------------------------------------------------------


def test_audit_clear_releases_held_claims_and_refuses_one_not_held(run, session: Session):
    """Scenarios: Audit passed, Not awaiting audit"""
    for slug in ("held", "also-held", "never-held"):
        claim_with_articles(session, slug)
    for slug in ("held", "also-held"):
        drafted_by_a_read(session, slug)
        decide_prepared_lead_claim(session, slug, now=NOW)

    refused, _ = run("audit", "clear", "held", "never-held")

    assert refused.exit_code == 1
    assert "never-held" in refused.output and "Nothing was cleared" in refused.output
    assert [claim.slug for claim in awaiting_audit(session)] == ["also-held", "held"]

    cleared, _ = run("audit", "clear", "held")

    assert cleared.exit_code == 0, cleared.output
    assert [claim.slug for claim in awaiting_audit(session)] == ["also-held"]
    listed, _ = run("audit", "list")
    assert "also-held" in listed.output and "1 claim awaits audit" in listed.output


def test_prepare_approves_a_reads_claim_only_when_every_step_succeeded(run, session: Session):
    """Scenarios: Prepared and named, A step that failed"""
    claim_with_articles(session, "searched", "https://news.example.org/a")
    claim_with_articles(session, "unsearched", "https://news.example.org/blocked")
    for slug in ("searched", "unsearched"):
        drafted_by_a_read(session, slug)

    # One at a time: every claim's thread would otherwise share the one test session, and
    # two flushing it at once fail with "Session is already flushing".
    result, _ = run("prepare", "--pending", "--workers", "1")

    assert result.exit_code == 0, result.output
    assert "approved by rule, now that its registries have been searched" in result.output
    states = {
        slug: claim.review_state
        for slug in ("searched", "unsearched")
        if (claim := find_claim(session, slug))
    }
    assert states == {"searched": ReviewState.APPROVED, "unsearched": ReviewState.PENDING}


def test_an_article_of_a_held_outlet_is_left_for_later_and_its_claim_waits(run, session: Session):
    """Scenario: Prepare comes to an article of a stopped outlet"""
    claim_with_articles(session, "waiting", "https://news.example.org/held")
    drafted_by_a_read(session, "waiting")

    result, ran = run("prepare", "waiting")

    assert result.exit_code == 0, result.output
    # Asked not to ask a held outlet, reported as left for later and not as failed, and
    # the claim's other steps ran.
    assert ran[0][-1] == "--unless-held"
    assert [step[0] for step in ran] == ["extract", "resolve", "fetch", "readings", "terms"]
    assert "read left for later" in result.output and "failed" not in result.output
    # Not decided: a later run reads the article first.
    claim = find_claim(session, "waiting")
    assert claim is not None and claim.review_state is ReviewState.PENDING


def test_a_claim_whose_terms_failed_is_still_decided(run, session: Session):
    """Scenario: Terms that could not be proposed"""
    claim_with_articles(session, "no-terms", "https://news.example.org/a")
    drafted_by_a_read(session, "no-terms")

    result, _ = run("prepare", "no-terms")

    assert result.exit_code == 0, result.output
    assert "terms failed" in result.output
    claim = find_claim(session, "no-terms")
    assert claim is not None and claim.review_state is ReviewState.APPROVED


def test_audit_list_shows_reads_that_overlap_a_claim(run, session: Session):
    """Scenarios: A read that overlaps an archived claim, A read that overlaps a claim
    that is not archived"""
    from thenwhat.backfill.link_read import NAMES_OVERLAP
    from thenwhat.claims.entry import archive_claim

    for slug in ("archived-one", "live-one"):
        claim_with_articles(session, slug)
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

    listed, _ = run("audit", "list")

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

    claim_with_articles(session, "live-one")
    claim_with_articles(session, "brand-one", "https://news.example.org/brand")
    for slug in ("oral-form", "after-archive"):
        claim_with_articles(session, slug)
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
        claim_with_articles(session, slug)
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

    claim_with_articles(session, "single-drug")
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
