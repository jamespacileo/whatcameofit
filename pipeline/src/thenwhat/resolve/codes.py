"""Development codes for a claim's intervention, from a registry of substances.
Behavior: openspec entity-resolution, "Development codes come from a substance registry".

A code is taken only when the registry lists the intervention's names under exactly one
substance and marks the code as a code of that substance. Nothing is matched loosely and
no model is asked. An intervention the registry does not list gets no code, and that is
said.
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Protocol

from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import core_name, name_key
from thenwhat.db.models import Claim, Entity, EntitySubstance
from thenwhat.domain import EntityType
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.gsrs import codes_of, label_of


class Substances(Protocol):
    name: str

    def substances_named(self, name: str) -> list[SourceRecord]: ...


class Listing(StrEnum):
    # The registry lists the names under one substance.
    ONE_SUBSTANCE = "one_substance"
    # The registry lists none of the names.
    NOT_LISTED = "not_listed"
    # The names are listed under more than one substance, so none is taken.
    SEVERAL_SUBSTANCES = "several_substances"


@dataclass(frozen=True, slots=True)
class Codes:
    """What the registry of substances says of one treatment's names."""

    listing: Listing
    # The first of the names asked about: the treatment's own name.
    asked: str
    # What the registry calls each substance found.
    substances: list[str] = field(default_factory=list)
    # The codes it lists for the one substance, less the names already known.
    codes: list[str] = field(default_factory=list)
    record: SourceRecord | None = None


def codes_for(substances: Substances, names: list[str]) -> Codes:
    """The development codes the registry lists for the substance these names belong to.

    Each name is looked up as written. The names must lead to exactly one substance: a
    treatment whose names the registry files under two substances is not identified, and
    gets no code. A code equal to one of the names is left out, as it is searched for as
    a name already.
    """
    asked = names[0] if names else ""
    found: dict[str, SourceRecord] = {}
    for name in dict.fromkeys(names):
        for record in substances.substances_named(name):
            found.setdefault(record.external_id, record)
    labels = [label_of(record) for record in found.values()]
    if not found:
        return Codes(Listing.NOT_LISTED, asked)
    if len(found) > 1:
        return Codes(Listing.SEVERAL_SUBSTANCES, asked, labels)
    record = next(iter(found.values()))
    known = {name_key(name) for name in names}
    codes = [code for code in codes_of(record) if name_key(code) not in known]
    return Codes(Listing.ONE_SUBSTANCE, asked, labels, codes, record)


def intervention_of(session: Session, claim: Claim) -> Entity | None:
    for entity in entities_of(session, claim):
        if entity.type is EntityType.INTERVENTION:
            return entity
    return None


def give_development_codes(
    session: Session, claim: Claim, *, substances: Substances
) -> Codes | None:
    """Look the claim's intervention up in the registry of substances and keep the
    substance's record with its codes. None when the claim has no intervention.

    Run again, it replaces what was kept. An intervention the registry no longer lists
    under one substance loses its record and its codes: nothing stale is searched for.
    """
    intervention = intervention_of(session, claim)
    if intervention is None:
        return None
    names = [intervention.name, *intervention.synonyms]
    # A dose or schedule in a name stops the registry from finding the substance:
    # "semaglutide 2.4 mg" is looked up as "semaglutide" too (batch 5's audit).
    cores = [core for name in names if (core := core_name(name)) and core != name_key(name)]
    answer = codes_for(substances, [*names, *cores])
    kept = session.get(EntitySubstance, intervention.id)
    if answer.record is None:
        if kept is not None:
            session.delete(kept)
            session.flush()
        return answer
    if kept is None:
        kept = EntitySubstance(entity_id=intervention.id)
        session.add(kept)
    kept.source_name = answer.record.source_name
    kept.external_id = answer.record.external_id
    kept.url = answer.record.url
    kept.payload = answer.record.payload
    kept.fetched_at = answer.record.fetched_at
    kept.codes = answer.codes
    session.flush()
    return answer
