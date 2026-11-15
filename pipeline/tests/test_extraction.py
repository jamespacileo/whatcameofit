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
from thenwhat.db.models import Base, Claim, Entity, ReportedStatement
from thenwhat.decide.core import BackendAnswer
from thenwhat.domain import (
    Decider,
    EntityType,
    ReviewState,
    StatementBasis,
    StatementFirmness,
    StatementKind,
    StatementSpeaker,
)
from thenwhat.extract.names import is_a_class, is_a_name
from thenwhat.extract.phrases import backfill_search_phrases
from thenwhat.extract.schema import Draft
from thenwhat.extract.service import (
    ClaimNotPending,
    Extracted,
    draft_claim_from_article,
    extract_into_claim,
)
from thenwhat.llm.client import Llm, LlmOutputInvalid, LlmSettings
from thenwhat.review.decisions import record_decision
from thenwhat.statements.service import StatementChecker

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


class Checks:
    """A batch backend for the statement check: says each statement is in the article,
    with the probability given for its text, 0.9 when none is given."""

    name = "fake"

    def __init__(self, probabilities: dict[str, float] | None = None) -> None:
        self.probabilities = probabilities or {}
        self.calls: list[tuple[str, str, list[str]]] = []

    def answer_many(
        self, step: str, intro: str, question: str, items: list[str], options: list[str]
    ) -> list[BackendAnswer]:
        self.calls.append((step, intro, items))
        answers = []
        for item in items:
            text = item.splitlines()[0].removeprefix("Statement: ")
            p = self.probabilities.get(text, 0.9)
            rest = (1 - p) / (len(options) - 1)
            answers.append(
                BackendAnswer(options[0], {o: p if o == options[0] else rest for o in options})
            )
        return answers

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        raise AssertionError("Statements are checked together.")


def checker(backend: Checks | None = None) -> StatementChecker:
    return StatementChecker(backend or Checks())


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
    return drafted(session, output, **overrides).claim


def drafted(
    session: Session,
    output: dict[str, Any] = DRAFT,
    checks: StatementChecker | None = None,
    **overrides: Any,
) -> Extracted:
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
    return draft_claim_from_article(
        session, client, checks or checker(), now=NOW, **(arguments | overrides)
    )


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


@pytest.mark.parametrize(
    "name",
    [
        "GLP-1 receptor agonists",
        "GLP-1 drugs",
        "PD-1 inhibitor",
        "COVID-19 vaccines",
        "Weight-loss medications",
        "β2 agonist",
        "GLP-1s",
        "GLP-1 drugs for obesity",
        "GLP-1 drugs For obesity",
        "(GLP-1s)",
        "glucagon-like peptide-1 receptor agonist",
        "glucagon receptor agonist",
        "GIP receptor agonist",
        "GLP-1 and/or GIP receptor agonist prescriptions",
    ],
)
def test_a_class_of_treatments_is_told_from_one_treatment(name: str):
    assert is_a_class(name)


@pytest.mark.parametrize(
    "name",
    [
        "semaglutide",
        "Wegovy",
        "BPL-003",
        "COVID-19 vaccine",
        "esketamine nasal spray",
        "retatrutide for obesity",
        "GLP-1 receptor agonist semaglutide",
        "SGLT2 inhibitor dapagliflozin",
        "PD-1 inhibitor pembrolizumab",
        "dual GLP-1/GIP agonist tirzepatide",
        "",
    ],
)
def test_one_treatment_is_not_a_class(name: str):
    assert not is_a_class(name)


def test_the_read_is_asked_for_one_condition_and_to_keep_prevention_apart():
    """Scenarios: An aim reported as the condition; Prevention is not treatment"""
    asked = Draft.model_fields["indication"].description or ""

    assert "never an aim or an outcome" in asked and "One condition" in asked
    assert "'prevention of COVID-19'" in asked


