"""Topics: the words that mark a lead or a claim as belonging to one, and how far a topic
is covered. Scenario names are from openspec lead-reading, "Topic coverage". Every title
here is synthetic."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from thenwhat.backfill.link_topics import (
    NOT_SCORED,
    NOT_SCREENED,
    REJECTED,
    TO_READ,
    UNLISTED,
    coverage,
)
from thenwhat.backfill.topics import (
    TOPICS,
    UnknownTopic,
    names_one,
    names_only_a_class,
    other_names_of,
    terms_of,
)
from thenwhat.claims.entry import add_article, add_claim
from thenwhat.db.models import Entity, EntityMatch, LinkLead
from thenwhat.domain import Decider, OutletKind, ReadOutcome, ReviewState, ScreenOutcome
from thenwhat.review.decisions import record_decision

NOW = datetime(2026, 11, 20, tzinfo=UTC)


def test_a_topic_word_is_named_whole_and_in_any_letter_case():
    words = ("GLP-1", "Ozempic")

    assert names_one("New glp-1 drugs compared", words)
    assert names_one("Ozempic, explained", words)
    assert not names_one("GLP-12 receptors", words)
    assert not names_one("Ozempics are not a thing", words)
    assert not names_one("anything", ())


def test_every_topic_has_words_and_an_unknown_topic_is_refused_by_name():
    assert all(TOPICS.values())
    assert set(terms_of("glp-1")) <= set(terms_of())
    with pytest.raises(UnknownTopic, match="glp-1"):
        terms_of("statins")


def test_a_drugs_other_names_are_its_brands_and_its_generic_name():
    assert set(other_names_of(["Wegovy"])) == {"semaglutide", "Ozempic", "Wegovy", "Rybelsus"}
    assert "Mounjaro" in other_names_of(["a weekly shot", "tirzepatide"])
    # A word that is no drug's name, and a name on no list, have no other names.
    assert other_names_of(["GLP-1"]) == ()
    assert other_names_of(["aspirin"]) == ()


def lead(
    session: Session,
    number: int,
    title: str,
    *,
    screen: ScreenOutcome | None = ScreenOutcome.IN_SCOPE,
    score: float | None = None,
    read: ReadOutcome | None = None,
) -> None:
    session.add(
        LinkLead(
            url=f"https://news.example.org/{number}",
            url_key=f"news.example.org/{number}",
            outlet="news.example.org",
            outlet_kind=OutletKind.GENERAL_NEWS,
            title=title,
            first_shared_at=NOW,
            screen_outcome=screen,
            triage_score=score,
            triage_version=1 if score is not None else None,
            read_outcome=read,
        )
    )
    session.flush()


def test_coverage_counts_the_leads_that_name_the_topic_by_where_they_stand(session: Session):
    """Scenario: Leads at every stage"""
    lead(session, 1, "Ozempic in a synthetic trial", screen=None)
    lead(session, 2, "Wegovy on a synthetic blog", screen=ScreenOutcome.UNLISTED_OUTLET)
    lead(session, 3, "Mounjaro awaits a score")
    lead(session, 4, "What tirzepatide costs", score=0.05)
    lead(session, 5, "Semaglutide held by triage", score=0.4)
    lead(session, 6, "Semaglutide passed by triage", score=0.9)
    lead(session, 7, "Retatrutide read already", score=0.9, read=ReadOutcome.NEW_CLAIM)
    lead(session, 8, "A synthetic story about statins", score=0.9)

    found = coverage(session, "glp-1", reject_below=0.1)

    assert found.named == 7
    assert found.standing == {
        NOT_SCREENED: 1,
        UNLISTED: 1,
        "already a source article": 0,
        NOT_SCORED: 1,
        REJECTED: 1,
        TO_READ: 2,
    }
    assert found.read == {"new_claim": 1}


def test_coverage_lists_each_claim_for_the_topic_with_what_it_holds(session: Session):
    """Scenario: A claim with a trial and a paper"""
    claim = add_claim(
        session,
        slug="semaglutide-obesity",
        headline="A synthetic headline",
        vertical="diabetes-and-hormones",
        intervention="semaglutide",
        indication="obesity",
    )
    add_article(
        session,
        claim.slug,
        url="https://news.example.org/a",
        outlet="Example News",
        title="A synthetic title",
        published_date=NOW.date(),
    )
    add_claim(
        session,
        slug="aspirin-headache",
        headline="A synthetic headline",
        vertical="brain-and-nerves",
        intervention="aspirin",
        indication="headache",
    )
    entity = session.query(Entity).filter_by(claim_id=claim.id).one()
    for source, identifier, state in (
        ("clinicaltrials.gov", "NCT00000001", ReviewState.APPROVED),
        ("clinicaltrials.gov", "NCT00000002", ReviewState.REJECTED),
        ("openalex", "W1", ReviewState.APPROVED),
    ):
        match = EntityMatch(
            entity_id=entity.id, source_name=source, external_id=identifier, score=0.9
        )
        session.add(match)
        record_decision(match, state, by=Decider.RULE, now=NOW)
    session.flush()

    [found] = coverage(session, "glp-1", reject_below=0.1).claims

    assert (found.slug, found.intervention, found.indication) == (
        "semaglutide-obesity",
        "semaglutide",
        "obesity",
    )
    assert (found.review_state, found.published) == ("pending", False)
    assert (found.articles, found.trials, found.papers, found.cards) == (1, 1, 1, 0)


@pytest.mark.parametrize(
    "name",
    ["GLP-1", "GLP-1 metabolic therapy", "Daily GLP-1 therapy", "Compounded GLP-1 injections"],
)
def test_a_topics_class_word_with_no_drug_and_no_name_is_the_class(name: str):
    assert names_only_a_class([name])


@pytest.mark.parametrize(
    "name",
    [
        "semaglutide",
        "oral GLP-1 pill orforglipron",
        "Oral engineered E. coli that senses glucose and releases GLP-1",
        "esketamine",
    ],
)
def test_a_drug_or_a_described_treatment_is_not_the_topics_class(name: str):
    assert not names_only_a_class([name])
