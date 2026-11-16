"""A claim's entities: adding them, their synonyms, and the origin paper.
Behavior: openspec entity-resolution."""

import re
from collections.abc import Sequence

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
from thenwhat.db.models import (
    Claim,
    Entity,
    EntityArticle,
    EntityMatch,
    EntitySubstance,
    SourceArticle,
)
from thenwhat.domain import EntityType, NamedBy
from thenwhat.extract.names import is_a_search_phrase


class EntityNotFound(EntryError):
    pass


class DuplicateEntity(EntryError):
    pass


def entities_of(session: Session, claim: Claim) -> list[Entity]:
    return list(
        session.scalars(select(Entity).where(Entity.claim_id == claim.id).order_by(Entity.id))
    )


def intervention_components(names: Sequence[str]) -> set[str]:
    """Components explicitly listed in a regimen name, including a brand's alias."""
    components: set[str] = set()
    for name in names:
        name = re.sub(r"^combination of\s+|\s+combination$", "", name.strip(), flags=re.I)
        parts = re.split(
            r"\s+(?:and|plus|with(?:\s+or\s+without)?)\s+|\s*[+/]\s*", name, flags=re.I
        )
        if len(parts) > 1:
            components.update(
                name_key(component.strip(" ;"))
                for part in parts
                for component in part.split(",")
                if component.strip(" ;")
            )
    return components


def whole_intervention_names(names: Sequence[str]) -> list[str]:
    """Whole names, excluding aliases that merely repeat one explicit component."""
    components = intervention_components(names)
    return [name for name in names if name.strip() and name_key(name) not in components]


def substance_name(session: Session, entity: Entity) -> str | None:
    """What the registry of substances calls the intervention's one substance, such as
    "Semaglutide" for Wegovy or "Aducanumab" for Aduhelm, or the one ingredient a
    source of brands lists a brand under when the registry does not list the brand. None
    when neither lists it under one substance, or neither was asked."""
    kept = session.get(EntitySubstance, entity.id)
    if kept is None:
        return None
    name = (kept.payload.get("substance") or {}).get("_name")
    return " ".join(name.split()) if isinstance(name, str) and name.strip() else None


def development_codes(session: Session, entity: Entity) -> list[str]:
    """The codes a registry of substances lists for the intervention's substance. Empty
    when the registry does not list it under one substance, or was never asked."""
    kept = session.get(EntitySubstance, entity.id)
    return list(kept.codes) if kept is not None else []


def people(session: Session) -> list[tuple[Entity, Claim]]:
    """Every stored person entity with its claim, in claim order, for the operator to
    look through. Only researchers belong; anyone else is deleted with `delete_people`."""
    rows = session.execute(
        select(Entity, Claim)
        .join(Claim, Claim.id == Entity.claim_id)
        .where(Entity.type == EntityType.PERSON)
        .order_by(Claim.slug, Entity.id)
    )
    return [(entity, claim) for entity, claim in rows]


def delete_people(session: Session, entity_ids: list[int]) -> list[Entity]:
    """Delete the person entities the operator marked. Nothing is deleted unless every
    id is a person: an intervention, paper or organisation is never removed this way."""
    marked: list[Entity] = []
    for entity_id in dict.fromkeys(entity_ids):
        entity = session.get(Entity, entity_id)
        if entity is None or entity.type is not EntityType.PERSON:
            raise EntityNotFound(f"There is no person entity with id {entity_id}.")
        marked.append(entity)
    for entity in marked:
        # A person is never looked up, so one has no match; any left by hand goes too.
        for match in session.scalars(select(EntityMatch).where(EntityMatch.entity_id == entity.id)):
            session.delete(match)
        session.flush()
        session.delete(entity)
    session.flush()
    return marked


ORGANISATION_TYPES = (EntityType.INSTITUTION, EntityType.COMPANY)


def _organisation_named(session: Session, claim: Claim, name: str) -> Entity | None:
    """The claim's institution or company known by this name or synonym."""
    wanted = name_key(name)
    for entity in entities_of(session, claim):
        known = {name_key(entity.name), *(name_key(synonym) for synonym in entity.synonyms)}
        if entity.type in ORGANISATION_TYPES and wanted in known:
            return entity
    return None


def _mark(entity: Entity, named_by: NamedBy) -> bool:
    if named_by in entity.named_by:
        return False
    entity.named_by = [*entity.named_by, named_by.value]
    return True


def note_named_organisation(
    session: Session, claim: Claim, article: SourceArticle, name: str, type: EntityType
) -> Entity:
    """Record that a source article named an institution or company: as a new entity, or
    on the one the claim already has under that name, which gains the article's mark."""
    entity = _organisation_named(session, claim, name)
    if entity is None:
        entity = Entity(claim_id=claim.id, type=type, name=tidy(name))
        session.add(entity)
    else:
        _mark(entity, NamedBy.ARTICLE)
    session.flush()
    if session.get(EntityArticle, (entity.id, article.id)) is None:
        session.add(EntityArticle(entity_id=entity.id, source_article_id=article.id))
        session.flush()
    return entity


def note_sponsor(session: Session, claim: Claim, name: str, *, industry: bool) -> Entity | None:
    """Record a trial's lead sponsor as an organisation of the claim, named by a registry
    record: a company when the registry classes it as industry, else an institution.
    Openspec entity-resolution, "A trial's organisation sponsor becomes an entity".

    An institution or company the claim already has under that name gains the mark and
    is not recorded twice. Returns the entity this call created or marked, or None when
    nothing changed. The caller passes only a sponsor that is not a person.
    """
    name = tidy(name)
    if not name:
        return None
    entity = _organisation_named(session, claim, name)
    if entity is not None:
        if not _mark(entity, NamedBy.REGISTRY):
            return None
        session.flush()
        return entity
    entity = Entity(
        claim_id=claim.id,
        type=EntityType.COMPANY if industry else EntityType.INSTITUTION,
        name=name,
        named_by=[NamedBy.REGISTRY.value],
    )
    session.add(entity)
    session.flush()
    return entity


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
