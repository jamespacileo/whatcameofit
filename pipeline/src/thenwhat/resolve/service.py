"""Proposing registry matches for a claim's entities. Behavior: openspec entity-resolution.

Every candidate is stored and scored. A rule rejects one scored near zero and approves
a trial scored high for the claim's indication; the rest wait for review.
"""

from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.db.models import Claim, Entity, EntityMatch
from thenwhat.decide.core import Backend, DecisionFailed
from thenwhat.decide.steps import OTHER_INDICATION, latest_scoring, score_matches
from thenwhat.domain import Decider, EntityType, ReviewState
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord, UnsearchableTerm

MAX_SUMMARY_CHARACTERS = 400


def what_it_says(record: SourceRecord) -> str | None:
    """One line on what a registry record is: for a trial its title, conditions,
    interventions, phase and state; for a paper its title."""
    section = record.payload.get("protocolSection")
    if isinstance(section, dict):
        parts: list[str] = []
        title = section.get("identificationModule", {}).get("briefTitle")
        if title:
            parts.append(str(title).rstrip("."))
        conditions = section.get("conditionsModule", {}).get("conditions", [])
        if conditions:
            parts.append(f"For: {', '.join(conditions)}")
        tested = [
            intervention.get("name")
            for intervention in section.get("armsInterventionsModule", {}).get("interventions", [])
        ]
        if any(tested):
            parts.append(f"Tests: {', '.join(name for name in tested if name)}")
        phases = "/".join(
            _plain_phase(phase) for phase in section.get("designModule", {}).get("phases", [])
        )
        state = section.get("statusModule", {}).get("overallStatus")
        standing = ", ".join(
            part for part in (phases, state.replace("_", " ").lower() if state else "") if part
        )
        if standing:
            parts.append(standing)
        text = ". ".join(parts)
        return f"{text[:MAX_SUMMARY_CHARACTERS]}." if text else None
    title = record.payload.get("title")
    if isinstance(title, list):
        title = title[0] if title else None
    return str(title)[:MAX_SUMMARY_CHARACTERS] if title else None


def _plain_phase(phase: str) -> str:
    if phase == "NA":
        return "No phase"
    words = phase.replace("_", " ").replace("PHASE", "Phase ").split()
    return " ".join(word.capitalize() if word.isalpha() else word for word in words)


class TrialSearch(Protocol):
    def search_trials(
        self, intervention: str, condition: str | None = None
    ) -> list[SourceRecord]: ...

    def search_phrase(self, phrase: str, condition: str | None) -> list[SourceRecord]: ...


def trials_of(
    trials: TrialSearch,
    entity: Entity,
    indication: str | None,
    unsearchable: Callable[[UnsearchableTerm], None] | None = None,
) -> list[SourceRecord]:
    """Every trial the registry holds under the intervention's name, its other names and
    its search phrases. A phrase is searched within the indication only.

    A term the registry cannot search for as written is passed to `unsearchable` and the
    other terms are still searched: each term is its own search. Nothing simpler is
    tried in its place. With no `unsearchable`, the failure is raised.
    """
    searches: list[Callable[[], list[SourceRecord]]] = [
        *(
            (lambda term=term: trials.search_trials(term, indication))
            for term in [entity.name, *entity.synonyms]
        ),
        *(
            (lambda phrase=phrase: trials.search_phrase(phrase, indication))
            for phrase in entity.search_phrases
        ),
    ]
    records: list[SourceRecord] = []
    for search in searches:
        try:
            records += search()
        except UnsearchableTerm as refused:
            if unsearchable is None:
                raise
            unsearchable(refused)
    return records


class DoiLookup(Protocol):
    def work(self, doi: str) -> SourceRecord | None: ...


