"""Proposing, scoring and deciding subject terms for a claim, and keeping each term's
record. Behavior: openspec knowledge-cards.

A link between a claim and a term never rests on a lookup or on the registry's filing
alone: every candidate is put to the term check, and rules decide on its score. Nothing
here is an input to a claim's status.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.claims.mesh_areas import approved_trial_payloads
from thenwhat.db.models import Claim, ClaimTerm, TermRecord
from thenwhat.decide.core import Backend
from thenwhat.decide.steps import BROADER, SAME, check_terms
from thenwhat.domain import Decider, EntityType, ReviewState, TermFit, TermRole
from thenwhat.review.decisions import record_decision
from thenwhat.sources import mesh
from thenwhat.sources.base import SourceRecord
from thenwhat.terms.candidates import LabelMatch, gather_candidates

# A stored term record older than this is fetched again.
RECORD_MAX_AGE = timedelta(days=90)
FITS = {SAME: TermFit.EXACT, BROADER: TermFit.BROADER}


class Vocabulary(Protocol):
    name: str

    def term(self, identifier: str, *, force: bool = False) -> SourceRecord | None: ...

    def terms_labelled(self, name: str) -> list[mesh.LabelledTerm]: ...


@dataclass(frozen=True, slots=True)
class TermsRun:
    """What one run did for a claim."""

    # Every candidate gathered by rule, new or not.
    gathered: int
    # The candidates this run stored for the first time.
    added: list[ClaimTerm]
    # The candidates this run got an answer for, with the rule's decision applied.
    scored: list[ClaimTerm]
    # The candidates the backend gave no usable answer for. They stay without a score.
    unscored: list[ClaimTerm]


def terms_of(session: Session, claim: Claim) -> list[ClaimTerm]:
    return list(
        session.scalars(
            select(ClaimTerm).where(ClaimTerm.claim_id == claim.id).order_by(ClaimTerm.id)
        )
    )


def stored_record(
    session: Session, vocabulary: Vocabulary, identifier: str, *, now: datetime
) -> TermRecord | None:
    """The term's own record, fetched when none is stored or the stored one is older
    than ninety days. A term the vocabulary does not hold has no record; a refresh that
    finds nothing leaves the stored record as it is."""
    kept = session.get(TermRecord, (vocabulary.name, identifier))
    if kept is not None and now - kept.fetched_at <= RECORD_MAX_AGE:
        return kept
    record = vocabulary.term(identifier, force=kept is not None)
    if record is None:
        return kept
    if kept is None:
        kept = TermRecord(source_name=record.source_name, external_id=record.external_id)
        session.add(kept)
    kept.url = record.url
    kept.payload = record.payload
    kept.fetched_at = record.fetched_at
    session.flush()
    return kept


def _definition(record: TermRecord | None) -> str | None:
    if record is None:
        return None
    return mesh.describe(
        SourceRecord(
            record.source_name, record.external_id, record.url, record.payload, record.fetched_at
        )
    ).definition


def _label_matches(session: Session, claim: Claim, vocabulary: Vocabulary) -> list[LabelMatch]:
    """Vocabulary terms whose label equals the claim's indication, its intervention's
    name or one of the intervention's other names. Search phrases are not names."""
    names = [(TermRole.CONDITION, claim.indication)]
    for entity in entities_of(session, claim):
        if entity.type is EntityType.INTERVENTION:
            names += [(TermRole.INTERVENTION, name) for name in [entity.name, *entity.synonyms]]
    return [
        LabelMatch(role, term.identifier, term.label, name)
        for role, name in names
        if name.strip()
        for term in vocabulary.terms_labelled(name)
    ]


def link_terms(
    session: Session,
    claim: Claim,
    *,
    vocabulary: Vocabulary,
    backend: Backend,
    now: datetime,
    limit: int = 10,
    accept_above: float = 0.0,
    reject_below: float = 0.0,
) -> TermsRun:
    """Gather the claim's candidate subject terms, score those without a score and
    decide them by rule, and keep the record of every approved term.

    A candidate's score is the probability of the answer chosen when the term was read
    as the claim's own condition or intervention, or as broader, and zero otherwise. One
    scored at or above `accept_above` is approved by rule (0 turns that off); one under
    `reject_below` is rejected by rule; the rest wait for review. A candidate that
    already has a score is left exactly as it is, so a link the operator rejected stays
    rejected.
    """
    candidates = gather_candidates(
        trial_payloads=approved_trial_payloads(session, claim),
        label_matches=_label_matches(session, claim, vocabulary),
        limit=limit,
    )
    known = {(term.role, term.source_name, term.external_id) for term in terms_of(session, claim)}
    added: list[ClaimTerm] = []
    for candidate in candidates:
        key = (candidate.role, candidate.source_name, candidate.identifier)
        if key in known:
            continue
        known.add(key)
        term = ClaimTerm(
            claim_id=claim.id,
            role=candidate.role,
            source_name=candidate.source_name,
            external_id=candidate.identifier,
            label=candidate.label,
            reasons=list(candidate.reasons),
        )
        session.add(term)
        added.append(term)
    session.flush()

    waiting = [
        term
        for term in terms_of(session, claim)
        if term.score is None and term.review_state is ReviewState.PENDING
    ]
    scored: list[ClaimTerm] = []
    unscored: list[ClaimTerm] = []
    for role in TermRole:
        asked = [
            (term, _definition(stored_record(session, vocabulary, term.external_id, now=now)))
            for term in waiting
            if term.role is role
        ]
        if not asked:
            continue
        decisions = check_terms(session, backend, claim=claim, role=role, candidates=asked, now=now)
        for (term, _), decision in zip(asked, decisions, strict=True):
            if decision is None:
                unscored.append(term)
                continue
            term.fit = FITS.get(decision.choice)
            score = decision.probabilities[decision.choice] if term.fit else 0.0
            term.score = score
            if accept_above > 0 and score >= accept_above:
                record_decision(term, ReviewState.APPROVED, by=Decider.RULE, now=now)
            elif score < reject_below:
                record_decision(term, ReviewState.REJECTED, by=Decider.RULE, now=now)
            scored.append(term)

    for term in terms_of(session, claim):
        if term.review_state is ReviewState.APPROVED:
            stored_record(session, vocabulary, term.external_id, now=now)
    session.flush()
    return TermsRun(len(candidates), added, scored, unscored)


def claims_without_terms(session: Session) -> list[Claim]:
    """Every published claim that has no candidate subject term yet."""
    linked = select(ClaimTerm.claim_id)
    return list(
        session.scalars(
            select(Claim)
            .where(
                Claim.review_state == ReviewState.APPROVED,
                Claim.archived_at.is_(None),
                Claim.id.not_in(linked),
            )
            .order_by(Claim.slug)
        )
    )
