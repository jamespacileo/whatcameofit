"""Store records into Postgres rows: each record's row is found by its natural key, or
created, and given the record's values. The way back from the store, and what the
round-trip tests rely on.
"""

from collections.abc import Iterable, Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key
from thenwhat.db.models import (
    Base,
    Claim,
    ClaimChange,
    Entity,
    EntityMatch,
    EvidenceEvent,
    LinkLead,
    RegistryTrial,
    SourceArticle,
    TrialRead,
)
from thenwhat.store.form import KEY_JOIN, Record, key_of, key_parts, payload_value
from thenwhat.store.rows import (
    SIMPLE,
    ArticleRef,
    ClaimRef,
    DecisionRef,
    EntityRef,
    EventRef,
    LeadRef,
    MatchRef,
    ReadRef,
    Row,
    TrialRef,
    action_rows,
    entity_substance_row,
    evidence_event_row,
    registry_trial_row,
    source_record_rows,
    trial_read_rows,
)


class NotFound(LookupError):
    """A record names a parent Postgres does not hold."""


class Occupied(RuntimeError):
    """Postgres already holds rows in a table the records would be placed in."""


def _claim_id(session: Session, slug: str) -> int | None:
    found = session.scalar(select(Claim.id).where(Claim.slug == slug))
    if found is None:
        # A slug a rename replaced still names its claim.
        found = session.scalar(select(ClaimChange.claim_id).where(ClaimChange.former_slug == slug))
    return found


def _by_url_key(rows: Iterable[Any], url_key: str) -> Any | None:
    return next((row for row in rows if article_key(row.url) == url_key), None)


def _article_id(session: Session, ref: ArticleRef) -> int | None:
    claim_id = _claim_id(session, ref.slug)
    articles = session.scalars(select(SourceArticle).where(SourceArticle.claim_id == claim_id))
    found = _by_url_key(articles.all(), ref.url_key)
    return None if found is None else found.id


def _entity_id(session: Session, ref: EntityRef) -> int | None:
    return session.scalar(
        select(Entity.id).where(
            Entity.claim_id == _claim_id(session, ref.slug),
            Entity.type == ref.type,
            Entity.name == ref.name,
        )
    )


def _decision_ref(session: Session, text: str) -> str:
    """`records.natural_ref` read the other way: the natural key back to the row id."""
    kind, _, rest = text.partition(":")

    def found(row_id: int | None) -> str:
        if row_id is None:
            raise NotFound(f"The reference {text!r} names a row Postgres does not hold.")
        return str(row_id)

    if kind == "claim":
        slug, colon, tail = rest.partition(":")
        if slug.isdigit():
            return text
        return f"claim:{found(_claim_id(session, slug))}{colon}{tail}"
    if kind == "source_article" and ":statement:" in rest:
        article, _, place = rest.rpartition(":statement:")
        slug, url_key = key_parts(article)
        row_id = found(_article_id(session, ArticleRef(slug, url_key)))
        return f"source_article:{row_id}:statement:{place}"
    if kind == "entity_match" and KEY_JOIN in rest:
        slug, entity_type, name, source, external = key_parts(rest)
        ref = MatchRef(EntityRef(slug, entity_type, name), source, external)
        return f"entity_match:{found(resolve(session, ref))}"
    if kind == "link_lead" and not rest.isdigit():
        return f"link_lead:{found(resolve(session, LeadRef(rest)))}"
    return text


def resolve(session: Session, ref: Any) -> Any:
    """A natural reference's row id; any other value as it is."""
    if isinstance(ref, ClaimRef):
        row_id = _claim_id(session, ref.slug)
    elif isinstance(ref, ArticleRef):
        row_id = _article_id(session, ref)
        if row_id is None and not ref.required:
            return None
    elif isinstance(ref, EntityRef):
        row_id = _entity_id(session, ref)
    elif isinstance(ref, MatchRef):
        row_id = session.scalar(
            select(EntityMatch.id).where(
                EntityMatch.entity_id == _entity_id(session, ref.entity),
                EntityMatch.source_name == ref.source_name,
                EntityMatch.external_id == ref.external_id,
            )
        )
    elif isinstance(ref, EventRef):
        row_id = session.scalar(
            select(EvidenceEvent.id).where(
                EvidenceEvent.claim_id == _claim_id(session, ref.slug),
                EvidenceEvent.dedupe_key == ref.dedupe_key,
            )
        )
    elif isinstance(ref, LeadRef):
        row_id = session.scalar(select(LinkLead.id).where(LinkLead.url_key == ref.url_key))
    elif isinstance(ref, TrialRef):
        row_id = session.scalar(
            select(RegistryTrial.id).where(
                RegistryTrial.registry_name == ref.registry_name,
                RegistryTrial.external_id == ref.external_id,
            )
        )
    elif isinstance(ref, ReadRef):
        row_id = session.scalar(
            select(TrialRead.id).where(
                TrialRead.source_name == ref.source_name, TrialRead.trial_id == ref.trial_id
            )
        )
    elif isinstance(ref, DecisionRef):
        return _decision_ref(session, ref.text)
    else:
        return ref
    if row_id is None:
        raise NotFound(f"{ref} names a row Postgres does not hold.")
    return row_id


