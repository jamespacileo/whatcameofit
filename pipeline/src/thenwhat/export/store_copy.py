"""A copy of what an export reads, taken from the pipeline's database into a SQLite file
of the truth store's schema, through the store's own merge. For the comparison only
(openspec truth-store, "The two exports are compared").

Until the store holds the records itself, this is how a store file is had to compare
against: the records are read (never written) from the session, put in the natural-key
form a writer hands over, staged, and merged by `store/merge.sql` as a D1 batch runs it.
It stands in for two things that are being built elsewhere and replaces neither: the
pipeline's mapping of each kind to its natural-key form (task 4.1), and the snapshot the
ingest service gives (design, "The read side"). When the snapshot exists the comparison
is given its file and this module is not used.

Only the kinds an export reads are copied: no leads, no registry corpus, no spend.

Nothing here is article text: titles and addresses as stored, and the pipeline's own
wording of statements.
"""

import hashlib
import json
import sqlite3
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.address import article_key
from thenwhat.db.models import (
    Claim,
    ClaimChange,
    ClaimTerm,
    DecisionLog,
    Entity,
    EntityArticle,
    EntityMatch,
    EvidenceEvent,
    FailureFlag,
    OrganisationRecord,
    OutletIcon,
    PaperRecord,
    Promise,
    Reading,
    ReportedStatement,
    SourceArticle,
    TermRecord,
    TrialRead,
)
from thenwhat.decide.steps import ENTITY_MATCH, EVIDENCE_STAGE, PAPER_MATCH
from thenwhat.decide.steps import match_ref as row_match_ref
from thenwhat.domain import Decider
from thenwhat.export.store_records import claim_ref, match_ref

# A payload this size or smaller is kept in the store's own `payload` table; a larger
# one is an object (design, decision 2).
INLINE_PAYLOAD_BYTES = 16384
# Records to a run, as the proof loads its sample: parents first, each run whole.
RUN_RECORDS = 20_000
# Records to a staged chunk.
CHUNK_RECORDS = 500

Record = tuple[str, str, dict[str, Any]]


class CopyFailed(Exception):
    """The store's merge refused a run of the copy."""


@dataclass
class CopyReport:
    """What a copy handed over and what the merge said of it."""

    runs: int = 0
    # Records handed over, by kind.
    handed: dict[str, int] = field(default_factory=dict)
    # Records the merge added, by kind. Fewer than handed means the store already held a
    # record under that natural key: two rows of the database are one record there.
    added: dict[str, int] = field(default_factory=dict)
    payload_objects: int = 0
    # What could not be said in the store's form, in words.
    notes: list[str] = field(default_factory=list)

    def folded(self) -> dict[str, int]:
        """Kinds of which the store kept fewer records than were handed over."""
        return {
            kind: self.handed[kind] - self.added.get(kind, 0)
            for kind in self.handed
            if kind not in ("action", "payload") and self.added.get(kind, 0) < self.handed[kind]
        }


def _statements(path: Path) -> list[str]:
    """A file's statements: split at a line holding only `;`, comment lines dropped."""
    found = []
    for chunk in path.read_text().split("\n;\n"):
        lines = [line for line in chunk.splitlines() if line.strip() and not line.startswith("--")]
        if lines:
            found.append("\n".join(lines))
    return found


def _named(path: Path) -> dict[str, str]:
    found: dict[str, str] = {}
    name: str | None = None
    lines: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith("-- name:"):
            name, lines = line.split(":", 1)[1].strip(), []
        elif line.strip() == ";" and name:
            found[name], name = "\n".join(lines), None
        elif name and not line.startswith("--"):
            lines.append(line)
    return found


def _text(value: datetime | date | None) -> str | None:
    return None if value is None else value.isoformat()


def _code(value: Any) -> Any:
    """An enum as its code; anything else as it is."""
    return getattr(value, "value", value)


def payload_text(payload: Any) -> bytes:
    """A payload as the bytes the store keeps and its checksum is of."""
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode()


def _event_rows(session: Session, claim_ids: list[int]) -> Iterator[Any]:
    for start in range(0, len(claim_ids), 200):
        yield from session.execute(
            select(*EvidenceEvent.__table__.c)
            .where(EvidenceEvent.claim_id.in_(claim_ids[start : start + 200]))
            .order_by(EvidenceEvent.id)
        )


