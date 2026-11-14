"""The review queue and the operator's decisions. Behavior: openspec review.

Decisions here are the operator's, or the assistant's when it is named. Rule decisions
are made where drafts, matches and events are created.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import ClaimNotFound, EntryError, InvalidUrl, claim_by_slug
from thenwhat.claims.status import refresh_status
from thenwhat.db.models import (
    Claim,
    ClaimTerm,
    DecisionLog,
    Entity,
    EntityMatch,
    EvidenceEvent,
    FailureFlag,
    SourceArticle,
)
from thenwhat.decide.steps import (
    BROADER,
    ENTITY_MATCH,
    EVIDENCE_STAGE,
    MATCH,
    NOT_A_MATCH,
    OTHER_INDICATION,
    PAPER_MATCH,
    SAME,
    SOMETHING_ELSE,
    TERM_MATCH,
    latest_scoring,
    match_ref,
    term_ref,
)
from thenwhat.domain import Decider, EntityType, EvidenceStage, ReviewState, TermFit
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import record_url
from thenwhat.sources.openalex import OpenAlex

Kind = Literal["claim", "match", "event", "term"]


class ItemNotFound(EntryError):
    pass


@dataclass(frozen=True, slots=True)
class QueueItem:
    kind: Kind
    id: int
    claim_slug: str
    assertion: str
    source_url: str | None
    score: float | None
    # For a candidate match: what the registry record says, when that was kept.
    detail: str | None = None
    # For a paper candidate: the reason codes found by rule. Empty when it shows none.
    reasons: tuple[str, ...] = ()


def pending_items(
    session: Session, *, claim_slug: str | None = None, kind: Kind | None = None
) -> list[QueueItem]:
    """What awaits review, claim by claim: the draft claim, then candidate matches
    (most likely first), then events (oldest first), then candidate subject terms (most
    likely first, those without a score last)."""
    claims = list(session.scalars(select(Claim).order_by(Claim.id)))
    if claim_slug is not None:
        claims = [claim for claim in claims if claim.slug == claim_slug]
        if not claims:
            raise ClaimNotFound(f"No claim has the slug '{claim_slug}'.")

    items: list[QueueItem] = []
    for claim in claims:
        if claim.review_state is ReviewState.PENDING:
            article = session.scalars(
                select(SourceArticle.url)
                .where(SourceArticle.claim_id == claim.id)
                .order_by(SourceArticle.published_date)
            ).first()
            items.append(
                QueueItem(
                    "claim", claim.id, claim.slug, f"Draft claim: {claim.headline}", article, None
                )
            )
        for match, entity in session.execute(
            select(EntityMatch, Entity)
            .join(Entity, Entity.id == EntityMatch.entity_id)
            .where(Entity.claim_id == claim.id, EntityMatch.review_state == ReviewState.PENDING)
            .order_by(EntityMatch.score.desc(), EntityMatch.id)
        ):
            items.append(_match_item(session, claim, match, entity))
        for event in session.scalars(
            select(EvidenceEvent)
            .where(
                EvidenceEvent.claim_id == claim.id,
                EvidenceEvent.review_state == ReviewState.PENDING,
            )
            .order_by(EvidenceEvent.event_date, EvidenceEvent.id)
        ):
            items.append(
                QueueItem(
                    "event",
                    event.id,
                    claim.slug,
                    f"{event.event_date} {event.type.value}: {event.summary}",
                    event.source_url,
                    event.confidence,
                )
            )
        for term in session.scalars(
            select(ClaimTerm)
            .where(ClaimTerm.claim_id == claim.id, ClaimTerm.review_state == ReviewState.PENDING)
            .order_by(ClaimTerm.score.desc().nulls_last(), ClaimTerm.id)
        ):
            items.append(_term_item(claim, term))
    return [item for item in items if kind is None or item.kind == kind]


def _match_item(session: Session, claim: Claim, match: EntityMatch, entity: Entity) -> QueueItem:
    link = record_url(match.source_name, match.external_id)
    if _is_paper_candidate(match, entity):
        # Its detail line carries the title, year, kind of paper and journal.
        found = ", ".join(match.reasons) if match.reasons else "none found by rule"
        return QueueItem(
            "match",
            match.id,
            claim.slug,
            f"related paper {match.external_id} for {entity.type.value} '{entity.name}'"
            f"{_score_note(session, match, entity)}. Reasons: {found}",
            link,
            match.score,
            match.record_summary,
            tuple(match.reasons),
        )
    return QueueItem(
        "match",
        match.id,
        claim.slug,
        f"{entity.type.value} '{entity.name}' is {match.source_name}"
        f" record {match.external_id}{_score_note(session, match, entity)}",
        link,
        match.score,
        match.record_summary,
    )


def _term_item(claim: Claim, term: ClaimTerm) -> QueueItem:
    if term.score is None:
        read = "not scored yet: run `terms` for the claim"
    elif term.fit is None:
        read = "read as something else"
    else:
        read = f"read as {term.fit.value}"
    told = "; ".join(_reason_line(reason) for reason in term.reasons) or "none found by rule"
    return QueueItem(
        "term",
        term.id,
        claim.slug,
        f"subject term '{term.label}' ({term.source_name} {term.external_id}) for the"
        f" claim's {term.role.value}, {read}. Reasons: {told}",
        record_url(term.source_name, term.external_id),
        term.score,
        reasons=tuple(str(reason.get("code")) for reason in term.reasons),
    )


def _reason_line(reason: dict) -> str:
    if "trials" in reason:
        return f"{reason.get('code')} ({reason['trials']} of {reason.get('of')} trials)"
    if "name" in reason:
        return f"{reason.get('code')} ('{reason['name']}')"
    return str(reason.get("code"))


def _is_paper_candidate(match: EntityMatch, entity: Entity) -> bool:
    """A paper the literature search found for the claim's intervention."""
    return entity.type is EntityType.INTERVENTION and match.source_name == OpenAlex.name


