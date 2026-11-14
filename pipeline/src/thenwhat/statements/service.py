"""Checking, storing and deciding reported statements. Behavior: openspec
reported-statements and claim-extraction.

A statement is proposed by the extraction, refused by rule when it copies its article,
quotes or names someone, checked against the article while its text is in memory, and
stored with the check's probability as its confidence. The text is passed in, shown to
the model, and dropped: nothing here stores, caches or logs it. Nothing here is an input
to a claim's status.
"""

import hashlib
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.db.models import Claim, Entity, ReportedStatement, SourceArticle
from thenwhat.decide.core import Backend
from thenwhat.decide.steps import (
    SAYS_THIS,
    check_statements,
    last_statement_place,
    statement_ref,
)
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.extract.schema import ProposedStatement, StatementsDraft
from thenwhat.review.decisions import record_decision
from thenwhat.statements.rules import Refusal, refusal, statement_key

if TYPE_CHECKING:
    from thenwhat.llm.client import Llm


def statement_rules(limit: int) -> str:
    """What the extraction is told about reported statements."""
    return f"""\
Also list what the article says about the intervention beyond its timeline, as
statements: at most {limit}, the most important first.
Write each statement in your own words, as one sentence under 200 characters. Never copy
a run of the article's words, never quote, and never use quotation marks.
Never name a person in a statement. Say who the article has saying it by role only.
Write the statement itself, not who said it: "It cut pain in a study in mice", not
"The researchers said it cut pain".
Put a statement as fact only when the article states it as fact; otherwise as a possibility.
Its basis is what the article says it rests on: a study in people, a study in animals,
laboratory work, or not said. Take it from the article only.
Only statements about the intervention: what it did, its safety, how it works, who it
could help, how it compares with existing treatment, what it could lead to. Nothing about
people, a company's conduct or prices.
A timeline is a promise, never a statement.
Report what the article says. Do not judge whether it is right.
"""


STATEMENTS_ONLY = """\
You read one news article about a medical research claim and list what it says about the
claim's intervention. Report only what the article says. Do not add facts, and do not
judge the claim.
"""


@dataclass(frozen=True, slots=True)
class StatementChecker:
    """How proposed statements are checked and decided: the decision backend, and the
    settings `STATEMENT_ACCEPT_ABOVE`, `STATEMENTS_PER_ARTICLE` and `STATEMENT_COPIED_RUN`."""

    backend: Backend
    accept_above: float = 0.8
    per_article: int = 6
    copied_run: int = 8


@dataclass(slots=True)
class StatementsRun:
    """What one read of one article did with its statements."""

    proposed: int = 0
    # Proposals refused by rule before any check, by rule.
    refused: Counter[Refusal] = field(default_factory=Counter)
    # Proposals worded as a statement the article already has, in any review state.
    known: int = 0
    # Proposals past the number of statements an article may have.
    left_out: int = 0
    stored: list[ReportedStatement] = field(default_factory=list)
    # Proposals the check gave no usable answer for. None of them is stored.
    unchecked: int = 0

    @property
    def approved(self) -> list[ReportedStatement]:
        return [s for s in self.stored if s.review_state is ReviewState.APPROVED]

    @property
    def pending(self) -> list[ReportedStatement]:
        return [s for s in self.stored if s.review_state is ReviewState.PENDING]


def statements_of(session: Session, article: SourceArticle) -> list[ReportedStatement]:
    return list(
        session.scalars(
            select(ReportedStatement)
            .where(ReportedStatement.source_article_id == article.id)
            .order_by(ReportedStatement.id)
        )
    )


