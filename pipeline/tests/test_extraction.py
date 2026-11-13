"""Drafting claims from article text, tested through the functions of
`thenwhat.extract.service` with a scripted model on a real database.

Scenario names are from openspec claim-extraction and claims. The article is synthetic:
real article text must never be stored, including in tests.
"""

import hashlib
import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from thenwhat.claims.entry import (
    add_article,
    add_claim,
    articles_of,
    claim_count,
    edit_claim,
    find_claim,
    promises_of,
)
from thenwhat.db.models import Base, Claim, Entity
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.extract.names import is_a_name
from thenwhat.extract.service import (
    ClaimNotPending,
    draft_claim_from_article,
    extract_into_claim,
)
from thenwhat.llm.client import Llm, LlmOutputInvalid, LlmSettings
from thenwhat.review.decisions import record_decision

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
MARKER = "The zebra-striped molars glowed under ultraviolet lamps."
ARTICLE_TEXT = (
    "Scientists at Example University say an antibody called EX-1 regrew teeth in mice. "
    f"{MARKER} The work appears in the Journal of Examples (doi 10.1000/example.2018.1). "
    "Lead author Dr Ada Example said human trials could start by 2025."
)
ARTICLE_URL = "https://news.example.org/2018/teeth"

DRAFT: dict[str, Any] = {
    "headline": "Antibody regrows teeth in mice",
    "summary": "An antibody restored missing teeth in mice; the team hopes to test it in people.",
    "intervention": "EX-1 antibody",
    "intervention_synonyms": ["EX-1"],
    "indication": "tooth agenesis",
    "paper_title": "An antibody restores teeth in mice",
    "paper_doi": "10.1000/example.2018.1",
    "entities": [
        {"type": "person", "name": "Ada Example"},
        {"type": "institution", "name": "Example University"},
    ],
    "promises": ["human trials could start by 2025"],
}


def model_returning(*outputs: dict[str, Any]) -> tuple[FunctionModel, list[str]]:
    """A scripted model and the list of prompts it was shown."""
    remaining = list(outputs)
    prompts: list[str] = []

    def respond(messages, info) -> ModelResponse:
        prompts.append(str(messages))
        output = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

    return FunctionModel(respond, model_name="scripted"), prompts


def llm(session: Session, *outputs: dict[str, Any]) -> tuple[Llm, list[str]]:
    model, prompts = model_returning(*outputs)
    settings = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))
    return Llm(session, settings, model=model, now=lambda: NOW), prompts


def draft(session: Session, output: dict[str, Any] = DRAFT, **overrides: Any) -> Claim:
    client, _ = llm(session, output)
    arguments: dict[str, Any] = {
        "text": ARTICLE_TEXT,
        "slug": "tooth-regrowth-ex1",
        "vertical": "mouth-and-teeth",
        "url": ARTICLE_URL,
        "outlet": "Example News",
        "title": "Mice regrow teeth",
        "published_date": date(2018, 3, 10),
    }
    return draft_claim_from_article(session, client, **(arguments | overrides))


def entities(session: Session, claim: Claim, type: EntityType) -> list[Entity]:
    return list(
        session.scalars(
            select(Entity)
            .where(Entity.claim_id == claim.id, Entity.type == type)
            .order_by(Entity.id)
        )
    )


def everything_stored(session: Session) -> str:
    """Every value in every table, as one string."""
    session.flush()
    return "\n".join(
        str(session.execute(text(f"SELECT * FROM {table.name}")).all())
        for table in Base.metadata.sorted_tables
    )


# --- what a draft contains -------------------------------------------------------


def test_article_with_a_paper_and_a_promise_becomes_a_full_draft(session: Session):
    """Scenario: Article with a paper and a promise"""
    claim = draft(session)

    [intervention] = entities(session, claim, EntityType.INTERVENTION)
    [paper] = entities(session, claim, EntityType.PAPER)
    [promise] = promises_of(session, claim)
    assert (claim.headline, claim.indication) == (
        "Antibody regrows teeth in mice",
        "tooth agenesis",
    )
    assert claim.summary == DRAFT["summary"]
    assert (intervention.name, intervention.synonyms) == ("EX-1 antibody", ["EX-1"])
    assert (paper.name, paper.doi, paper.is_origin_paper) == (
        "An antibody restores teeth in mice",
        "10.1000/example.2018.1",
        True,
    )
    assert (promise.description, promise.parsed_date) == (
        "human trials could start by 2025",
        date(2025, 12, 31),
    )
    assert [e.name for e in entities(session, claim, EntityType.PERSON)] == ["Ada Example"]
    assert [e.name for e in entities(session, claim, EntityType.INSTITUTION)] == [
        "Example University"
    ]


