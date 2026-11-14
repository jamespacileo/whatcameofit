"""Looking up the institutions and companies a claim names. Behavior: openspec
entity-resolution, "Organisations are looked up by name" and "A chosen organisation
match is approved by rule".

No model scores or decides these: the score is the organisation registry's own measure
of how well the name matched, and a match is approved by rule only when the registry
itself marks the record as its chosen answer. A person is never looked up, in any
registry or directory.
"""

from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import ORGANISATION_TYPES, entities_of
from thenwhat.db.models import Claim, EntityMatch, OrganisationRecord
from thenwhat.domain import Decider, ReviewState
from thenwhat.resolve.service import MAX_SUMMARY_CHARACTERS
from thenwhat.review.decisions import record_decision
from thenwhat.sources import ror
from thenwhat.sources.base import SourceRecord


class OrganisationRegistry(Protocol):
    def organisations(self, name: str) -> list[SourceRecord]: ...


def organisation_line(record: SourceRecord) -> str:
    """One line on an organisation: its name, country and website."""
    organisation = ror.describe(record)
    parts = [organisation.name, organisation.country, organisation.website or ""]
    return ". ".join(part for part in parts if part)[:MAX_SUMMARY_CHARACTERS]


def keep_record(session: Session, record: SourceRecord) -> OrganisationRecord:
    """Store the organisation's own record, replacing an older copy, so the export can
    say what the registry says of it and when that was read."""
    kept = session.get(OrganisationRecord, (record.source_name, record.external_id))
    if kept is None:
        kept = OrganisationRecord(source_name=record.source_name, external_id=record.external_id)
        session.add(kept)
    if kept.fetched_at is None or record.fetched_at >= kept.fetched_at:
        kept.url = record.url
        kept.payload = ror.organisation_of(record)
        kept.fetched_at = record.fetched_at
    return kept


def match_organisations(
    session: Session, claim: Claim, *, registry: OrganisationRegistry, now: datetime
) -> list[EntityMatch]:
    """Store the organisation the registry matches to each institution and company
    entity of the claim, and approve it by rule when the registry marks it as its chosen
    answer. Returns the matches this run added.

    A name the registry does not know adds nothing. A match that already exists keeps
    its decision: an approved or rejected one is left as it is, and a pending one is
    approved by rule when the registry chooses it again.
    """
    named = [entity for entity in entities_of(session, claim) if entity.type in ORGANISATION_TYPES]
    stored = {
        (match.entity_id, match.source_name, match.external_id): match
        for match in session.scalars(
            select(EntityMatch).where(EntityMatch.entity_id.in_([e.id for e in named]))
        )
    }
    added: list[EntityMatch] = []
    for entity in named:
        for record in registry.organisations(entity.name):
            keep_record(session, record)
            key = (entity.id, record.source_name, record.external_id)
            match = stored.get(key)
            if match is None:
                match = EntityMatch(
                    entity_id=entity.id,
                    source_name=record.source_name,
                    external_id=record.external_id,
                    score=ror.describe(record).name_match,
                    record_summary=organisation_line(record),
                    review_state=ReviewState.PENDING,
                )
                session.add(match)
                stored[key] = match
                added.append(match)
            if match.review_state is ReviewState.PENDING and ror.is_chosen(record):
                record_decision(match, ReviewState.APPROVED, by=Decider.RULE, now=now)
    session.flush()
    return added
