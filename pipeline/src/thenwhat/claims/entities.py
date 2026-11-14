"""A claim's entities: adding them, their synonyms, and the origin paper.
Behavior: openspec entity-resolution."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import (
    DuplicateClaim,
    EntryError,
    InvalidField,
    MissingField,
    claim_by_slug,
    name_key,
    slug_of_claim_covering,
    tidy,
)
from thenwhat.db.models import Claim, Entity
from thenwhat.domain import EntityType
from thenwhat.extract.names import is_a_search_phrase


class EntityNotFound(EntryError):
    pass


class DuplicateEntity(EntryError):
    pass


def entities_of(session: Session, claim: Claim) -> list[Entity]:
    return list(
        session.scalars(select(Entity).where(Entity.claim_id == claim.id).order_by(Entity.id))
    )


def _find(session: Session, claim: Claim, name: str, type: EntityType | None = None) -> Entity:
    """The claim's entity known by this name or synonym."""
    wanted = name_key(name)
    for entity in entities_of(session, claim):
        known = {name_key(entity.name), *(name_key(synonym) for synonym in entity.synonyms)}
        if wanted in known and (type is None or entity.type is type):
            return entity
    kind = type.value if type else "entity"
    raise EntityNotFound(f"Claim '{claim.slug}' has no {kind} named '{name}'.")


def add_entity(
    session: Session, claim_slug: str, *, type: EntityType, name: str, doi: str | None = None
) -> Entity:
    claim = claim_by_slug(session, claim_slug)
    name = tidy(name)
    if not name:
        raise MissingField("name is required.")
    if type is EntityType.INTERVENTION:
        raise InvalidField(
            "A claim has one intervention. Add its other names with `entity synonym`."
        )
    if doi and type is not EntityType.PAPER:
        raise InvalidField("Only a paper can have a DOI.")
    if any(
        e.type is type and name_key(e.name) == name_key(name) for e in entities_of(session, claim)
    ):
        raise DuplicateEntity(f"Claim '{claim.slug}' already has the {type.value} '{name}'.")
    entity = Entity(claim_id=claim.id, type=type, name=name, doi=(doi or "").strip() or None)
    session.add(entity)
    session.flush()
    return entity


def add_synonym(session: Session, claim_slug: str, entity_name: str, synonym: str) -> Entity:
    """Record another name for an entity. Registry searches use every name."""
    claim = claim_by_slug(session, claim_slug)
    entity = _find(session, claim, entity_name)
    synonym = tidy(synonym)
    if not synonym:
        raise MissingField("synonym is required.")
    known = {name_key(entity.name), *(name_key(existing) for existing in entity.synonyms)}
    if name_key(synonym) in known:
        return entity
    if entity.type is EntityType.INTERVENTION:
        other = slug_of_claim_covering(session, synonym, claim.indication)
        if other is not None and other != claim.slug:
            raise DuplicateClaim(other)
    entity.synonyms = [*entity.synonyms, synonym]
    session.flush()
    return entity


def add_search_phrase(session: Session, claim_slug: str, entity_name: str, phrase: str) -> Entity:
    """Record words a registry would use for an intervention that has no product name.
    They are searched for within the claim's indication and never shown as a name."""
    claim = claim_by_slug(session, claim_slug)
    entity = _find(session, claim, entity_name)
    if entity.type is not EntityType.INTERVENTION:
        raise InvalidField("Only an intervention has search phrases.")
    phrase = tidy(phrase)
    if not phrase:
        raise MissingField("phrase is required.")
    if not is_a_search_phrase(phrase):
        raise InvalidField(
            f"'{phrase}' says what kind of thing it is, not which. Give the words a"
            " registry would file it under."
        )
    known = {
        name_key(entity.name),
        *(name_key(existing) for existing in [*entity.synonyms, *entity.search_phrases]),
    }
    if name_key(phrase) not in known:
        entity.search_phrases = [*entity.search_phrases, phrase]
        session.flush()
    return entity


def set_origin_paper(session: Session, claim_slug: str, paper_name: str) -> Entity:
    """Mark one of the claim's papers as the origin paper, replacing any earlier one."""
    claim = claim_by_slug(session, claim_slug)
    paper = _find(session, claim, paper_name, EntityType.PAPER)
    for entity in entities_of(session, claim):
        if entity.is_origin_paper and entity is not paper:
            entity.is_origin_paper = False
    session.flush()  # the old one must be cleared before the new one is set
    paper.is_origin_paper = True
    session.flush()
    return paper