def place_row(session: Session, row: Row) -> Base:
    """Find the row by its key, or create it, and give it the record's values. A value
    `("keep", v)` is set only where the row has none."""
    key = {column: resolve(session, value) for column, value in row.key.items()}
    keep = {
        column: value[1]
        for column, value in row.values.items()
        if isinstance(value, tuple) and len(value) == 2 and value[0] == "keep"
    }
    values = {
        column: resolve(session, value)
        for column, value in row.values.items()
        if column not in keep
    }
    # An article and an article lead have no address key column: theirs is worked out.
    url_key = None if hasattr(row.model, "url_key") else key.pop("url_key", None)
    if url_key is not None:
        candidates = session.scalars(select(row.model).filter_by(**key)).all()
        found = _by_url_key(candidates, url_key)
    else:
        found = session.scalars(select(row.model).filter_by(**key)).one_or_none()
    if found is None:
        if not row.create:
            raise NotFound(f"No {row.model.__tablename__} row for {row.key}.")
        found = row.model(**key, **values, **keep)
        session.add(found)
    else:
        for column, value in values.items():
            if column == "registry_candidate_trial_ids" and isinstance(found, Claim):
                value = sorted(set(found.registry_candidate_trial_ids).union(value))
            setattr(found, column, value)
        for column, value in keep.items():
            if getattr(found, column) is None:
                setattr(found, column, value)
    session.flush()
    return found


def rows_of(
    record: Record,
    records: Mapping[tuple[str, str], Record],
    r2_objects: Mapping[str, str] | None = None,
) -> list[Row]:
    """What finds or creates a record's rows. `records` holds the run's other records by
    kind and key, for the payload an event or a trial names and the substance an
    intervention's substance names; `r2_objects` the text of each payload kept in R2,
    by checksum."""

    def payload(sha256: str) -> Any:
        return payload_value(records[("payload", sha256)], (r2_objects or {}).get(sha256))

    kind, b = record.kind, record.body
    if kind in SIMPLE:
        return [SIMPLE[kind](record)]
    if kind == "action":
        return action_rows(record)
    if kind == "source_record":
        return source_record_rows(record)
    if kind == "trial_read":
        return trial_read_rows(record)
    if kind == "evidence_event":
        return [evidence_event_row(record, payload=payload(b["payload_sha256"]))]
    if kind == "registry_trial":
        return [registry_trial_row(record, payload=payload(b["payload_sha256"]))]
    if kind == "entity_substance":
        substance = records[
            ("source_record", key_of("substance", b["source_name"], b["external_id"]))
        ]
        value = payload(substance.body["payload_sha256"])
        return [entity_substance_row(record, substance=substance, payload=value)]
    if kind == "payload":
        return []
    raise ValueError(f"Postgres has no table for the store's kind {kind!r}.")


# Parents first: a record is placed after every record its key names.
ORDER = (
    "payload",
    "claim",
    "source_article",
    "promise",
    "reported_statement",
    "entity",
    "entity_article",
    "entity_match",
    "claim_term",
    "source_record",
    "entity_substance",
    "evidence_event",
    "failure_flag",
    "trial_read",
    "registry_trial",
    "registry_load",
    "article_lead",
    "link_lead",
    "link_share",
    "link_lead_link",
    "link_lead_label",
    "decision",
    "usage",
    "measure_daily",
    "measure_claim",
    "work_entry",
    "outlet_icon",
    "action",
)
ACTION_ORDER = ("publish", "archive", "merge", "rename")


def place(
    session: Session, records: Iterable[Record], r2_objects: Mapping[str, str] | None = None
) -> None:
    """Every record into Postgres, parents first, as the store's merge takes a run:
    publication, then archive, then merge, then rename.

    Only into empty tables: a record's values replace a row's, which on a row already
    held would clear a hold or put a rule's review over a person's. The store's merge has
    the rules for a row already held; this does not, so it refuses (`Occupied`) before
    writing anything."""
    given = list(records)
    by_key = {(record.kind, record.key): record for record in given}

    def order(record: Record) -> tuple[int, int]:
        action = record.body.get("action") if record.kind == "action" else None
        return ORDER.index(record.kind), ACTION_ORDER.index(action) if action else 0

    rows = [
        row for record in sorted(given, key=order) for row in rows_of(record, by_key, r2_objects)
    ]
    models = {row.model for row in rows}
    held = sorted(
        model.__tablename__
        for model in models
        if session.scalar(select(model).limit(1)) is not None
    )
    if held:
        raise Occupied(
            f"Postgres already holds rows in {', '.join(held)}; place only fills empty tables."
        )
    for row in rows:
        place_row(session, row)