def content_checksum(event: Any) -> str:
    """Of the fields a status is derived from (store-tables.md, the finding). A stand-in
    for the pipeline's own, which task 4.1 writes."""
    parts = (
        _code(event.type),
        event.event_date.isoformat(),
        _code(event.trial_state) or "",
        ",".join(event.trial_phases or []),
        _code(event.regulatory_outcome) or "",
        event.external_id,
    )
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


class _Copy:
    def __init__(self, session: Session, payloads: Path, report: CopyReport) -> None:
        self.session = session
        self.payloads = payloads
        self.report = report
        self.seen_payloads: set[str] = set()

    def keep_payload(self, payload: Any, records: list[Record]) -> str:
        """Add the payload's record once and return its checksum. A large one is written
        to the folder that stands in for the object store."""
        raw = payload_text(payload)
        sha = hashlib.sha256(raw).hexdigest()
        if sha in self.seen_payloads:
            return sha
        self.seen_payloads.add(sha)
        body: dict[str, Any] = {"sha256": sha, "bytes": len(raw)}
        if len(raw) <= INLINE_PAYLOAD_BYTES:
            body["body"] = raw.decode()
        else:
            body["r2_key"] = f"payload/{sha}"
            held = self.payloads / "payload" / sha
            held.parent.mkdir(parents=True, exist_ok=True)
            held.write_bytes(raw)
            self.report.payload_objects += 1
        records.append(("payload", sha, body))
        return sha


def _first_slugs(
    session: Session, claims: list[Claim]
) -> tuple[dict[int, str], list[list[Record]]]:
    """The slug each claim is first handed over under, and the renames that bring it to
    the slug it has now, one run a rename so that each sees the one before it.

    The database keeps the slug a claim had before each rename that changed it. The
    store learns a former slug only from a `rename` action, so a renamed claim is handed
    over under its first slug and renamed again, in the order it was.
    """
    ids = {claim.id for claim in claims}
    renames = [
        change
        for change in session.scalars(
            select(ClaimChange)
            .where(ClaimChange.kind == "rename", ClaimChange.former_slug.is_not(None))
            .order_by(ClaimChange.id)
        )
        if change.claim_id in ids
    ]
    now_slug = {claim.id: claim.slug for claim in claims}
    first: dict[int, str] = dict(now_slug)
    steps: list[list[Record]] = []
    by_claim: dict[int, list[ClaimChange]] = {}
    for change in renames:
        by_claim.setdefault(change.claim_id, []).append(change)
    for claim_id, changes in by_claim.items():
        assert changes[0].former_slug is not None
        first[claim_id] = changes[0].former_slug
        for place, change in enumerate(changes):
            after = (
                changes[place + 1].former_slug if place + 1 < len(changes) else now_slug[claim_id]
            )
            if after == change.former_slug:
                continue
            steps.append(
                [
                    (
                        "action",
                        f"rename|{change.former_slug}|{change.id}",
                        {
                            "action": "rename",
                            "slug": change.former_slug,
                            "new_slug": after,
                            "decided_by": _code(change.decided_by),
                            "at": _text(change.decided_at),
                        },
                    )
                ]
            )
    return first, steps