def rejected_by_rule(session: Session, *, claim_slug: str | None = None) -> list[QueueItem]:
    """The candidate matches a rule rejected for scoring near zero, likeliest first, for
    all claims or for one. The operator can approve any of them."""
    query = (
        select(EntityMatch, Entity, Claim)
        .join(Entity, Entity.id == EntityMatch.entity_id)
        .join(Claim, Claim.id == Entity.claim_id)
        .where(
            EntityMatch.review_state == ReviewState.REJECTED,
            EntityMatch.reviewed_by == Decider.RULE,
        )
        .order_by(Claim.id, EntityMatch.score.desc(), EntityMatch.id)
    )
    if claim_slug is not None:
        claim_by_slug(session, claim_slug)
        query = query.where(Claim.slug == claim_slug)
    return [
        _match_item(session, claim, match, entity)
        for match, entity, claim in session.execute(query)
    ]


def _score_note(session: Session, match: EntityMatch, entity: Entity) -> str:
    """What the reviewer should know about how a trial candidate's score was reached."""
    if entity.type is not EntityType.INTERVENTION:
        return ""
    scored = latest_scoring(session, match)
    if scored is None or scored.output is None:
        return ""
    if OTHER_INDICATION not in scored.options:
        return " (scored without the indication: run `resolve --rescore`)"
    if scored.output.get("choice") == OTHER_INDICATION:
        return " (read as the same intervention for another indication)"
    return ""


def decide_item(
    session: Session,
    kind: Kind,
    item_id: int,
    state: ReviewState,
    *,
    now: datetime,
    no_signal_years: int = 3,
    by: Decider = Decider.HUMAN,
) -> None:
    """Approve or reject an item, or change an earlier decision.

    The decider is the operator unless the assistant is named. A decision on an event
    re-derives the claim's status; one on a subject term never touches it. The
    operator's decision on a match is recorded as the human label for the score it was
    given; the assistant's is not, because a label is a person's answer. Rejecting a
    match also rejects the events read from it.
    """
    if by not in (Decider.HUMAN, Decider.ASSISTANT):
        raise ValueError("A review decision is made by the operator or the assistant.")
    if kind == "claim":
        claim = session.get(Claim, item_id)
        if claim is None:
            raise ItemNotFound(f"There is no claim with id {item_id}.")
        if state is ReviewState.APPROVED and not claim.summary.strip():
            raise EntryError(
                f"Claim '{claim.slug}' has no summary. Add one with `claim edit` before approving."
            )
        record_decision(claim, state, by=by, now=now)
    elif kind == "match":
        match = session.get(EntityMatch, item_id)
        if match is None:
            raise ItemNotFound(f"There is no match with id {item_id}.")
        record_decision(match, state, by=by, now=now)
        if by is Decider.HUMAN:
            label = MATCH if state is ReviewState.APPROVED else NOT_A_MATCH
            _label(session, ENTITY_MATCH, match_ref(match.id), label)
            if state is ReviewState.APPROVED:
                # A rejection does not say which of a paper's other answers was right.
                _label(session, PAPER_MATCH, match_ref(match.id), MATCH)
        entity = session.get(Entity, match.entity_id)
        assert entity is not None
        claim = session.get(Claim, entity.claim_id)
        assert claim is not None
        if state is ReviewState.REJECTED:
            for event in session.scalars(
                select(EvidenceEvent).where(
                    EvidenceEvent.entity_match_id == match.id,
                    EvidenceEvent.review_state != ReviewState.REJECTED,
                )
            ):
                record_decision(event, ReviewState.REJECTED, by=by, now=now)
            session.flush()
            refresh_status(
                session, claim, as_of=now.date(), now=now, no_signal_years=no_signal_years
            )
    elif kind == "term":
        term = session.get(ClaimTerm, item_id)
        if term is None:
            raise ItemNotFound(f"There is no subject term link with id {item_id}.")
        record_decision(term, state, by=by, now=now)
        if by is Decider.HUMAN:
            # An approval says the reading was right; a rejection, that the term is
            # something else. An approval of a term never read as either labels nothing.
            label = SOMETHING_ELSE
            if state is ReviewState.APPROVED:
                label = {TermFit.EXACT: SAME, TermFit.BROADER: BROADER}.get(term.fit)
            if label is not None:
                _label(session, TERM_MATCH, term_ref(term), label)
    else:
        event = session.get(EvidenceEvent, item_id)
        if event is None:
            raise ItemNotFound(f"There is no event with id {item_id}.")
        record_decision(event, state, by=by, now=now)
        session.flush()
        claim = session.get(Claim, event.claim_id)
        assert claim is not None
        refresh_status(session, claim, as_of=now.date(), now=now, no_signal_years=no_signal_years)
    session.flush()