def test_descriptions_the_model_returns_are_not_recorded_as_names(session: Session):
    """Scenario: Article that only describes the intervention"""
    output = DRAFT | {"intervention_synonyms": ["EX-1", "the drug", "experimental antibody jab"]}

    claim = draft(session, output)

    [intervention] = entities(session, claim, EntityType.INTERVENTION)
    assert intervention.synonyms == ["EX-1"]


def test_device_with_no_name_gets_search_phrases_and_no_other_name(session: Session):
    """Scenario: Device with no product name"""
    output = DRAFT | {
        "intervention": "Wrist-worn median nerve stimulation device",
        "intervention_synonyms": [],
        "intervention_search_phrases": ["median nerve stimulation", "the device"],
        "indication": "Tourette syndrome",
    }

    claim = draft(session, output)

    [intervention] = entities(session, claim, EntityType.INTERVENTION)
    assert intervention.search_phrases == ["median nerve stimulation"]
    assert intervention.synonyms == []


@pytest.mark.parametrize(
    ("name", "synonyms", "kept"),
    [
        ("EX-1 plus EX-2", ["EX-1", "EX-2", "Dualex"], ["Dualex"]),
        ("Dualex", ["EX-1 plus EX-2", "EX-1", "EX-2"], ["EX-1 plus EX-2"]),
    ],
)
def test_combination_components_are_not_saved_as_whole_intervention_names(
    session: Session, name: str, synonyms: list[str], kept: list[str]
):
    claim = draft(session, DRAFT | {"intervention": name, "intervention_synonyms": synonyms})
    [intervention] = entities(session, claim, EntityType.INTERVENTION)
    assert intervention.name == name
    assert intervention.synonyms == kept


def test_named_drug_may_have_no_search_phrase(session: Session):
    """Scenario: Named drug"""
    claim = draft(session)

    [intervention] = entities(session, claim, EntityType.INTERVENTION)
    assert intervention.search_phrases == []


def test_only_the_researcher_is_recorded_as_a_person(session: Session):
    """Scenario: Report featuring a patient"""
    output = DRAFT | {
        "entities": [
            {"type": "person", "name": "Milo"},
            {"type": "person", "name": "Professor Ada Example"},
            {"type": "institution", "name": "Example University"},
        ]
    }
    client, prompts = llm(session, output)

    claim = draft_claim_from_article(
        session,
        client,
        checker(),
        text=(
            "By Rae Reporter. Milo, 15, wore the wristband for a month."
            " Professor Ada Example, who led the study, said it calmed his tics."
        ),
        slug="tic-wristband",
        vertical="brain-and-nerves",
        url=ARTICLE_URL,
        outlet="Example News",
        title="A wristband for tics",
        published_date=date(2023, 6, 1),
    ).claim

    assert [p.name for p in entities(session, claim, EntityType.PERSON)] == [
        "Professor Ada Example"
    ]
    # The model is told who counts; a first name it returns anyway is dropped.
    assert "carrying out or leading the research" in prompts[0]
    assert "a patient, a relative, a reporter or a commentator" in prompts[0]


def test_article_naming_only_patients_records_no_person(session: Session):
    """Scenario: Article naming no researcher"""
    claim = draft(session, DRAFT | {"entities": [{"type": "person", "name": "Milo"}]})

    assert entities(session, claim, EntityType.PERSON) == []


def test_article_with_no_promise_gives_a_draft_without_promises(session: Session):
    """Scenario: Article with no promise"""
    claim = draft(session, DRAFT | {"promises": []})

    assert promises_of(session, claim) == []


def test_model_is_shown_the_article_text(session: Session):
    client, prompts = llm(session, DRAFT)

    draft_claim_from_article(
        session,
        client,
        checker(),
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
        session,
        client,
        checker(),
        claim_slug="tooth-regrowth-ex1",
        article_url=ARTICLE_URL,
        text=ARTICLE_TEXT,
    ).claim

    assert MARKER in prompts[0]
    assert claim.summary == DRAFT["summary"]
    assert MARKER not in everything_stored(session)


