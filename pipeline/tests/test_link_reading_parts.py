"""The pieces reading a link lead is built from: the slug rule, the vertical decision,
the spacing of requests to one outlet, and adding a read article to a claim that
exists. Scenario names are from openspec lead-reading. Everything here is synthetic."""

import hashlib
from datetime import UTC, date, datetime

import httpx
import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from backfill_support import committed_sessions
from thenwhat.backfill.allowance import Allowances, outlet_source
from thenwhat.claims.entry import (
    InvalidSlug,
    SlugTaken,
    add_article,
    add_claim,
    articles_of,
    free_slug_for,
    promises_of,
    slug_for,
)
from thenwhat.claims.verticals import RETIRED_VERTICALS, VERTICALS
from thenwhat.db.models import Claim, DecisionLog, Entity, SourceAllowanceUse
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import VERTICAL_CHOICE, choose_vertical
from thenwhat.domain import Decider, ReviewState
from thenwhat.extract.retrieve import ArticleRetriever
from thenwhat.extract.schema import Draft
from thenwhat.extract.service import article_from_draft
from thenwhat.review.decisions import record_decision
from thenwhat.statements.service import StatementChecker

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)

# --- the slug rule -----------------------------------------------------------------


def test_a_slug_is_the_intervention_and_the_indication_in_plain_words():
    assert slug_for("EX-1 antibody", "Tooth agenesis") == "ex-1-antibody-tooth-agenesis"


def test_characters_outside_the_slugs_set_are_breaks_and_accents_are_dropped():
    """Scenario: A named intervention"""
    assert slug_for("Ménière's drug (β-2)", "ear/balance disorder") == (
        "meniere-s-drug-2-ear-balance-disorder"
    )


def test_a_long_slug_is_cut_to_the_whole_words_that_fit_in_sixty_characters():
    slug = slug_for(
        "Autologous mesenchymal stromal cell infusion",
        "relapsing remitting multiple sclerosis in adults",
    )

    assert slug == "autologous-mesenchymal-stromal-cell-infusion-relapsing"
    assert len(slug) <= 60 and not slug.endswith("-")


def test_nothing_usable_makes_no_slug():
    with pytest.raises(InvalidSlug):
        slug_for("…", "—")


def test_a_slug_that_belongs_to_another_claim_is_refused_by_name(session: Session):
    """Scenario: The slug is taken"""
    add_claim(
        session,
        slug="ex-1-antibody-tooth-agenesis",
        headline="A claim that took the slug by hand",
        vertical="mouth-and-teeth",
        intervention="Another drug",
        indication="another condition",
    )

    with pytest.raises(SlugTaken, match="'ex-1-antibody-tooth-agenesis'.*another claim"):
        free_slug_for(session, "EX-1 antibody", "tooth agenesis")
    assert free_slug_for(session, "EX-2 antibody", "tooth agenesis") == (
        "ex-2-antibody-tooth-agenesis"
    )


# --- the vertical decision ---------------------------------------------------------


class Chooses:
    """A decision backend that gives one vertical a probability and spreads the rest."""

    name = "fake"

    def __init__(self, vertical: str, probability: float) -> None:
        self.vertical = vertical
        self.probability = probability
        self.offered: list[str] = []

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        assert step == VERTICAL_CHOICE
        self.offered = options
        rest = (1 - self.probability) / (len(options) - 1)
        probabilities = {option: rest for option in options}
        probabilities[self.vertical] = self.probability
        return BackendAnswer(self.vertical, probabilities)


def choose(session: Session, backend: Chooses) -> tuple[str, float]:
    return choose_vertical(
        session,
        backend,
        ref="link_lead:1",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
        summary="An antibody restored missing teeth in mice.",
        now=NOW,
    )


def test_the_vertical_is_chosen_among_the_configured_ones_and_logged(session: Session):
    """Scenario: A named intervention"""
    backend = Chooses("mouth-and-teeth", 0.93)

    vertical, probability = choose(session, backend)

    assert (vertical, probability) == ("mouth-and-teeth", pytest.approx(0.93))
    [entry] = session.scalars(select(DecisionLog).where(DecisionLog.step == VERTICAL_CHOICE))
    assert entry.input_ref == "link_lead:1"


def test_a_retired_vertical_is_never_offered(session: Session):
    backend = Chooses("mouth-and-teeth", 0.9)

    choose(session, backend)

    assert backend.offered == list(VERTICALS)
    assert not set(backend.offered) & set(RETIRED_VERTICALS)


def test_an_unsure_choice_comes_back_with_its_low_probability(session: Session):
    """Scenario: No confident vertical. The caller creates no claim below its setting."""
    _, probability = choose(session, Chooses("cancer", 0.4))

    assert probability == pytest.approx(0.4)


# --- spacing requests to one outlet --------------------------------------------------