def records_of(
    session: Session, claims: list[Claim], payloads: Path, report: CopyReport
) -> list[list[Record]]:
    """The runs of a copy of these claims, in the order they are merged: the claims
    under their first slugs, their renames, then everything else with the actions that
    archive, merge and publish."""
    copy = _Copy(session, payloads, report)
    first_slug, rename_runs = _first_slugs(session, claims)
    slug = {claim.id: claim.slug for claim in claims}
    ids = sorted(slug)

    def of_claims(model: Any, column: Any = None) -> Iterable[Any]:
        column = model.claim_id if column is None else column
        for start in range(0, len(ids), 1000):
            yield from session.scalars(
                select(model).where(column.in_(ids[start : start + 1000])).order_by(model.id)
            )

    claim_records: list[Record] = []
    for claim in sorted(claims, key=lambda claim: claim.id):
        claim_records.append(
            (
                "claim",
                first_slug[claim.id],
                {
                    "slug": first_slug[claim.id],
                    "headline": claim.headline,
                    "summary": claim.summary,
                    "vertical": claim.vertical,
                    "approach": claim.approach,
                    "indication": claim.indication,
                    "first_reported_date": _text(claim.first_reported_date),
                    "evidence_stage": _code(claim.evidence_stage),
                    "current_status": _code(claim.current_status),
                    "overlay_years": claim.overlay_years,
                    "status_updated_at": _text(claim.status_updated_at),
                    # Not read by an export; the store asks for one.
                    "origin": "entry",
                    "review_state": _code(claim.review_state),
                    "reviewed_at": _text(claim.reviewed_at),
                    "reviewed_by": _code(claim.reviewed_by),
                    "awaiting_audit_at": _text(claim.awaiting_audit_at),
                    "created_at": _text(claim.created_at),
                },
            )
        )

    rest: list[Record] = []
    payloads_first: list[Record] = []

    # --- what was reported ----------------------------------------------------------
    url_key: dict[int, str] = {}
    held_keys: set[tuple[int, str]] = set()
    for article in of_claims(SourceArticle):
        key = article_key(article.url) or article.url
        if (article.claim_id, key) in held_keys:
            report.notes.append(
                f"{slug[article.claim_id]} holds two articles at one address key ({key});"
                " the store keeps the first."
            )
        held_keys.add((article.claim_id, key))
        url_key[article.id] = key
        rest.append(
            (
                "source_article",
                f"{slug[article.claim_id]}|{key}",
                {
                    "slug": slug[article.claim_id],
                    "url_key": key,
                    "url": article.url,
                    "outlet": article.outlet,
                    "title": article.title,
                    "published_date": _text(article.published_date),
                    "content_hash": article.content_hash,
                    "archive_url": article.archive_url,
                },
            )
        )
    for promise in of_claims(Promise):
        key = url_key[promise.source_article_id]
        digest = hashlib.md5(promise.description.encode(), usedforsecurity=False).hexdigest()
        rest.append(
            (
                "promise",
                f"{slug[promise.claim_id]}|{key}|{digest}",
                {
                    "slug": slug[promise.claim_id],
                    "url_key": key,
                    "description": promise.description,
                    "parsed_date": _text(promise.parsed_date),
                },
            )
        )
    for statement in of_claims(ReportedStatement):
        key = url_key[statement.source_article_id]
        natural = f"{slug[statement.claim_id]}|{key}|{statement.text_key}"
        rest.append(
            (
                "reported_statement",
                natural,
                {
                    "slug": slug[statement.claim_id],
                    "url_key": key,
                    "text": statement.text,
                    "text_key": statement.text_key,
                    "kind": _code(statement.kind),
                    "firmness": _code(statement.firmness),
                    "speaker": _code(statement.speaker),
                    "basis": _code(statement.basis),
                    "confidence": statement.confidence,
                    "decision_ref": f"statement:{natural}",
                    "article_read_at": _text(statement.article_read_at),
                    "review_state": _code(statement.review_state),
                    "reviewed_at": _text(statement.reviewed_at),
                    "reviewed_by": _code(statement.reviewed_by),
                    "created_at": _text(statement.created_at),
                },
            )
        )

    # --- entities, matches, terms ---------------------------------------------------
    entities: dict[int, Entity] = {}
    for entity in of_claims(Entity):
        entities[entity.id] = entity
        rest.append(
            (
                "entity",
                f"{slug[entity.claim_id]}|{_code(entity.type)}|{entity.name}",
                {
                    "slug": slug[entity.claim_id],
                    "type": _code(entity.type),
                    "name": entity.name,
                    "synonyms": list(entity.synonyms),
                    "search_phrases": list(entity.search_phrases),
                    "is_origin_paper": int(entity.is_origin_paper),
                    "doi": entity.doi,
                    "named_by": sorted(_code(by) for by in entity.named_by),
                },
            )
        )
    entity_ids = sorted(entities)

    def of_entities(model: Any) -> Iterable[Any]:
        for start in range(0, len(entity_ids), 1000):
            yield from session.scalars(
                select(model)
                .where(model.entity_id.in_(entity_ids[start : start + 1000]))
                .order_by(*model.__table__.primary_key.columns)
            )

    def entity_key(entity: Entity) -> dict[str, Any]:
        return {
            "slug": slug[entity.claim_id],
            "entity_type": _code(entity.type),
            "entity_name": entity.name,
        }

    for link in of_entities(EntityArticle):
        entity = entities[link.entity_id]
        if link.source_article_id not in url_key:
            continue
        key = url_key[link.source_article_id]
        rest.append(
            (
                "entity_article",
                f"{slug[entity.claim_id]}|{_code(entity.type)}|{entity.name}|{key}",
                {**entity_key(entity), "url_key": key},
            )
        )
    matches: dict[int, EntityMatch] = {}
    match_refs: dict[str, str] = {}
    for match in of_entities(EntityMatch):
        entity = entities[match.entity_id]
        matches[match.id] = match
        match_refs[row_match_ref(match.id)] = match_ref(
            slug[entity.claim_id],
            _code(entity.type),
            entity.name,
            match.source_name,
            match.external_id,
        )
        rest.append(
            (
                "entity_match",
                f"{slug[entity.claim_id]}|{_code(entity.type)}|{entity.name}"
                f"|{match.source_name}|{match.external_id}",
                {
                    **entity_key(entity),
                    "source_name": match.source_name,
                    "external_id": match.external_id,
                    "score": match.score,
                    "record_summary": match.record_summary,
                    "record_facts": match.record_facts,
                    "reasons": list(match.reasons),
                    "review_state": _code(match.review_state),
                    "reviewed_at": _text(match.reviewed_at),
                    "reviewed_by": _code(match.reviewed_by),
                    "created_at": _text(match.created_at),
                },
            )
        )
    for term in of_claims(ClaimTerm):
        rest.append(
            (
                "claim_term",
                f"{slug[term.claim_id]}|{_code(term.role)}|{term.source_name}|{term.external_id}",
                {
                    "slug": slug[term.claim_id],
                    "role": _code(term.role),
                    "source_name": term.source_name,
                    "external_id": term.external_id,
                    "label": term.label,
                    "score": term.score,
                    "fit": _code(term.fit),
                    "reasons": list(term.reasons),
                    "review_state": _code(term.review_state),
                    "reviewed_at": _text(term.reviewed_at),
                    "reviewed_by": _code(term.reviewed_by),
                    "created_at": _text(term.created_at),
                },
            )
        )

    # --- the records of sources: small tables, copied whole --------------------------
    for record in session.scalars(
        select(TermRecord).order_by(TermRecord.source_name, TermRecord.external_id)
    ):
        rest.append(
            (
                "source_record",
                f"term|{record.source_name}|{record.external_id}",
                {
                    "kind": "term",
                    "source_name": record.source_name,
                    "external_id": record.external_id,
                    "url": record.url,
                    "body": record.payload,
                    "fetched_at": _text(record.fetched_at),
                },
            )
        )
    for record in session.scalars(
        select(OrganisationRecord).order_by(
            OrganisationRecord.source_name, OrganisationRecord.external_id
        )
    ):
        rest.append(
            (
                "source_record",
                f"organisation|{record.source_name}|{record.external_id}",
                {
                    "kind": "organisation",
                    "source_name": record.source_name,
                    "external_id": record.external_id,
                    "url": record.url,
                    "body": record.payload,
                    "fetched_at": _text(record.fetched_at),
                },
            )
        )
    for paper in session.scalars(select(PaperRecord).order_by(PaperRecord.id)):
        rest.append(
            (
                "source_record",
                f"paper|{paper.source_name}|{paper.identifier}",
                {
                    "kind": "paper",
                    "source_name": paper.source_name,
                    "external_id": paper.identifier,
                    "pubmed_id": paper.pubmed_id,
                    "body": paper.payload,
                    "fetched_at": _text(paper.fetched_at),
                },
            )
        )

    # --- evidence -------------------------------------------------------------------
    dedupe_key: dict[int, str] = {}
    trial_ids: set[tuple[str, str]] = set()
    # Read as rows, not objects: a payload can be megabytes and none is kept in memory.
    for event in _event_rows(session, ids):
        dedupe_key[event.id] = event.dedupe_key
        trial_ids.add((event.source_name, event.external_id))
        body: dict[str, Any] = {
            "slug": slug[event.claim_id],
            "dedupe_key": event.dedupe_key,
            "type": _code(event.type),
            "event_date": _text(event.event_date),
            "date_basis": event.date_basis,
            "source_name": event.source_name,
            "source_url": event.source_url,
            "external_id": event.external_id,
            "trial_phases": None if event.trial_phases is None else list(event.trial_phases),
            "trial_state": _code(event.trial_state),
            "regulatory_outcome": _code(event.regulatory_outcome),
            "summary": event.summary,
            "confidence": event.confidence,
            "content_sha256": content_checksum(event),
            "payload_sha256": copy.keep_payload(event.raw_payload, payloads_first),
            "fetched_at": _text(event.fetched_at),
            "review_state": _code(event.review_state),
            "reviewed_at": _text(event.reviewed_at),
            "reviewed_by": _code(event.reviewed_by),
            "created_at": _text(event.created_at),
        }
        matched = matches.get(event.entity_match_id) if event.entity_match_id else None
        if matched is not None:
            entity = entities[matched.entity_id]
            body |= {
                "match_entity_type": _code(entity.type),
                "match_entity_name": entity.name,
                "match_source_name": matched.source_name,
                "match_external_id": matched.external_id,
            }
        rest.append(("evidence_event", f"{slug[event.claim_id]}|{event.dedupe_key}", body))
    for flag in of_claims(FailureFlag):
        rest.append(
            (
                "failure_flag",
                f"{slug[flag.claim_id]}|{flag.trial_external_id}",
                {
                    "slug": slug[flag.claim_id],
                    "trial_external_id": flag.trial_external_id,
                    "dedupe_key": dedupe_key[flag.evidence_event_id],
                    "source_url": flag.source_url,
                    "created_at": _text(flag.created_at),
                },
            )
        )
    for read in session.scalars(select(TrialRead).order_by(TrialRead.id)):
        if (read.source_name, read.trial_id) not in trial_ids:
            continue
        readings = session.scalars(
            select(Reading)
            .where(Reading.trial_read_id == read.id)
            .order_by(Reading.outcome, Reading.kind, Reading.id)
        )
        rest.append(
            (
                "trial_read",
                f"{read.source_name}|{read.trial_id}",
                {
                    "source_name": read.source_name,
                    "trial_id": read.trial_id,
                    "input_hash": read.input_hash,
                    "instructions_version": read.instructions_version,
                    "provider": read.provider,
                    "model": read.model,
                    "refusals": list(read.refusals),
                    "read_at": _text(read.read_at),
                    "readings": [
                        {
                            "outcome": reading.outcome,
                            "kind": _code(reading.kind),
                            "field": _code(reading.field),
                            "words": reading.words,
                            "number": reading.number,
                            "unit": _code(reading.unit),
                            "code": _code(reading.code),
                            "confidence": reading.confidence,
                            "decided_by": _code(reading.decided_by),
                        }
                        for reading in readings
                    ],
                },
            )
        )

    # --- the decisions an export reads: a match's scoring, a claim's stage reading ---
    refs = {f"claim:{claim_id}": claim_ref(slug[claim_id]) for claim_id in ids} | match_refs
    for decision in session.scalars(
        select(DecisionLog)
        .where(DecisionLog.step.in_([ENTITY_MATCH, PAPER_MATCH, EVIDENCE_STAGE]))
        .order_by(DecisionLog.id)
    ):
        if decision.input_ref not in refs:
            continue
        rest.append(
            (
                "decision",
                str(decision.id),
                {
                    "seq": decision.id,
                    "step": decision.step,
                    "input_ref": refs[decision.input_ref],
                    "backend": decision.backend,
                    "model": decision.model,
                    "options": decision.options,
                    "output": decision.output,
                    "confidence": decision.confidence,
                    "error": decision.error,
                    "human_label": decision.human_label,
                    "created_at": _text(decision.created_at),
                },
            )
        )

    for icon in session.scalars(select(OutletIcon).order_by(OutletIcon.domain)):
        held = icon.content is not None and icon.media_type is not None
        rest.append(
            (
                "outlet_icon",
                icon.domain,
                {
                    "domain": icon.domain,
                    "icon_url": (icon.icon_url or "") if held else None,
                    "media_type": icon.media_type if held else None,
                    "content_hex": icon.content.hex() if held and icon.content else None,
                    "fetched_at": _text(icon.fetched_at),
                },
            )
        )

    # --- actions: a published time, an archive and a merge are not a claim's fields ---
    by_id = {claim.id: claim for claim in claims}
    merges = {
        change.claim_id: change
        for change in session.scalars(
            select(ClaimChange)
            .where(ClaimChange.kind == "merge", ClaimChange.undone_at.is_(None))
            .order_by(ClaimChange.id)
        )
    }
    for claim in sorted(claims, key=lambda claim: claim.id):
        if claim.published_at is not None:
            rest.append(
                (
                    "action",
                    f"publish|{claim.slug}",
                    {"action": "publish", "slug": claim.slug, "at": _text(claim.published_at)},
                )
            )
        if claim.archived_at is not None:
            rest.append(
                (
                    "action",
                    f"archive|{claim.slug}",
                    {
                        "action": "archive",
                        "slug": claim.slug,
                        "reason": claim.archive_reason or "not recorded",
                        "decided_by": "human",
                        "at": _text(claim.archived_at),
                    },
                )
            )
        if claim.merged_into_id is not None:
            kept = by_id.get(claim.merged_into_id)
            if kept is None:
                report.notes.append(
                    f"{claim.slug} was merged into a claim that is not in the copy."
                )
                continue
            change = merges.get(claim.id)
            decided_by = change.decided_by if change else Decider.HUMAN
            rest.append(
                (
                    "action",
                    f"merge|{claim.slug}",
                    {
                        "action": "merge",
                        "slug": claim.slug,
                        "into_slug": kept.slug,
                        "decided_by": _code(decided_by),
                        "at": _text(change.decided_at if change else claim.archived_at),
                    },
                )
            )

    everything = [*payloads_first, *rest]
    data_runs = [
        everything[start : start + RUN_RECORDS] for start in range(0, len(everything), RUN_RECORDS)
    ]
    return [claim_records, *rename_runs, *data_runs]


