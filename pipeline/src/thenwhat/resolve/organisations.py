"""Looking up the institutions and companies a claim's article named. Behavior:
openspec entity-resolution, "Organisations are looked up by name".

No model scores these: the score is the organisation registry's own measure of how well
the name matched. A person is never looked up, in any registry or directory.
"""

from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.db.models import Claim, EntityMatch
from thenwhat.domain import EntityType
from thenwhat.resolve.service import MAX_SUMMARY_CHARACTERS
from thenwhat.sources import ror
from thenwhat.sources.base import SourceRecord


class OrganisationRegistry(Protocol):
    def organisations(self, name: str) -> list[SourceRecord]: ...


def organisation_line(record: SourceRecord) -> str:
    """One line on an organisation: its name, country and website."""
    organisation = ror.describe(record)
    parts = [organisation.name, organisation.country, organisation.website or ""]
    return ". ".join(part for part in parts if part)[:MAX_SUMMARY_CHARACTERS]


def match_organisations(
    session: Session, claim: Claim, *, registry: OrganisationRegistry
) -> list[EntityMatch]:
    """Store, as a pending candidate, the organisation the registry matches to each
    institution and company entity of the claim. Returns the candidates this run added.

    A name the registry does not know adds nothing. A candidate that already exists is
    left exactly as it is.
    """
    named = [
        entity
        for entity in entities_of(session, claim)
        if entity.type in (EntityType.INSTITUTION, EntityType.COMPANY)
    ]
    seen = {
        (match.entity_id, match.source_name, match.external_id)
        for match in session.scalars(
            select(EntityMatch).where(EntityMatch.entity_id.in_([e.id for e in named]))
        )
    }
    added: list[EntityMatch] = []
    for entity in named:
        for record in registry.organisations(entity.name):
            key = (entity.id, record.source_name, record.external_id)
            if key in seen:
                continue
            seen.add(key)
            match = EntityMatch(
                entity_id=entity.id,
                source_name=record.source_name,
                external_id=record.external_id,
                score=ror.describe(record).name_match,
                record_summary=organisation_line(record),
            )
            session.add(match)
            added.append(match)
    session.flush()
    return added
