"""Reported statements: the refusal rules (pure), the statement check, storing and
deciding statements, and reading a decided claim's article again. Scenario names are
from openspec reported-statements, decision-steps and claim-extraction.

Every article here is synthetic: real article text must never be stored, including in
tests.
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

from thenwhat.claims.entities import add_entity, entities_of
from thenwhat.claims.entry import add_article, add_claim, add_promise, promises_of
from thenwhat.config import Settings
from thenwhat.db.models import Base, Claim, DecisionLog, ReportedStatement, SourceArticle
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import (
    DOES_NOT_SAY,
    SAYS_SOMETHING_WEAKER,
    SAYS_THIS,
    STATEMENT_CHECK,
)
from thenwhat.domain import (
    ClaimStatus,
    Decider,
    EntityType,
    EvidenceStage,
    ReviewState,
    StatementBasis,
    StatementFirmness,
    StatementKind,
    StatementSpeaker,
)
from thenwhat.extract.schema import ProposedStatement
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.review.decisions import record_decision
from thenwhat.statements.rules import Refusal, refusal, statement_key
from thenwhat.statements.service import (
    StatementChecker,
    articles_to_read,
    claims_missing_statements,
    keep_statements,
    read_again,
)

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
LATER = datetime(2026, 11, 27, 10, 0, tzinfo=UTC)
MARKER = "The violet-banded pump hummed beside the incubator all night."
ARTICLE = (
    "A team at Example Institute says a gel called GX-7 cut knee pain for most of the forty"
    f" people in its small study. {MARKER} Doctor Ivo Sample, who led the work, said the gel"
    " could one day spare some patients from knee replacement surgery altogether. A larger"
    " trial is planned for 2027."
)
ARTICLE_URL = "https://news.example.org/2026/knee-gel"


def proposal(statement: str, **overrides: Any) -> ProposedStatement:
    values = {
        "text": statement,
        "kind": StatementKind.EFFECT,
        "firmness": StatementFirmness.FACT,
        "speaker": StatementSpeaker.ARTICLE,
        "basis": StatementBasis.PEOPLE,
    }
    return ProposedStatement(**(values | overrides))


EFFECT = proposal("GX-7 eased knee pain for most people in a small study.")
HOPE = proposal(
    "The gel could spare some people a knee replacement.",
    kind=StatementKind.WHAT_IT_COULD_LEAD_TO,
    firmness=StatementFirmness.POSSIBILITY,
    speaker=StatementSpeaker.RESEARCHER,
    basis=StatementBasis.NOT_SAID,
)


class Checks:
    """A batch backend for the statement check: answers each statement by its text, as
    (choice, probability of that choice). A text given as None gets no answer."""

    name = "fake"

    def __init__(self, by_text: dict[str, tuple[str, float] | None] | None = None) -> None:
        self.by_text = by_text or {}
        self.calls: list[tuple[str, str, list[str]]] = []

    def answer_many(
        self, step: str, intro: str, question: str, items: list[str], options: list[str]
    ) -> list[BackendAnswer | None]:
        self.calls.append((step, intro, items))
        return [self._one(item, options) for item in items]

    def _one(self, item: str, options: list[str]) -> BackendAnswer | None:
        said = item.splitlines()[0].removeprefix("Statement: ")
        reading = self.by_text.get(said, (SAYS_THIS, 0.9))
        if reading is None:
            return None
        choice, p = reading
        rest = (1 - p) / (len(options) - 1)
        return BackendAnswer(choice, {o: p if o == choice else rest for o in options})

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        raise AssertionError("Statements are checked together.")


def claim_with_article(
    session: Session, slug: str = "knee-gel-gx7", intervention: str = "GX-7"
) -> tuple[Claim, SourceArticle]:
    claim = add_claim(
        session,
        slug=slug,
        headline="A gel was reported to ease knee pain",
        vertical="mouth-and-teeth",
        intervention=intervention,
        indication="knee osteoarthritis",
        summary="A gel eased knee pain in a small study.",
    )
    article = add_article(
        session,
        slug,
        url=ARTICLE_URL,
        outlet="Example News",
        title="Gel eases knee pain",
        published_date=date(2026, 3, 1),
    )
    add_entity(session, slug, type=EntityType.PERSON, name="Ivo Sample")
    article.content_hash = hashlib.sha256(ARTICLE.encode()).hexdigest()
    session.flush()
    return claim, article


def keep(
    session: Session,
    article: SourceArticle,
    proposed: list[ProposedStatement],
    backend: Checks | None = None,
    **settings: Any,
):
    return keep_statements(
        session,
        StatementChecker(backend or Checks(), **settings),
        article=article,
        text=ARTICLE,
        proposed=proposed,
        now=NOW,
    )


def check_logs(session: Session) -> list[DecisionLog]:
    return list(
        session.scalars(
            select(DecisionLog).where(DecisionLog.step == STATEMENT_CHECK).order_by(DecisionLog.id)
        )
    )


def everything_stored(session: Session) -> str:
    session.flush()
    return "\n".join(
        str(session.execute(text(f"SELECT * FROM {table.name}")).all())
        for table in Base.metadata.sorted_tables
    )


# --- settings ------------------------------------------------------------------------


def test_statement_settings_have_their_defaults(monkeypatch: pytest.MonkeyPatch):
    for name in ("STATEMENT_ACCEPT_ABOVE", "STATEMENTS_PER_ARTICLE", "STATEMENT_COPIED_RUN"):
        monkeypatch.delenv(name, raising=False)

    settings = Settings(database_url="postgresql://example")

    assert settings.statement_accept_above == 0.8
    assert settings.statements_per_article == 6
    assert settings.statement_copied_run == 8


# --- refusal rules -------------------------------------------------------------------


def refused(statement: str, people: list[str] | None = None, run: int = 8) -> Refusal | None:
    return refusal(statement, article=ARTICLE, people=people or ["Ivo Sample"], copied_run=run)


def test_a_statement_in_its_own_words_is_accepted():
    assert refused(EFFECT.text) is None


def test_a_statement_over_200_characters_is_refused():
    assert refused("GX-7 eased pain. " + "x" * 190) is Refusal.TOO_LONG
    assert refused("x" * 200) is None


@pytest.mark.parametrize(
    "statement",
    [
        'The gel is "a game changer" for knees.',
        "The gel is “a game changer” for knees.",
        "The gel is 'a game changer' for knees.",
        "The gel is ‘a game changer’ for knees.",
        "The gel is «a game changer» for knees.",
    ],
)
def test_a_statement_with_a_quotation_mark_is_refused(statement: str):
    assert refused(statement) is Refusal.QUOTATION


def test_an_apostrophe_is_not_a_quotation():
    assert refused("The gel eased patients' pain and the team’s hopes rose.") is None


@pytest.mark.parametrize(
    "statement",
    ["Ivo Sample expects the gel to spare surgery.", "Sample expects the gel to spare surgery."],
)
def test_a_statement_naming_a_recorded_person_is_refused(statement: str):
    """Scenario: Statement that names a researcher"""
    assert refused(statement) is Refusal.NAMES_A_PERSON


def test_a_title_or_a_word_in_lower_case_is_not_a_name():
    assert refused("A doctor expects the gel to spare surgery.", ["Doctor Ivo Sample"]) is None
    assert refused("A small sample of people took the gel.") is None


def test_a_statement_copying_a_sentence_is_refused():
    """Scenario: Statement that copies a sentence"""
    copied = "The gel could one day spare some patients from knee replacement surgery."

    assert refused(copied) is Refusal.COPIES_THE_ARTICLE


def test_copying_is_compared_on_lower_cased_words():
    assert refused("CUT KNEE PAIN, for most of the forty people!") is Refusal.COPIES_THE_ARTICLE


def test_a_drug_name_with_its_condition_is_not_copying():
    """A run shorter than the setting is the drug, its condition and a few words."""
    article = "Doctors gave GX-7 gel for knee osteoarthritis pain to forty people in Leeds."

    statement = "GX-7 gel for knee osteoarthritis pain eased symptoms in a study."

    assert refusal(statement, article=article, people=[], copied_run=8) is None
    assert refusal(statement, article=article, people=[], copied_run=6) is (
        Refusal.COPIES_THE_ARTICLE
    )


def test_statements_compared_without_case_spacing_or_punctuation_share_a_key():
    assert statement_key("GX-7  eased pain.") == statement_key("gx 7 eased pain")


# --- the statement check -------------------------------------------------------------


def test_each_checked_statement_has_one_log_record_by_article_and_place(session: Session):
    """Scenario: Six statements from one article"""
    _, article = claim_with_article(session)
    six = [proposal(f"GX-7 eased pain in study number {n}.") for n in range(1, 7)]

    keep(session, article, six)

    logs = check_logs(session)
    assert [log.input_ref for log in logs] == [
        f"source_article:{article.id}:statement:{n}" for n in range(1, 7)
    ]
    assert all(log.options == [SAYS_THIS, SAYS_SOMETHING_WEAKER, DOES_NOT_SAY] for log in logs)
    recorded = str([(log.input_ref, log.output, log.error) for log in logs])
    assert MARKER not in recorded and "GX-7 eased pain" not in recorded


def test_the_check_is_shown_the_article_and_how_each_statement_is_put(session: Session):
    _, article = claim_with_article(session)
    checks = Checks()

    keep(session, article, [HOPE], checks)

    [(step, intro, [item])] = checks.calls
    assert step == STATEMENT_CHECK and MARKER in intro
    assert item.splitlines() == [
        f"Statement: {HOPE.text}",
        "Put as: possibility",
        "Said by: researcher",
        "Rests on, as the article gives it: not_said",
    ]


def test_confidence_is_the_probability_that_the_article_says_it(session: Session):
    """Scenarios: Statement the article makes; Statement stronger than the article"""
    _, article = claim_with_article(session)
    checks = Checks({EFFECT.text: (SAYS_THIS, 0.93), HOPE.text: (SAYS_SOMETHING_WEAKER, 0.7)})

    run = keep(session, article, [EFFECT, HOPE], checks)

    made, stronger = run.stored
    assert made.confidence == pytest.approx(0.93)
    assert stronger.confidence == pytest.approx(0.15)
    assert stronger.confidence < 0.5


def test_a_statement_the_backend_fails_on_is_logged_and_not_stored(session: Session):
    """Scenario: Backend failure"""
    _, article = claim_with_article(session)

    run = keep(session, article, [EFFECT, HOPE], Checks({HOPE.text: None}))

    assert [s.text for s in run.stored] == [EFFECT.text]
    assert run.unchecked == 1
    failed = [log for log in check_logs(session) if log.error]
    assert [log.input_ref for log in failed] == [f"source_article:{article.id}:statement:2"]


def test_refused_statements_cost_no_check_and_are_counted(session: Session):
    """Scenario: Statement that copies a sentence"""
    _, article = claim_with_article(session)
    copied = proposal("The gel could one day spare some patients from knee replacement surgery.")
    named = proposal("Sample expects the gel to spare surgery.")
    checks = Checks()

    run = keep(session, article, [copied, named, EFFECT], checks)

    assert run.refused == {Refusal.COPIES_THE_ARTICLE: 1, Refusal.NAMES_A_PERSON: 1}
    [(_, _, items)] = checks.calls
    assert len(items) == 1
    assert [s.text for s in run.stored] == [EFFECT.text]
    # The statement keeps its place among the article's proposals.
    assert run.stored[0].decision_ref == f"source_article:{article.id}:statement:3"


# --- storing and deciding ------------------------------------------------------------


def test_threshold_approves_at_or_above_and_leaves_the_rest_pending(session: Session):
    """Scenarios: Confident statement; Unsure statement"""
    _, article = claim_with_article(session)
    checks = Checks({EFFECT.text: (SAYS_THIS, 0.9), HOPE.text: (SAYS_THIS, 0.6)})

    run = keep(session, article, [EFFECT, HOPE], checks, accept_above=0.8)

    confident, unsure = run.stored
    assert (confident.review_state, confident.reviewed_by, confident.reviewed_at) == (
        ReviewState.APPROVED,
        Decider.RULE,
        NOW,
    )
    assert (unsure.review_state, unsure.reviewed_by) == (ReviewState.PENDING, None)


def test_an_article_keeps_at_most_the_configured_number(session: Session):
    """Scenario: Article that says nine things"""
    _, article = claim_with_article(session)
    nine = [proposal(f"GX-7 eased pain in study number {n}.") for n in range(1, 10)]

    run = keep(session, article, nine, per_article=6)

    assert len(run.stored) == 6 and run.left_out == 3
    assert len(check_logs(session)) == 6


def test_a_statement_is_stored_with_its_article_and_the_time_it_was_read(session: Session):
    claim, article = claim_with_article(session)

    [stored] = keep(session, article, [EFFECT]).stored

    assert (stored.claim_id, stored.source_article_id, stored.article_read_at) == (
        claim.id,
        article.id,
        NOW,
    )
    assert stored.decision_ref == check_logs(session)[0].input_ref


def test_statements_do_not_change_status_or_evidence_stage(session: Session):
    """Scenario: Statement with a basis in people"""
    claim, article = claim_with_article(session)
    claim.evidence_stage = EvidenceStage.ANIMAL

    keep(session, article, [EFFECT])

    assert claim.current_status is ClaimStatus.PRECLINICAL_ONLY
    assert claim.evidence_stage is EvidenceStage.ANIMAL


# --- a decided claim's article, read again -------------------------------------------


def model_returning(*outputs: list[dict[str, Any]]) -> tuple[FunctionModel, list[str]]:
    """A scripted model returning statements, one list per call, and the prompts shown."""
    prompts: list[str] = []
    remaining = list(outputs)

    def respond(messages, info) -> ModelResponse:
        prompts.append(str(messages))
        statements = remaining.pop(0) if len(remaining) > 1 else remaining[0]
        return ModelResponse(
            parts=[ToolCallPart(info.output_tools[0].name, {"statements": statements})]
        )

    return FunctionModel(respond, model_name="scripted"), prompts


def scripted(session: Session, *outputs: list[dict[str, Any]]) -> tuple[Llm, list[str]]:
    model, prompts = model_returning(*outputs)
    settings = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))
    return Llm(session, settings, model=model, now=lambda: NOW), prompts


def as_output(*proposals: ProposedStatement) -> list[dict[str, Any]]:
    return [p.model_dump(mode="json") for p in proposals]


def approved_claim(session: Session) -> tuple[Claim, SourceArticle]:
    claim, article = claim_with_article(session)
    add_promise(session, claim.slug, article_url=ARTICLE_URL, description="a larger trial in 2027")
    record_decision(claim, ReviewState.APPROVED, by=Decider.RULE, now=NOW)
    session.flush()
    return claim, article


def reread(session: Session, article: SourceArticle, llm: Llm, *, now: datetime = NOW, **kw):
    return read_again(
        session, llm, StatementChecker(Checks(**kw)), article=article, text=ARTICLE, now=now
    )


def test_an_approved_claim_gains_statements_and_nothing_else_changes(session: Session):
    """Scenario: Approved claim with no statements"""
    claim, article = approved_claim(session)
    before = (
        claim.headline,
        claim.summary,
        claim.indication,
        claim.review_state,
        [(e.type, e.name, e.synonyms, e.search_phrases) for e in entities_of(session, claim)],
        [p.description for p in promises_of(session, claim)],
        article.content_hash,
    )
    llm, prompts = scripted(session, as_output(EFFECT, HOPE))

    done = reread(session, article, llm)

    assert [s.text for s in done.run.stored] == [EFFECT.text, HOPE.text]
    assert done.changed is False
    after = (
        claim.headline,
        claim.summary,
        claim.indication,
        claim.review_state,
        [(e.type, e.name, e.synonyms, e.search_phrases) for e in entities_of(session, claim)],
        [p.description for p in promises_of(session, claim)],
        article.content_hash,
    )
    assert after == before
    # The model is told which intervention the statements are about, and the rules.
    assert "Intervention: GX-7" in prompts[0] and "never use quotation marks" in prompts[0]


def test_reading_again_keeps_nothing_of_the_article(
    session: Session, caplog: pytest.LogCaptureFixture
):
    caplog.set_level(logging.DEBUG)
    _, article = approved_claim(session)
    llm, _ = scripted(session, as_output(EFFECT, HOPE))

    reread(session, article, llm)

    stored = everything_stored(session)
    assert MARKER not in stored and MARKER not in caplog.text
    assert not any(sentence in stored for sentence in ARTICLE.split(". "))


def test_an_article_whose_text_has_changed_is_said_to_have_changed(session: Session):
    """Scenario: Article whose text has changed"""
    _, article = approved_claim(session)
    first_hash = hashlib.sha256(b"the text as first read").hexdigest()
    article.content_hash = first_hash
    llm, _ = scripted(session, as_output(EFFECT))

    done = reread(session, article, llm)

    assert done.changed is True
    assert len(done.run.stored) == 1
    assert article.content_hash == first_hash


def test_an_article_that_has_statements_is_not_read_again(session: Session):
    """Scenario: Second run with no change"""
    claim, article = approved_claim(session)
    llm, prompts = scripted(session, as_output(EFFECT))
    reread(session, article, llm)

    assert articles_to_read(session, [claim], again=False) == []
    assert articles_to_read(session, [claim], again=True) == [article]
    assert len(prompts) == 1


def test_reading_again_replaces_pending_and_never_recreates_a_rejected_statement(
    session: Session,
):
    """Scenario: Rejected statement found again"""
    _, article = approved_claim(session)
    unsure = proposal("GX-7 may suit people with mild knee pain.")
    llm, _ = scripted(session, as_output(EFFECT, HOPE, unsure))
    first = reread(session, article, llm, by_text={unsure.text: (SAYS_THIS, 0.5)})
    approved, rejected, pending = first.run.stored
    record_decision(rejected, ReviewState.REJECTED, by=Decider.HUMAN, now=NOW)
    session.flush()

    again = reread(session, article, llm, now=LATER, by_text={unsure.text: (SAYS_THIS, 0.95)})

    kept = session.scalars(
        select(ReportedStatement)
        .where(ReportedStatement.source_article_id == article.id)
        .order_by(ReportedStatement.id)
    ).all()
    assert [(s.text, s.review_state) for s in kept] == [
        (EFFECT.text, ReviewState.APPROVED),
        (HOPE.text, ReviewState.REJECTED),
        (unsure.text, ReviewState.APPROVED),
    ]
    assert again.run.known == 2
    assert pending not in kept and approved in kept
    # The second read's check has places of its own.
    assert kept[2].decision_ref == f"source_article:{article.id}:statement:6"


def test_published_claims_with_an_unread_article_are_missing_statements(session: Session):
    claim, article = approved_claim(session)
    pending_claim, _ = claim_with_article(session, "knee-gel-gx8", "GX-8")

    assert claims_missing_statements(session) == [claim]

    llm, _ = scripted(session, as_output(EFFECT))
    reread(session, article, llm)

    assert claims_missing_statements(session) == []
    assert pending_claim.review_state is ReviewState.PENDING
