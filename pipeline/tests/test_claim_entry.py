"""Manual entry, tested through the functions of `thenwhat.claims.entry` on a real database.

Tests named after a scenario in openspec claims carry its name in a `Scenario:` docstring.
"""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import (
    ArticleNotFound,
    ClaimNotFound,
    DuplicateArticle,
    DuplicateClaim,
    InvalidSlug,
    InvalidUrl,
    MissingField,
    SlugLocked,
    SlugTaken,
    UnknownVertical,
    add_article,
    add_claim,
    add_promise,
    articles_of,
    claim_count,
    find_claim,
    promises_of,
    rename_slug,
    archive_claim,
    unarchive_claim,
    ArchiveRefused,
)
from thenwhat.db.models import Claim, Entity
from thenwhat.domain import EntityType


def new_claim(session: Session, **overrides) -> Claim:
    values = {
        "slug": "tooth-regrowth-usag1",
        "headline": "Antibody regrows teeth in mice",
        "vertical": "mouth-and-teeth",
        "intervention": "USAG-1 antibody",
        "indication": "tooth agenesis",
    }
    return add_claim(session, **(values | overrides))


# --- adding a claim ----------------------------------------------------------


def test_claim_is_created_with_its_intervention_entity(session: Session):
    claim = new_claim(session)

    interventions = session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).all()
    assert (claim.slug, claim.indication) == ("tooth-regrowth-usag1", "tooth agenesis")
    assert [entity.name for entity in interventions] == ["USAG-1 antibody"]


def test_duplicate_slug_is_refused(session: Session):
    """Scenario: Duplicate slug"""
    new_claim(session)

    with pytest.raises(SlugTaken, match="tooth-regrowth-usag1"):
        new_claim(session, intervention="Tideglusib", indication="dentine repair")

    assert claim_count(session) == 1


@pytest.mark.parametrize("slug", ["Tooth-Regrowth", "tooth_regrowth", "-tooth", "a" * 61, ""])
def test_malformed_slug_is_refused(session: Session, slug: str):
    with pytest.raises(InvalidSlug):
        new_claim(session, slug=slug)

    assert claim_count(session) == 0


def test_unknown_vertical_is_refused_and_valid_ones_are_listed(session: Session):
    """Scenario: Unknown vertical"""
    with pytest.raises(UnknownVertical, match="mouth-and-teeth"):
        new_claim(session, vertical="hair-regrowth-typo")

    assert claim_count(session) == 0


@pytest.mark.parametrize("field", ["headline", "intervention", "indication"])
def test_blank_required_field_is_refused(session: Session, field: str):
    with pytest.raises(MissingField, match=field):
        new_claim(session, **{field: "   "})

    assert claim_count(session) == 0


# --- claim identity ------------------------------------------------------------


def test_same_intervention_for_a_different_indication_is_a_separate_claim(session: Session):
    """Scenario: Same intervention, different indication"""
    new_claim(session)

    new_claim(session, slug="usag1-gum-disease", indication="periodontitis")

    assert claim_count(session) == 2


def test_second_claim_for_the_same_intervention_and_indication_is_refused(session: Session):
    """Scenario: Second claim for the same intervention and indication"""
    new_claim(session)

    with pytest.raises(DuplicateClaim) as refused:
        new_claim(session, slug="another-slug")

    assert refused.value.existing_slug == "tooth-regrowth-usag1"
    assert claim_count(session) == 1


def test_identity_ignores_letter_case_and_spacing(session: Session):
    new_claim(session)

    with pytest.raises(DuplicateClaim):
        new_claim(
            session,
            slug="another-slug",
            intervention="  usag-1   ANTIBODY ",
            indication="Tooth  Agenesis",
        )


def test_identity_recognises_a_synonym_of_the_intervention(session: Session):
    """Scenario: Compound known under another name"""
    claim = new_claim(session)
    entity = session.scalars(select(Entity).where(Entity.claim_id == claim.id)).one()
    entity.synonyms = ["TRG-035"]
    session.flush()

    with pytest.raises(DuplicateClaim):
        new_claim(session, slug="another-slug", intervention="trg-035")


# --- source articles -----------------------------------------------------------