def resolve_claim(
    session: Session,
    claim: Claim,
    *,
    trials: TrialSearch,
    dois: DoiLookup,
    backend: Backend,
    now: datetime,
    rescore: bool = False,
    reject_below: float = 0.0,
    accept_above: float = 0.0,
    unsearchable: Callable[[UnsearchableTerm], None] | None = None,
) -> list[EntityMatch]:
    """Search the registries for the claim's interventions and papers and store each new
    hit as a scored, pending candidate. Returns the candidates this run added.

    Trials are searched within the claim's indication when the intervention's name is a
    broad one. Candidates that already exist are left exactly as they are, whatever their
    state, unless `rescore` asks for pending ones to be scored again. If a candidate
    cannot be scored, none of this run's candidates are kept.

    A candidate scored under `reject_below` is rejected by rule: kept, out of the review
    queue, and open to the operator to approve. A trial candidate scored for the claim's
    indication at or above `accept_above` is approved by rule; 0 turns that rule off.
    """
    entities = entities_of(session, claim)
    seen = {
        (match.entity_id, match.source_name, match.external_id)
        for match in session.scalars(
            select(EntityMatch).where(EntityMatch.entity_id.in_([e.id for e in entities]))
        )
    }
    found: list[tuple[Entity, SourceRecord]] = []

    def consider(entity: Entity, record: SourceRecord) -> None:
        key = (entity.id, record.source_name, record.external_id)
        if key not in seen:
            seen.add(key)
            found.append((entity, record))

    for entity in entities:
        if entity.type is EntityType.INTERVENTION:
            for record in trials_of(trials, entity, claim.indication, unsearchable):
                consider(entity, record)
        elif entity.type is EntityType.PAPER and entity.doi:
            if any(key[0] == entity.id and key[2].lower() == entity.doi.lower() for key in seen):
                continue  # Its DOI already has a match, such as an origin paper set by rule.
            record = dois.work(entity.doi)
            if record is not None:
                consider(entity, record)

    added: list[EntityMatch] = []
    for entity, record in found:
        match = EntityMatch(
            entity_id=entity.id,
            source_name=record.source_name,
            external_id=record.external_id,
            score=0.0,
            record_summary=what_it_says(record),
        )
        session.add(match)
        added.append(match)
    session.flush()
    try:
        score_matches(
            session,
            backend,
            claim=claim,
            candidates=[
                (entity, match, record)
                for (entity, record), match in zip(found, added, strict=True)
            ],
            now=now,
        )
    except DecisionFailed:
        # The decision log keeps the failure; the unscored candidates are withdrawn.
        for match in added:
            session.delete(match)
        session.flush()
        raise
    reject_near_zero(added, reject_below, now)
    approve_confident(session, added, accept_above, now)
    session.flush()
    if rescore:
        rescore_claim(
            session,
            claim,
            trials=trials,
            backend=backend,
            now=now,
            skip=added,
            reject_below=reject_below,
            accept_above=accept_above,
            unsearchable=unsearchable,
        )
    return added


def reject_near_zero(scored: list[EntityMatch], reject_below: float, now: datetime) -> None:
    for match in scored:
        if match.review_state is ReviewState.PENDING and match.score < reject_below:
            record_decision(match, ReviewState.REJECTED, by=Decider.RULE, now=now)


def _scored_for_the_indication(session: Session, match: EntityMatch) -> bool:
    """True when the latest scoring asked about the claim's indication and did not read
    the record as the same intervention for another indication."""
    scored = latest_scoring(session, match)
    if scored is None or scored.output is None:
        return False
    return OTHER_INDICATION in scored.options and scored.output.get("choice") != OTHER_INDICATION


def approve_confident(
    session: Session, scored: list[EntityMatch], accept_above: float, now: datetime
) -> None:
    """Approve by rule the trial candidates scored for the indication at or above the
    threshold. Openspec auto-publish: "Confident candidates are approved by rule"."""
    if accept_above <= 0:
        return
    for match in scored:
        entity = session.get(Entity, match.entity_id)
        if (
            match.review_state is ReviewState.PENDING
            and match.score >= accept_above
            and entity is not None
            and entity.type is EntityType.INTERVENTION
            and _scored_for_the_indication(session, match)
        ):
            record_decision(match, ReviewState.APPROVED, by=Decider.RULE, now=now)


def rescore_claim(
    session: Session,
    claim: Claim,
    *,
    trials: TrialSearch,
    backend: Backend,
    now: datetime,
    skip: list[EntityMatch] | None = None,
    reject_below: float = 0.0,
    accept_above: float = 0.0,
    unsearchable: Callable[[UnsearchableTerm], None] | None = None,
) -> list[EntityMatch]:
    """Score again the pending trial candidates that the search still returns, and return
    them. For candidates scored before the indication was part of the question.

    A candidate someone has decided keeps the score it was decided on. A pending
    candidate the search no longer returns keeps its old score, and the review queue
    says how it was scored.
    """
    just_scored = {match.id for match in skip or []}
    again: list[tuple[Entity, EntityMatch, SourceRecord]] = []
    for entity in entities_of(session, claim):
        if entity.type is not EntityType.INTERVENTION:
            continue
        pending = {
            (match.source_name, match.external_id): match
            for match in session.scalars(
                select(EntityMatch).where(
                    EntityMatch.entity_id == entity.id,
                    EntityMatch.review_state == ReviewState.PENDING,
                )
            )
            if match.id not in just_scored
        }
        for record in trials_of(trials, entity, claim.indication, unsearchable):
            match = pending.pop((record.source_name, record.external_id), None)
            if match is not None:
                match.record_summary = what_it_says(record)
                again.append((entity, match, record))
    score_matches(session, backend, claim=claim, candidates=again, now=now)
    rescored = [match for _, match, _ in again]
    reject_near_zero(rescored, reject_below, now)
    approve_confident(session, rescored, accept_above, now)
    session.flush()
    return rescored