def keep_statements(
    session: Session,
    checker: StatementChecker,
    *,
    article: SourceArticle,
    text: str,
    proposed: Sequence[ProposedStatement],
    now: datetime,
) -> StatementsRun:
    """Refuse, check, store and decide the statements proposed for the article.

    A statement is approved by rule when the check gives it a probability of at least
    `accept_above` that the article says it, and is pending below that. A proposal worded
    like a statement the article already has is skipped, so a rejected statement is not
    created again. One the check gives no usable answer for is not stored.
    """
    run = StatementsRun(proposed=len(proposed))
    existing = statements_of(session, article)
    keys = {statement.text_key for statement in existing}
    room = max(checker.per_article - len(existing), 0)
    people = [e.name for e in _claim_entities(session, article) if e.type is EntityType.PERSON]
    start = last_statement_place(session, article.id)

    asked: list[tuple[str, str, ProposedStatement]] = []
    for place, statement in enumerate(proposed, start=start + 1):
        refused = refusal(
            statement.text, article=text, people=people, copied_run=checker.copied_run
        )
        if refused is not None:
            run.refused[refused] += 1
            continue
        key = statement_key(statement.text)
        if key in keys:
            run.known += 1
            continue
        keys.add(key)
        if len(asked) >= room:
            run.left_out += 1
            continue
        asked.append((statement_ref(article.id, place), key, statement))

    decisions = check_statements(
        session,
        checker.backend,
        article_text=text,
        statements=[(ref, as_checked(statement)) for ref, _, statement in asked],
        now=now,
    )
    for (ref, key, statement), decision in zip(asked, decisions, strict=True):
        if decision is None:
            run.unchecked += 1
            continue
        stored = ReportedStatement(
            claim_id=article.claim_id,
            source_article_id=article.id,
            text=statement.text.strip(),
            text_key=key,
            kind=statement.kind,
            firmness=statement.firmness,
            speaker=statement.speaker,
            basis=statement.basis,
            confidence=decision.probabilities[SAYS_THIS],
            decision_ref=ref,
            article_read_at=now,
        )
        if checker.accept_above > 0 and stored.confidence >= checker.accept_above:
            record_decision(stored, ReviewState.APPROVED, by=Decider.RULE, now=now)
        session.add(stored)
        run.stored.append(stored)
    session.flush()
    return run


def as_checked(statement: ProposedStatement) -> str:
    """A proposed statement as the check is shown it: its text, and how the article is
    said to put it."""
    return (
        f"Statement: {statement.text}\n"
        f"Put as: {statement.firmness.value}\n"
        f"Said by: {statement.speaker.value}\n"
        f"Rests on, as the article gives it: {statement.basis.value}"
    )


def _claim_entities(session: Session, article: SourceArticle) -> list[Entity]:
    claim = session.get(Claim, article.claim_id)
    assert claim is not None
    return entities_of(session, claim)


# --- decided claims: reading an article again for statements only --------------------


@dataclass(frozen=True, slots=True)
class Reread:
    run: StatementsRun
    # Whether the text read now differs from the one first read, by the stored hash.
    # None when no hash was stored.
    changed: bool | None


def read_again(
    session: Session,
    llm: "Llm",
    checker: StatementChecker,
    *,
    article: SourceArticle,
    text: str,
    now: datetime,
) -> Reread:
    """Read an article of a claim in any review state again, for statements only.

    Nothing else about the claim changes: not its headline, summary, intervention,
    indication, promises or entities, and not the article's stored hash, which records
    the first read. Pending statements of the article are replaced; approved and
    rejected ones stay.
    """
    claim = session.get(Claim, article.claim_id)
    assert claim is not None
    intervention = next(
        (e.name for e in entities_of(session, claim) if e.type is EntityType.INTERVENTION), ""
    )
    draft = llm.run(
        "statements",
        instructions=STATEMENTS_ONLY + statement_rules(checker.per_article),
        prompt=(
            f"Intervention: {intervention}\nIndication: {claim.indication}\n\nArticle:\n{text}"
        ),
        output_type=StatementsDraft,
    )
    for statement in statements_of(session, article):
        if statement.review_state is ReviewState.PENDING:
            session.delete(statement)
    session.flush()
    run = keep_statements(
        session, checker, article=article, text=text, proposed=draft.statements, now=now
    )
    changed = None
    if article.content_hash is not None:
        changed = hashlib.sha256(text.encode()).hexdigest() != article.content_hash
    return Reread(run, changed)


def articles_to_read(
    session: Session, claims: Sequence[Claim], *, again: bool
) -> list[SourceArticle]:
    """The claims' articles, in date order, that are to be read for statements: those
    with no statement yet, or all of them when asked to read them again."""
    articles = session.scalars(
        select(SourceArticle)
        .where(SourceArticle.claim_id.in_([claim.id for claim in claims]))
        .order_by(SourceArticle.claim_id, SourceArticle.published_date, SourceArticle.id)
    )
    with_statements = set(session.scalars(select(ReportedStatement.source_article_id)))
    return [a for a in articles if again or a.id not in with_statements]


def claims_missing_statements(session: Session) -> list[Claim]:
    """Every published claim with an article that has no reported statement."""
    with_statements = select(ReportedStatement.source_article_id)
    unread = select(SourceArticle.claim_id).where(SourceArticle.id.not_in(with_statements))
    return list(
        session.scalars(
            select(Claim)
            .where(
                Claim.review_state == ReviewState.APPROVED,
                Claim.archived_at.is_(None),
                Claim.id.in_(unread),
            )
            .order_by(Claim.slug)
        )
    )
