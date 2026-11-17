"""What each claim step reads of a claim, and noticing when it changed.

A claim's input lives in several tables: its intervention's names, its approved matches,
its approved trial events, its articles. Whatever changes them (a correction, a review, a
read that joins an article, another step), the steps' entries are compared with what the
claims hold now before a run, and each whose input changed is marked stale, as the
ledger's `mark_changed` does for one record, so the claim is due again for that step.
Each kind of input is asked for once for every claim compared. Behavior: openspec
work-ledger, "Due work".
"""

from collections.abc import Sequence
from functools import cached_property
from typing import Any, Protocol

from sqlalchemy import func, or_, select, tuple_
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, Entity, EntityMatch, EvidenceEvent, SourceArticle, WorkEntry
from thenwhat.domain import TRIAL_EVENT_TYPES, EntityType, ReviewState
from thenwhat.work.ledger import fingerprint

CLAIM = "claim"


class Inputs:
    """What the claim steps read of a set of claims, each kind asked for once."""

    def __init__(self, session: Session, ids: Sequence[int]) -> None:
        self._session = session
        self._ids = list(ids)

    @cached_property
    def names(self) -> dict[int, dict[str, Any]]:
        """Each claim's intervention's names and search phrases, its indication, and when
        a new registry search was last asked for it."""
        rows = self._session.execute(
            select(
                Claim.id,
                Claim.indication,
                Claim.registry_search_due_at,
                Entity.name,
                Entity.synonyms,
                Entity.search_phrases,
            )
            .outerjoin(
                Entity, (Entity.claim_id == Claim.id) & (Entity.type == EntityType.INTERVENTION)
            )
            .where(Claim.id.in_(self._ids))
        )
        return {
            row.id: {
                "name": row.name,
                "synonyms": sorted(row.synonyms or []),
                "phrases": sorted(row.search_phrases or []),
                "indication": row.indication,
                "search_asked_at": row.registry_search_due_at,
            }
            for row in rows
        }

    @cached_property
    def paper_dois(self) -> dict[int, list[str]]:
        rows = self._session.execute(
            select(Entity.claim_id, Entity.id, Entity.doi).where(
                Entity.claim_id.in_(self._ids),
                Entity.type == EntityType.PAPER,
                Entity.doi.is_not(None),
            )
        )
        return _grouped(
            (claim_id, f"{entity_id}:{doi.lower()}") for claim_id, entity_id, doi in rows if doi
        )

    @cached_property
    def approved(self) -> dict[int, list[str]]:
        """Each claim's approved matches, as source and identifier."""
        rows = self._session.execute(
            select(Entity.claim_id, EntityMatch.source_name, EntityMatch.external_id)
            .join(EntityMatch, EntityMatch.entity_id == Entity.id)
            .where(Entity.claim_id.in_(self._ids), EntityMatch.review_state == ReviewState.APPROVED)
        )
        return _grouped((row.claim_id, f"{row.source_name} {row.external_id}") for row in rows)

    @cached_property
    def trial_events(self) -> dict[int, list[str]]:
        """Each claim's approved trial events: the stored registry records its trial
        readings are read from."""
        rows = self._session.execute(
            select(EvidenceEvent.claim_id, EvidenceEvent.id).where(
                EvidenceEvent.claim_id.in_(self._ids),
                EvidenceEvent.review_state == ReviewState.APPROVED,
                EvidenceEvent.type.in_(TRIAL_EVENT_TYPES),
            )
        )
        return _grouped((row.claim_id, str(row.id)) for row in rows)

    @cached_property
    def unread(self) -> dict[int, list[str]]:
        """Each claim's articles that have not been read."""
        rows = self._session.execute(
            select(SourceArticle.claim_id, SourceArticle.id).where(
                SourceArticle.claim_id.in_(self._ids), SourceArticle.content_hash.is_(None)
            )
        )
        return _grouped((row.claim_id, str(row.id)) for row in rows)

    @cached_property
    def named(self) -> dict[int, list[str]]:
        """The registry numbers and DOIs each claim's articles' pages name."""
        rows = self._session.execute(
            select(
                SourceArticle.claim_id,
                SourceArticle.named_registry_numbers,
                SourceArticle.named_dois,
            ).where(SourceArticle.claim_id.in_(self._ids))
        )
        return _grouped(
            (row.claim_id, identifier.lower())
            for row in rows
            for identifier in (*row.named_registry_numbers, *row.named_dois)
        )


def _grouped(pairs: Any) -> dict[int, list[str]]:
    grouped: dict[int, set[str]] = {}
    for claim_id, value in pairs:
        grouped.setdefault(claim_id, set()).add(value)
    return {claim_id: sorted(values) for claim_id, values in grouped.items()}


class Reads(Protocol):
    name: str
    version: int
    record_kind: str

    def read(self, inputs: Inputs, claim_id: int) -> dict[str, Any]: ...


def notice_changes(session: Session, steps: Sequence[Reads]) -> int:
    """Mark stale each claim step's entry whose claim no longer holds the input the entry
    was made for, so the claim is due again for that step. Returns how many were marked."""
    claim_steps = {step.name: step for step in steps if step.record_kind == CLAIM}
    if not claim_steps:
        return 0
    entries = list(
        session.scalars(
            select(WorkEntry).where(
                WorkEntry.record_kind == CLAIM,
                WorkEntry.stale.is_(False),
                tuple_(WorkEntry.step, WorkEntry.step_version).in_(
                    [(step.name, step.version) for step in claim_steps.values()]
                ),
            )
        )
    )
    inputs = Inputs(session, sorted({entry.record_id for entry in entries}))
    marked = 0
    for entry in entries:
        read = claim_steps[entry.step].read(inputs, entry.record_id)
        if entry.fingerprint != fingerprint(read):
            entry.stale = True
            marked += 1
    session.flush()
    return marked


def names_a_record() -> Any:
    """The condition of a claim one of whose articles' pages names a registry number or
    a DOI."""
    return (
        select(SourceArticle.id)
        .where(
            SourceArticle.claim_id == Claim.id,
            or_(
                func.cardinality(SourceArticle.named_registry_numbers) > 0,
                func.cardinality(SourceArticle.named_dois) > 0,
            ),
        )
        .exists()
    )