def decide_matches(
    session: Session,
    claim_slug: str,
    state: ReviewState,
    *,
    now: datetime,
    at_least: float | None = None,
    below: float | None = None,
    no_signal_years: int = 3,
    by: Decider = Decider.HUMAN,
) -> list[int]:
    """Approve or reject, in one go, a claim's pending candidates on one side of a score.
    Returns the ids decided. Candidates already decided are left as they are."""
    if (at_least is None) == (below is None):
        raise EntryError("Give one of --at-least and --below.")
    claim = claim_by_slug(session, claim_slug)
    pending = session.scalars(
        select(EntityMatch)
        .join(Entity, Entity.id == EntityMatch.entity_id)
        .where(Entity.claim_id == claim.id, EntityMatch.review_state == ReviewState.PENDING)
        .order_by(EntityMatch.id)
    ).all()
    chosen = [
        match.id
        for match in pending
        if (at_least is not None and match.score >= at_least)
        or (below is not None and match.score < below)
    ]
    for match_id in chosen:
        decide_item(
            session, "match", match_id, state, now=now, no_signal_years=no_signal_years, by=by
        )
    return chosen


def flag_failure(
    session: Session,
    claim_slug: str,
    *,
    trial_id: str,
    event_id: int,
    source_url: str,
    now: datetime,
    no_signal_years: int = 3,
) -> FailureFlag:
    """Record that a trial missed its primary endpoint. This is the only way a claim
    can become failed, and it needs an approved event and a source link."""
    claim = claim_by_slug(session, claim_slug)
    source_url = source_url.strip()
    if not source_url.startswith(("http://", "https://")):
        raise InvalidUrl("A failure flag needs a source link starting with http:// or https://.")
    trial_id = trial_id.strip()
    if not trial_id:
        raise EntryError("A failure flag must name the trial.")
    event = session.get(EvidenceEvent, event_id)
    if event is None or event.claim_id != claim.id:
        raise ItemNotFound(f"Claim '{claim.slug}' has no event with id {event_id}.")
    if event.review_state is not ReviewState.APPROVED:
        raise EntryError("A failure flag must rest on an approved event. Approve it first.")
    already = session.scalars(
        select(FailureFlag.id).where(
            FailureFlag.claim_id == claim.id, FailureFlag.trial_external_id == trial_id
        )
    ).first()
    if already is not None:
        raise EntryError(f"Trial {trial_id} already has a failure flag.")

    flag = FailureFlag(
        claim_id=claim.id,
        trial_external_id=trial_id,
        evidence_event_id=event.id,
        source_url=source_url,
        created_at=now,
    )
    session.add(flag)
    session.flush()
    refresh_status(session, claim, as_of=now.date(), now=now, no_signal_years=no_signal_years)
    return flag


def confirm_stage(
    session: Session,
    claim_slug: str,
    stage: EvidenceStage,
    *,
    now: datetime,
    no_signal_years: int = 3,
    by: Decider = Decider.HUMAN,
) -> Claim:
    """Set the stage of evidence at announcement and bring the status up to date: with
    no trial found, the stage decides between two statuses. The operator's choice becomes
    the human label for whatever was suggested; the assistant's choice labels nothing."""
    claim = claim_by_slug(session, claim_slug)
    claim.evidence_stage = stage
    if by is Decider.HUMAN:
        _label(session, EVIDENCE_STAGE, f"claim:{claim.id}", stage.value)
    session.flush()
    refresh_status(session, claim, as_of=now.date(), now=now, no_signal_years=no_signal_years)
    return claim


def _label(session: Session, step: str, input_ref: str, label: str) -> None:
    for entry in session.scalars(
        select(DecisionLog).where(
            DecisionLog.step == step,
            DecisionLog.input_ref == input_ref,
            DecisionLog.error.is_(None),
        )
    ):
        entry.human_label = label