@pytest.mark.parametrize(
    "name",
    [
        "EX-1",
        "TRG035",
        "semaglutide",
        "Hibsago",
        "mRNA-4157",
        "sac-TMT",
        "GAE",
        "Genicular artery embolization",
        "BPL-003 nasal spray",
        "Pig kidney transplant",
    ],
)
def test_a_name_is_kept_as_another_name(name: str):
    assert is_a_name(name)


@pytest.mark.parametrize(
    "description",
    [
        "the drug",
        "the pill",
        "The injection",
        "a one-time treatment",
        "one-time CRISPR treatment",
        "experimental oral minoxidil pill",
        "gene-editing treatment",
        "Non-surgical knee procedure",
        "Under-the-skin implant",
        "experimental personalized mRNA vaccine",
        "new therapy",
        "  ",
    ],
)
def test_a_description_is_not_another_name(description: str):
    assert not is_a_name(description)


def test_descriptions_the_model_returns_are_not_recorded_as_names(session: Session):
    """Scenario: Article that only describes the intervention"""
    output = DRAFT | {"intervention_synonyms": ["EX-1", "the drug", "experimental antibody jab"]}

    claim = draft(session, output)

    [intervention] = entities(session, claim, EntityType.INTERVENTION)
    assert intervention.synonyms == ["EX-1"]


def test_article_with_no_promise_gives_a_draft_without_promises(session: Session):
    """Scenario: Article with no promise"""
    claim = draft(session, DRAFT | {"promises": []})

    assert promises_of(session, claim) == []


def test_model_is_shown_the_article_text(session: Session):
    client, prompts = llm(session, DRAFT)

    draft_claim_from_article(
        session,
        client,
        text=ARTICLE_TEXT,
        slug="tooth-regrowth-ex1",
        vertical="mouth-and-teeth",
        url=ARTICLE_URL,
        outlet="Example News",
        title="Mice regrow teeth",
        published_date=date(2018, 3, 10),
    )

    assert MARKER in prompts[0]


# --- validation ------------------------------------------------------------------


def test_invalid_output_saves_no_draft_and_names_the_fields(session: Session):
    """Scenario: Invalid output"""
    with pytest.raises(LlmOutputInvalid) as refused:
        draft(session, DRAFT | {"headline": "", "paper_doi": "not a doi"})

    assert refused.value.fields == ["headline", "paper_doi"]
    assert claim_count(session) == 0


def test_overlong_summary_fails_validation(session: Session):
    """Scenario: Overlong summary"""
    with pytest.raises(LlmOutputInvalid) as refused:
        draft(session, DRAFT | {"summary": "x" * 501})

    assert refused.value.fields == ["summary"]


def test_summary_of_exactly_500_characters_is_accepted(session: Session):
    assert len(draft(session, DRAFT | {"summary": "x" * 500}).summary) == 500


# --- retention -------------------------------------------------------------------


def test_after_successful_extraction_only_the_hash_of_the_text_remains(
    session: Session, caplog: pytest.LogCaptureFixture
):
    """Scenario: After successful extraction"""
    caplog.set_level(logging.DEBUG)

    claim = draft(session)

    [article] = articles_of(session, claim)
    assert article.content_hash == hashlib.sha256(ARTICLE_TEXT.encode()).hexdigest()
    assert MARKER not in everything_stored(session)
    assert MARKER not in caplog.text


def test_article_stored_after_extraction_holds_no_body(session: Session):
    """Scenario: Article stored after extraction"""
    claim = draft(session)

    stored = everything_stored(session)
    assert find_claim(session, claim.slug) is not None
    assert not any(sentence in stored for sentence in ARTICLE_TEXT.split(". "))


def test_after_failed_extraction_nothing_of_the_text_remains(
    session: Session, caplog: pytest.LogCaptureFixture
):
    """Scenario: After failed extraction"""
    caplog.set_level(logging.DEBUG)

    with pytest.raises(LlmOutputInvalid):
        draft(session, DRAFT | {"summary": ""})

    assert MARKER not in everything_stored(session)
    assert MARKER not in caplog.text