def copy_to_store(
    session: Session,
    path: Path,
    *,
    store_sql: Path,
    payloads: Path,
    now: datetime,
    claims: list[Claim] | None = None,
) -> CopyReport:
    """Make `path` a store file holding what an export of `claims` reads, every claim
    when none are named. `store_sql` is the folder of the store's schema and merge.

    A claim that one of these was merged into is copied with it. The session is only
    read. Any file already at `path` is replaced.
    """
    if claims is None:
        claims = list(session.scalars(select(Claim).order_by(Claim.id)))
    else:
        held = {claim.id: claim for claim in claims}
        for claim in list(held.values()):
            kept_id = claim.merged_into_id
            while kept_id is not None and kept_id not in held:
                kept = session.get(Claim, kept_id)
                assert kept is not None
                held[kept.id] = kept
                kept_id = kept.merged_into_id
        claims = list(held.values())
    report = CopyReport()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.unlink(missing_ok=True)
    merge = _statements(store_sql / "merge.sql")
    ingest = _named(store_sql / "ingest.sql")
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.execute("PRAGMA foreign_keys = ON")  # D1 enforces foreign keys
        db.executescript((store_sql / "schema.sql").read_text())
        for number, records in enumerate(records_of(session, claims, payloads, report)):
            if not records:
                continue
            run = f"copy-{number}"
            counts: dict[str, int] = {}
            for kind, _, _ in records:
                counts[kind] = counts.get(kind, 0) + 1
                report.handed[kind] = report.handed.get(kind, 0) + 1
            db.execute(
                ingest["register_run"],
                (run, "migration", "copy", None, "copy", now.isoformat(), None, None),
            )
            db.execute(ingest["state_steps"], (run, "{}"))
            db.execute(ingest["state_counts"], (run, json.dumps(counts)))
            for start in range(0, len(records), CHUNK_RECORDS):
                chunk = [
                    {"kind": kind, "key": key, "body": body}
                    for kind, key, body in records[start : start + CHUNK_RECORDS]
                ]
                db.execute(ingest["stage"], (run, json.dumps(chunk)))
            # As a D1 batch: every statement or none, nothing read in between.
            db.execute("BEGIN")
            try:
                for statement in merge:
                    db.execute(statement, (run,) if "?1" in statement else ())
                db.execute("COMMIT")
            except sqlite3.Error as error:
                db.execute("ROLLBACK")
                raise CopyFailed(f"The store's merge undid run {run}: {error}") from error
            for kind, added in db.execute(
                "SELECT kind, added FROM merge_report WHERE run_id = ?", (run,)
            ):
                report.added[kind] = report.added.get(kind, 0) + added
            db.execute("DELETE FROM stg WHERE run_id = ?", (run,))
            report.runs += 1
    finally:
        db.close()
    return report