def test_snapshot_url_is_kept_with_the_article(session: Session):
    """Scenario: Dead link with a snapshot"""
    snapshot = "http://web.archive.org/web/20190101000000/https://news.example.org/2018/teeth"

    claim = draft(session, archive_url=snapshot)

    [article] = articles_of(session, claim)
    assert article.archive_url == snapshot


# --- reported statements (openspec reported-statements) ------------------------------

STATEMENT_ARTICLE = (
    "Researchers at Example University report that an antibody named EX-1 regrew missing"
    " teeth in seven of ten mice. Professor Ada Example said she hoped the antibody might one"
    f" day spare people born without teeth from implants. {MARKER} Trials in people could"
    " begin by 2027."
)
EFFECT = "EX-1 regrew missing teeth in most of the mice it was given to."
HOPE = "The antibody might let people born without teeth avoid implants in future."
STATEMENT_DRAFT = DRAFT | {
    "promises": ["trials in people could begin by 2027"],
    "statements": [
        {
            "text": EFFECT,
            "kind": "effect",
            "firmness": "fact",
            "speaker": "article",
            "basis": "animals",
        },
        {
            "text": HOPE,
            "kind": "who_it_could_help",
            "firmness": "possibility",
            "speaker": "researcher",
            "basis": "not_said",
        },
    ],
}


def stored_statements(session: Session, claim: Claim) -> list[ReportedStatement]:
    return list(
        session.scalars(
            select(ReportedStatement)
            .where(ReportedStatement.claim_id == claim.id)
            .order_by(ReportedStatement.id)
        )
    )


def test_article_with_an_effect_a_hope_and_a_timeline_gives_two_statements_and_a_promise(
    session: Session,
):
    """Scenario: Article with an effect and a hope"""
    client, prompts = llm(session, STATEMENT_DRAFT)

    claim = draft_claim_from_article(
        session,
        client,
        checker(),
        text=STATEMENT_ARTICLE,
        slug="tooth-regrowth-ex1",
        vertical="mouth-and-teeth",
        url=ARTICLE_URL,
        outlet="Example News",
        title="Mice regrow teeth",
        published_date=date(2018, 3, 10),
        now=NOW,
    ).claim

    effect, hope = stored_statements(session, claim)
    [promise] = promises_of(session, claim)
    assert (effect.text, effect.kind, effect.firmness, effect.speaker, effect.basis) == (
        EFFECT,
        StatementKind.EFFECT,
        StatementFirmness.FACT,
        StatementSpeaker.ARTICLE,
        StatementBasis.ANIMALS,
    )
    assert (hope.firmness, hope.speaker, hope.basis) == (
        StatementFirmness.POSSIBILITY,
        StatementSpeaker.RESEARCHER,
        StatementBasis.NOT_SAID,
    )
    assert promise.description == "trials in people could begin by 2027"
    assert effect.article_read_at == NOW
    # The model is told the rules: own words, no quotation, no names, timelines apart.
    for rule in (
        "in your own words",
        "never use quotation marks",
        "Never name a person in a statement",
        "A timeline is a promise, never a statement",
        "Only statements about the intervention",
    ):
        assert rule in prompts[0]


def test_article_that_only_announces_a_trial_gives_a_promise_and_no_statement(session: Session):
    """Scenario: Article that only announces a trial"""
    claim = draft(session, DRAFT | {"statements": []})

    assert stored_statements(session, claim) == []
    assert len(promises_of(session, claim)) == 1


def test_a_confident_statement_is_approved_by_rule_and_an_unsure_one_waits(session: Session):
    """Scenarios: Confident statement; Unsure statement"""
    checks = checker(Checks({EFFECT: 0.9, HOPE: 0.6}))

    run = drafted(session, STATEMENT_DRAFT, checks, text=STATEMENT_ARTICLE).statements

    [approved] = run.approved
    [pending] = run.pending
    assert (approved.text, approved.confidence, approved.reviewed_by) == (EFFECT, 0.9, Decider.RULE)
    assert approved.reviewed_at == NOW
    assert (pending.text, pending.confidence, pending.review_state) == (
        HOPE,
        pytest.approx(0.6),
        ReviewState.PENDING,
    )