def test_pasted_text_of_a_paywalled_article_is_used_and_discarded(session: Session):
    """Scenario: Paywalled article"""
    add_claim(
        session,
        slug="tooth-regrowth-ex1",
        headline="Operator's headline",
        vertical="mouth-and-teeth",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
    )
    add_article(
        session,
        "tooth-regrowth-ex1",
        url=ARTICLE_URL,
        outlet="Paywalled Times",
        title="Mice regrow teeth",
        published_date=date(2018, 3, 10),
    )
    client, prompts = llm(session, DRAFT)

    claim = extract_into_claim(
        session, client, claim_slug="tooth-regrowth-ex1", article_url=ARTICLE_URL, text=ARTICLE_TEXT
    )

    assert MARKER in prompts[0]
    assert claim.summary == DRAFT["summary"]
    assert MARKER not in everything_stored(session)


def test_snapshot_url_is_kept_with_the_article(session: Session):
    """Scenario: Dead link with a snapshot"""
    snapshot = "http://web.archive.org/web/20190101000000/https://news.example.org/2018/teeth"

    claim = draft(session, archive_url=snapshot)

    [article] = articles_of(session, claim)
    assert article.archive_url == snapshot


# --- drafts and existing claims ----------------------------------------------------


def test_new_draft_is_pending(session: Session):
    """Scenario: Unapproved draft"""
    assert draft(session).review_state is ReviewState.PENDING


def test_edited_draft_carries_the_correction_once_approved(session: Session):
    """Scenario: Edited draft"""
    claim = draft(session)

    edit_claim(session, claim.slug, headline="Antibody regrows teeth in mice, team reports")
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)

    assert claim.headline == "Antibody regrows teeth in mice, team reports"
    assert (claim.review_state, claim.reviewed_by, claim.reviewed_at) == (
        ReviewState.APPROVED,
        Decider.HUMAN,
        NOW,
    )


def test_extraction_into_an_existing_claim_keeps_what_the_operator_entered(session: Session):
    add_claim(
        session,
        slug="tooth-regrowth-ex1",
        headline="Operator's headline",
        vertical="mouth-and-teeth",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
        summary="Operator's summary.",
    )
    add_article(
        session,
        "tooth-regrowth-ex1",
        url=ARTICLE_URL,
        outlet="Example News",
        title="Mice regrow teeth",
        published_date=date(2018, 3, 10),
    )
    client, _ = llm(session, DRAFT)

    claim = extract_into_claim(
        session, client, claim_slug="tooth-regrowth-ex1", article_url=ARTICLE_URL, text=ARTICLE_TEXT
    )

    [intervention] = entities(session, claim, EntityType.INTERVENTION)
    assert (claim.headline, claim.summary) == ("Operator's headline", "Operator's summary.")
    assert intervention.synonyms == ["EX-1"]
    assert len(entities(session, claim, EntityType.PAPER)) == 1
    assert len(promises_of(session, claim)) == 1


def test_running_extraction_twice_adds_nothing_twice(session: Session):
    claim = draft(session)
    client, _ = llm(session, DRAFT)

    extract_into_claim(
        session, client, claim_slug=claim.slug, article_url=ARTICLE_URL, text=ARTICLE_TEXT
    )

    assert len(entities(session, claim, EntityType.PAPER)) == 1
    assert len(entities(session, claim, EntityType.PERSON)) == 1
    assert len(promises_of(session, claim)) == 1


def test_extraction_into_an_approved_claim_is_refused(session: Session):
    claim = draft(session)
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    client, _ = llm(session, DRAFT)

    with pytest.raises(ClaimNotPending):
        extract_into_claim(
            session, client, claim_slug=claim.slug, article_url=ARTICLE_URL, text=ARTICLE_TEXT
        )


# --- deciding drafts by rule (openspec auto-publish) -----------------------------------


def test_valid_draft_is_approved_by_rule_when_asked(session: Session):
    """Scenario: Valid draft"""
    claim = draft(session, decide_by_rule_at=NOW)

    assert (claim.review_state, claim.reviewed_by, claim.reviewed_at) == (
        ReviewState.APPROVED,
        Decider.RULE,
        NOW,
    )


def test_draft_naming_a_description_is_rejected_by_rule_and_kept(session: Session):
    """Scenario: Unapproved draft"""
    claim = draft(session, DRAFT | {"intervention": "the new drug"}, decide_by_rule_at=NOW)

    assert (claim.review_state, claim.reviewed_by) == (ReviewState.REJECTED, Decider.RULE)
    assert find_claim(session, claim.slug) is claim


def test_without_the_rule_a_draft_stays_pending(session: Session):
    assert draft(session).review_state is ReviewState.PENDING
