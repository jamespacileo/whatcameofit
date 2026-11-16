"""Development codes for a claim's intervention, from a registry of substances.
Behavior: openspec entity-resolution, "Development codes come from a substance registry".

A code is taken only when the registry lists the intervention's names under exactly one
substance and marks the code as a code of that substance. Nothing is matched loosely and
no model is asked. An intervention the registry does not list gets no code, and that is
said.

A brand the registry does not list is then asked of a second source, which files brands
under their ingredients (openspec entity-resolution, "A brand the substance registry
does not list is looked up under its ingredient"). The second source gives a name to
search for, never a code.
"""

from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Protocol

from sqlalchemy.orm import Session

from thenwhat.claims.entities import entities_of
from thenwhat.claims.entry import core_name, name_key
from thenwhat.db.models import Claim, Entity, EntitySubstance
from thenwhat.domain import EntityType
from thenwhat.sources.base import SourceRecord
from thenwhat.sources.gsrs import codes_of, label_of, name_of


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
    # The sources asked, in order. The last is the one whose answer this is; the ones
    # before it listed none of the names.
    sources: tuple[str, ...] = ()

    @property
    def source(self) -> str:
        """The source whose answer this is."""
        return self.sources[-1] if self.sources else ""


def one_substance(records: list[SourceRecord], *, forms: bool = True) -> SourceRecord | None:
    """The one substance these records are, or None when they are several.

    A registry files a drug and its forms apart: imatinib and imatinib mesylate,
    dostarlimab and dostarlimab-gxly. They are one treatment. When one record's name
    opens every other record's name, whole word for whole word, that record is the
    substance and the others are its forms. Semaglutide and tirzepatide share no such
    name and stay two.

    That holds for a registry of substances. A source of brands lists ingredients, and
    two ingredients are two molecules even when one's name opens the other's: with
    `forms` off, the records are one only when they are one, or all carry one name.
    """
    if len(records) == 1:
        return records[0]
    named = [(name_key(name_of(record)), record) for record in records]
    if not forms:
        same = bool(named[0][0]) and all(name == named[0][0] for name, _ in named)
        return records[0] if same else None
    for base, record in named:
        if base and all(
            other == base or other.startswith((f"{base} ", f"{base}-")) for other, _ in named
        ):
            return record
    return None


def codes_for(
    substances: Substances,
    names: list[str],
    *,
    brands: Substances | None = None,
    forms: bool = True,
) -> Codes:
    """The development codes the registry lists for the substance these names belong to.

    Each name is looked up as written. The names must lead to exactly one substance: a
    treatment whose names the registry files under two substances is not identified, and
    gets no code. A code equal to one of the names is left out, as it is searched for as
    a name already.

    `brands` is asked only when the registry lists none of the names. The names must
    be a brand it lists under exactly one ingredient: ingredients named differently are
    several, with no allowance for a name that opens another (`forms` off).
    """
    asked = names[0] if names else ""
    found: dict[str, SourceRecord] = {}
    for name in dict.fromkeys(names):
        for record in substances.substances_named(name):
            found.setdefault(record.external_id, record)
    labels = [label_of(record) for record in found.values()]
    sources = (substances.name,)
    if not found:
        if brands is None:
            return Codes(Listing.NOT_LISTED, asked, sources=sources)
        answer = codes_for(brands, names, forms=False)
        return replace(answer, sources=sources + answer.sources)
    record = one_substance(list(found.values()), forms=forms)
    if record is None:
        return Codes(Listing.SEVERAL_SUBSTANCES, asked, labels, sources=sources)
    labels = [label_of(record)]
    known = {name_key(name) for name in names}
    codes = [code for code in codes_of(record) if name_key(code) not in known]
    return Codes(Listing.ONE_SUBSTANCE, asked, labels, codes, record, sources)


def intervention_of(session: Session, claim: Claim) -> Entity | None:
    for entity in entities_of(session, claim):
        if entity.type is EntityType.INTERVENTION:
            return entity
    return None


def give_development_codes(
    session: Session, claim: Claim, *, substances: Substances, brands: Substances | None = None
) -> Codes | None:
    """Look the claim's intervention up in the registry of substances and keep the
    substance's record with its codes. None when the claim has no intervention.

    When the registry lists none of its names, `brands` is asked whether they are a
    brand of one ingredient, and that ingredient's record is kept instead, under its
    own source's name, with no code.

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
    answer = codes_for(substances, [*names, *cores], brands=brands)
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