def test_statements_keep_nothing_of_the_article(session: Session, caplog: pytest.LogCaptureFixture):
    """Scenario: After successful extraction, with statements"""
    caplog.set_level(logging.DEBUG)

    claim = drafted(session, STATEMENT_DRAFT, text=STATEMENT_ARTICLE).claim

    assert len(stored_statements(session, claim)) == 2
    stored = everything_stored(session)
    assert MARKER not in stored and MARKER not in caplog.text
    assert not any(sentence in stored for sentence in STATEMENT_ARTICLE.split(". "))


def test_statements_are_added_for_the_article_of_a_pending_claim(session: Session):
    claim = draft(session, DRAFT | {"statements": []})
    client, _ = llm(session, STATEMENT_DRAFT)

    extracted = extract_into_claim(
        session,
        client,
        checker(),
        claim_slug=claim.slug,
        article_url=ARTICLE_URL,
        text=STATEMENT_ARTICLE,
        now=NOW,
    )

    assert [s.text for s in extracted.statements.stored] == [EFFECT, HOPE]


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
        session,
        client,
        checker(),
        claim_slug="tooth-regrowth-ex1",
        article_url=ARTICLE_URL,
        text=ARTICLE_TEXT,
    ).claim

    [intervention] = entities(session, claim, EntityType.INTERVENTION)
    assert (claim.headline, claim.summary) == ("Operator's headline", "Operator's summary.")
    assert intervention.synonyms == ["EX-1"]
    assert len(entities(session, claim, EntityType.PAPER)) == 1
    assert len(promises_of(session, claim)) == 1


def test_running_extraction_twice_adds_nothing_twice(session: Session):
    claim = draft(session)
    client, _ = llm(session, DRAFT)

    extract_into_claim(
        session,
        client,
        checker(),
        claim_slug=claim.slug,
        article_url=ARTICLE_URL,
        text=ARTICLE_TEXT,
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
            session,
            client,
            checker(),
            claim_slug=claim.slug,
            article_url=ARTICLE_URL,
            text=ARTICLE_TEXT,
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


# --- search phrases for a decided claim ---------------------------------------------


def described_claim(session: Session) -> Claim:
    return add_claim(
        session,
        slug="tics-wrist-stimulation",
        headline="A wrist device was reported to reduce tics",
        vertical="mouth-and-teeth",
        intervention="Wrist-worn median nerve stimulation device",
        indication="Tourette syndrome",
        summary="A small wrist device sends pulses to a nerve.",
    )


def test_decided_claim_is_given_phrases_from_what_it_says_of_itself(session: Session):
    claim = described_claim(session)
    record_decision(claim, ReviewState.APPROVED, by=Decider.RULE, now=NOW)
    client, prompts = llm(
        session, {"search_phrases": ["median nerve stimulation", "the device", "Tourette syndrome"]}
    )

    kept = backfill_search_phrases(session, client, claim)

    [intervention] = entities(session, claim, EntityType.INTERVENTION)
    assert kept == intervention.search_phrases == ["median nerve stimulation"]
    assert "Wrist-worn median nerve stimulation device" in prompts[0]


def test_claim_that_has_a_phrase_is_not_asked_about_again(session: Session):
    claim = described_claim(session)
    client, prompts = llm(session, {"search_phrases": ["median nerve stimulation"]})
    backfill_search_phrases(session, client, claim)

    assert backfill_search_phrases(session, client, claim) == []
    assert len(prompts) == 1


def test_named_drug_given_no_phrase_keeps_none(session: Session):
    claim = described_claim(session)
    client, _ = llm(session, {"search_phrases": []})

    assert backfill_search_phrases(session, client, claim) == []