ARTICLE_2018: dict[str, Any] = {
    "url": "https://news.example.org/2018/teeth",
    "outlet": "Example News",
    "title": "Mice regrow teeth",
    "published_date": date(2018, 3, 10),
}
ARTICLE_2021: dict[str, Any] = {
    "url": "https://news.example.org/2021/teeth-update",
    "outlet": "Example News",
    "title": "Tooth drug heads for trials",
    "published_date": date(2021, 4, 2),
}


def changed(fields: dict[str, Any], **changes: Any) -> dict[str, Any]:
    return fields | changes


def test_added_article_is_listed_on_its_claim(session: Session):
    """Scenario: Add an article"""
    claim = new_claim(session)

    add_article(session, claim.slug, **ARTICLE_2018)

    [article] = articles_of(session, claim)
    assert (article.url, article.outlet, article.title, article.published_date) == tuple(
        ARTICLE_2018.values()
    )


def test_later_article_about_an_existing_claim_attaches_to_it(session: Session):
    """Scenario: Later article about an existing claim"""
    claim = new_claim(session)
    add_article(session, claim.slug, **ARTICLE_2018)

    add_article(session, claim.slug, **ARTICLE_2021)

    assert [a.url for a in articles_of(session, claim)] == [
        ARTICLE_2018["url"],
        ARTICLE_2021["url"],
    ]
    assert claim_count(session) == 1


def test_duplicate_article_url_creates_no_second_record(session: Session):
    """Scenario: Duplicate article URL"""
    claim = new_claim(session)
    add_article(session, claim.slug, **ARTICLE_2018)

    with pytest.raises(DuplicateArticle):
        add_article(session, claim.slug, **changed(ARTICLE_2021, url=ARTICLE_2018["url"]))

    assert len(articles_of(session, claim)) == 1


def test_first_article_sets_the_first_reported_date(session: Session):
    claim = new_claim(session)

    add_article(session, claim.slug, **ARTICLE_2021)

    assert claim.first_reported_date == date(2021, 4, 2)


def test_earlier_article_added_later_moves_the_first_reported_date(session: Session):
    """Scenario: Earlier article added later"""
    claim = new_claim(session)
    add_article(session, claim.slug, **ARTICLE_2021)

    add_article(session, claim.slug, **ARTICLE_2018)

    assert claim.first_reported_date == date(2018, 3, 10)


def test_later_article_leaves_the_first_reported_date_alone(session: Session):
    claim = new_claim(session)
    add_article(session, claim.slug, **ARTICLE_2018)

    add_article(session, claim.slug, **ARTICLE_2021)

    assert claim.first_reported_date == date(2018, 3, 10)


def test_article_for_an_unknown_claim_is_refused(session: Session):
    with pytest.raises(ClaimNotFound, match="no-such-claim"):
        add_article(session, "no-such-claim", **ARTICLE_2018)


@pytest.mark.parametrize("field", ["outlet", "title"])
def test_article_with_a_blank_required_field_is_refused(session: Session, field: str):
    claim = new_claim(session)

    with pytest.raises(MissingField, match=field):
        add_article(session, claim.slug, **changed(ARTICLE_2018, **{field: " "}))


@pytest.mark.parametrize("url", ["", "news.example.org/teeth", "ftp://example.org/a"])
def test_article_url_must_be_a_web_address(session: Session, url: str):
    claim = new_claim(session)

    with pytest.raises(InvalidUrl):
        add_article(session, claim.slug, **changed(ARTICLE_2018, url=url))


# --- promises ------------------------------------------------------------------


def claim_with_two_articles(session: Session) -> Claim:
    claim = new_claim(session)
    add_article(session, claim.slug, **ARTICLE_2018)
    add_article(session, claim.slug, **ARTICLE_2021)
    return claim


def test_repeated_promises_are_each_linked_to_their_own_article(session: Session):
    """Scenario: Repeated promises"""
    claim = claim_with_two_articles(session)

    add_promise(session, claim.slug, article_url=ARTICLE_2018["url"], description="by 2020")
    add_promise(session, claim.slug, article_url=ARTICLE_2021["url"], description="by 2024")

    first, second = promises_of(session, claim)
    articles = {article.id: article.url for article in articles_of(session, claim)}
    assert (articles[first.source_article_id], first.parsed_date) == (
        ARTICLE_2018["url"],
        date(2020, 12, 31),
    )
    assert (articles[second.source_article_id], second.parsed_date) == (
        ARTICLE_2021["url"],
        date(2024, 12, 31),
    )