def test_two_processes_keep_their_requests_to_one_outlet_apart(engine: Engine, fake_time):
    """Scenario: Two processes, one outlet"""
    source = outlet_source("www.Spacing-Test.example")
    open_session = committed_sessions(engine)
    try:
        first = Allowances(open_session, {}, fake_time, outlet_interval_seconds=10)
        second = Allowances(open_session, {}, fake_time, outlet_interval_seconds=10)

        first.claim(source)
        second.claim(source)
        second.claim(outlet_source("other-outlet.example"))

        assert source == "outlet:spacing-test.example"
        # The second process waited the interval; another outlet is not held up by it.
        assert fake_time.slept == [10.0]
    finally:
        with Session(engine) as session, session.begin():
            session.execute(
                delete(SourceAllowanceUse).where(SourceAllowanceUse.source_name.like("outlet:%"))
            )


def test_a_longer_delay_in_robots_txt_replaces_the_interval(engine: Engine, fake_time):
    source = outlet_source("slow-outlet.example")
    open_session = committed_sessions(engine)
    try:
        allowances = Allowances(open_session, {}, fake_time, outlet_interval_seconds=10)

        allowances.claim(source, at_least_seconds=30)
        allowances.claim(source, at_least_seconds=30)
        allowances.claim(source, at_least_seconds=2)

        assert fake_time.slept == [30.0, 10.0]
    finally:
        with Session(engine) as session, session.begin():
            session.execute(
                delete(SourceAllowanceUse).where(SourceAllowanceUse.source_name.like("outlet:%"))
            )


def test_the_delay_an_outlet_asks_for_is_read_from_its_robots_txt():
    def site(request: httpx.Request) -> httpx.Response:
        if request.url.host == "slow.example":
            return httpx.Response(200, text="User-agent: *\nCrawl-delay: 30\nAllow: /\n")
        return httpx.Response(200, text="User-agent: *\nAllow: /\n")

    retriever = ArticleRetriever(
        contact_email="ops@thenwhat.test", transport=httpx.MockTransport(site)
    )

    assert retriever.crawl_delay("https://slow.example/news/a") == 30.0
    assert retriever.crawl_delay("https://quick.example/news/a") == 0.0


# --- an article for a claim that exists ----------------------------------------------


class NeverAsked:
    name = "fake"

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        raise AssertionError("an article with no statements needs no check")


DRAFT = Draft.model_validate(
    {
        "headline": "A different headline the article would give",
        "summary": "A different summary.",
        "intervention": "EX-1 antibody",
        "intervention_synonyms": ["EX-ONE"],
        "indication": "tooth agenesis",
        "entities": [{"type": "institution", "name": "Example University"}],
        "promises": ["human trials by 2025"],
    }
)


def tracked(session: Session) -> Claim:
    claim = add_claim(
        session,
        slug="ex-1-tooth-agenesis",
        headline="Antibody regrows teeth in mice",
        vertical="mouth-and-teeth",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
        summary="The reviewed summary.",
    )
    add_article(
        session,
        claim.slug,
        url="https://news.example.org/2021/teeth",
        outlet="The Example",
        title="A synthetic headline",
        published_date=date(2021, 3, 1),
    )
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    session.flush()
    return claim


def test_an_earlier_article_is_added_and_nothing_the_operator_reviewed_changes(
    session: Session,
):
    """Scenarios: An earlier report of a tracked claim, A decided claim"""
    claim = tracked(session)
    names_before = [
        (entity.type, entity.name, list(entity.synonyms))
        for entity in session.scalars(select(Entity).where(Entity.claim_id == claim.id))
    ]
    text = "Synthetic words of an earlier report."

    article, statements = article_from_draft(
        session,
        StatementChecker(NeverAsked(), accept_above=0.8, per_article=6, copied_run=8),
        claim,
        DRAFT,
        text=text,
        url="https://older.example.org/2018/teeth",
        outlet="older.example.org",
        title="An earlier synthetic headline",
        published_date=date(2018, 6, 2),
        archive_url="https://web.archive.org/web/2018/https://older.example.org/2018/teeth",
        now=NOW,
    )

    assert article.content_hash == hashlib.sha256(text.encode()).hexdigest()
    assert article.archive_url and statements.proposed == 0
    assert len(articles_of(session, claim)) == 2
    assert claim.first_reported_date == date(2018, 6, 2)
    assert (claim.headline, claim.summary) == (
        "Antibody regrows teeth in mice",
        "The reviewed summary.",
    )
    assert (claim.vertical, claim.indication) == ("mouth-and-teeth", "tooth agenesis")
    assert (claim.review_state, claim.reviewed_by) == (ReviewState.APPROVED, Decider.HUMAN)
    names_after = [
        (entity.type, entity.name, list(entity.synonyms))
        for entity in session.scalars(select(Entity).where(Entity.claim_id == claim.id))
    ]
    assert names_after == names_before
    assert promises_of(session, claim) == []