def test_relative_promise_is_dated_from_its_own_article(session: Session):
    claim = claim_with_two_articles(session)

    promise = add_promise(
        session, claim.slug, article_url=ARTICLE_2021["url"], description="within five years"
    )

    assert promise.parsed_date == date(2026, 4, 2)


def test_unparseable_promise_keeps_its_description_and_has_no_date(session: Session):
    """Scenario: Unparseable promise"""
    claim = claim_with_two_articles(session)

    promise = add_promise(
        session, claim.slug, article_url=ARTICLE_2018["url"], description="in the near future"
    )

    assert (promise.description, promise.parsed_date) == ("in the near future", None)


def test_operator_supplied_date_overrides_the_parsed_one(session: Session):
    claim = claim_with_two_articles(session)

    promise = add_promise(
        session,
        claim.slug,
        article_url=ARTICLE_2018["url"],
        description="by 2025",
        parsed_date=date(2025, 6, 30),
    )

    assert promise.parsed_date == date(2025, 6, 30)


def test_promise_for_an_article_the_claim_does_not_have_is_refused(session: Session):
    claim = new_claim(session)

    with pytest.raises(ArticleNotFound):
        add_promise(session, claim.slug, article_url=ARTICLE_2018["url"], description="by 2025")


def test_promise_with_a_blank_description_is_refused(session: Session):
    claim = claim_with_two_articles(session)

    with pytest.raises(MissingField, match="description"):
        add_promise(session, claim.slug, article_url=ARTICLE_2018["url"], description="  ")


# --- renaming a slug -------------------------------------------------------------


def test_slug_change_after_publication_is_refused(session: Session):
    """Scenario: Slug change after publication"""
    claim = new_claim(session)
    claim.published_at = datetime(2026, 1, 1, tzinfo=UTC)

    with pytest.raises(SlugLocked):
        rename_slug(session, "tooth-regrowth-usag1", "tooth-regrowth")

    assert claim.slug == "tooth-regrowth-usag1"


def test_unpublished_claim_can_be_renamed(session: Session):
    claim = new_claim(session)

    rename_slug(session, "tooth-regrowth-usag1", "tooth-regrowth")

    assert claim.slug == "tooth-regrowth"
    assert find_claim(session, "tooth-regrowth-usag1") is None


def test_rename_to_a_malformed_slug_is_refused(session: Session):
    new_claim(session)

    with pytest.raises(InvalidSlug):
        rename_slug(session, "tooth-regrowth-usag1", "Tooth Regrowth")


def test_rename_to_a_taken_slug_is_refused(session: Session):
    new_claim(session)
    new_claim(session, slug="enamel-gel", intervention="Enamel gel", indication="enamel loss")

    with pytest.raises(SlugTaken):
        rename_slug(session, "enamel-gel", "tooth-regrowth-usag1")


def test_rename_of_an_unknown_claim_is_refused(session: Session):
    with pytest.raises(ClaimNotFound):
        rename_slug(session, "no-such-claim", "new-name")


# --- archiving ---------------------------------------------------------------


def test_archiving_keeps_the_claim_and_records_why(session: Session):
    """Scenario: Operator takes a claim down"""
    now = datetime(2026, 11, 14, tzinfo=UTC)
    new_claim(session)

    claim = archive_claim(session, "tooth-regrowth-usag1", reason="wrong trial", now=now)

    assert claim.archived_at == now
    assert claim.archive_reason == "wrong trial"
    assert find_claim(session, "tooth-regrowth-usag1") is claim


def test_archiving_an_unknown_slug_is_refused(session: Session):
    """Scenario: Unknown slug"""
    with pytest.raises(ClaimNotFound, match="no-such-claim"):
        archive_claim(session, "no-such-claim", reason="x", now=datetime(2026, 11, 14, tzinfo=UTC))


def test_archiving_needs_a_reason(session: Session):
    new_claim(session)

    with pytest.raises(ArchiveRefused):
        archive_claim(session, "tooth-regrowth-usag1", reason="  ", now=datetime.now(UTC))


def test_unarchiving_puts_it_back(session: Session):
    """Scenario: Putting it back"""
    new_claim(session)
    archive_claim(session, "tooth-regrowth-usag1", reason="wrong trial", now=datetime.now(UTC))

    claim = unarchive_claim(session, "tooth-regrowth-usag1")

    assert claim.archived_at is None
    assert claim.archive_reason is None
