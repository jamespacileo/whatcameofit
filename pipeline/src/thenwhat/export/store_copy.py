"""A copy of what an export reads, taken from the pipeline's database into a SQLite file
of the truth store's schema, through the store's own merge. For the comparison only
(openspec truth-store, "The two exports are compared").

Until the store holds the records itself, this is how a store file is had to compare
against: the records are read (never written) from the session, put in the natural-key
form a writer hands over, staged, and merged by `store/merge.sql` as a D1 batch runs it.
Each record is put in that form by the pipeline's own mapping (`thenwhat.store`), so the
file holds what the pipeline's writer would have put in the store. The copy stands in
for the snapshot the ingest service gives (design, "The read side"): when that exists
the comparison is given its file and this module is not used.

Only the kinds an export reads are copied: no leads, no registry corpus, no spend.

Nothing here is article text: titles and addresses as stored, and the pipeline's own
wording of statements.
"""

import json
import sqlite3
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, cast

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
    LinkLead,
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
from thenwhat.store import records as r
from thenwhat.store.form import Record, body, key_of, payload_of, payload_record, when

# Records to a run, as the proof loads its sample: parents first, each run whole.
RUN_RECORDS = 20_000
# Records to a staged chunk.
CHUNK_RECORDS = 500


class CopyFailed(Exception):
    """The store's merge refused a run of the copy."""


@dataclass
class CopyReport:
    """What a copy handed over and what the merge said of it."""

    runs: int = 0
    # Records handed over, by kind.
    handed: dict[str, int] = field(default_factory=dict)
    # Records the merge added, by kind.
    added: dict[str, int] = field(default_factory=dict)
    payload_objects: int = 0
    # What could not be said in the store's form, in words.
    notes: list[str] = field(default_factory=list)

    # Records that were not handed over because another row of the database has the same
    # natural key: two rows there are one record in the store. By kind.
    folded: dict[str, int] = field(default_factory=dict)


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


def _event_rows(session: Session, claim_ids: list[int]) -> Iterator[EvidenceEvent]:
    """The claims' events as rows, not objects: a payload can be megabytes and none is
    kept in memory. A row has an event's fields under the same names."""
    for start in range(0, len(claim_ids), 200):
        for row in session.execute(
            select(*EvidenceEvent.__table__.c)
            .where(EvidenceEvent.claim_id.in_(claim_ids[start : start + 200]))
            .order_by(EvidenceEvent.id)
        ):
            yield cast(EvidenceEvent, row)


def _keep_payload(
    value: Any, records: list[Record], seen: set[str], payloads: Path, report: CopyReport
) -> None:
    """Add the payload's record once. A large one is written to the folder that stands
    in for the object store, under the key its record names."""
    record = payload_record(value)
    if record.key in seen:
        return
    seen.add(record.key)
    if "r2_key" in record.body:
        held = payloads / record.body["r2_key"]
        held.parent.mkdir(parents=True, exist_ok=True)
        held.write_bytes(payload_of(value).text.encode())
        report.payload_objects += 1
    records.append(record)


def _first_slugs(
    session: Session, claims: list[Claim]
) -> tuple[dict[int, str], list[list[Record]]]:
    """The slug each claim is first handed over under, and the renames that bring it to
    the slug it has now, one run a rename so that each sees the one before it.

    The database keeps the slug a claim had before each rename that changed it. The
    store learns a former slug only from a `rename` action, and refuses one that names a
    slug it never held, so a renamed claim is handed over under its first slug and
    renamed again, in the order it was.
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
                    Record(
                        "action",
                        key_of("rename", change.former_slug, when(change.decided_at)),
                        body(
                            action="rename",
                            slug=change.former_slug,
                            new_slug=after,
                            decided_by=change.decided_by.value,
                            at=when(change.decided_at),
                        ),
                    )
                ]
            )
    return first, steps


def records_of(
    session: Session, claims: list[Claim], payloads: Path, report: CopyReport
) -> list[list[Record]]:
    """The runs of a copy of these claims, in the order they are merged: the claims
    under their first slugs, their renames, then everything else with the actions that
    archive, merge and publish. Each record is the pipeline's own natural-key form of
    its row (`thenwhat.store.records`)."""
    first_slug, rename_runs = _first_slugs(session, claims)
    slug = {claim.id: claim.slug for claim in claims}
    ids = sorted(slug)
    # What a merged claim keeps for itself is not handed over, nor its archive: the
    # store reads its slug as the claim it was merged into (`store/gather.py`).
    merged = {claim.id for claim in claims if claim.merged_into_id is not None}
    own = [claim_id for claim_id in ids if claim_id not in merged]

    def of_claims(model: Any, among: list[int] = ids) -> Iterable[Any]:
        for start in range(0, len(among), 1000):
            yield from session.scalars(
                select(model)
                .where(model.claim_id.in_(among[start : start + 1000]))
                .order_by(model.id)
            )

    tied_to_lead = set(session.scalars(select(LinkLead.claim_id).where(LinkLead.claim_id.in_(ids))))
    claim_records: list[Record] = []
    for claim in sorted(claims, key=lambda claim: claim.id):
        record = r.claim_record(
            claim, origin=r.claim_origin(claim, from_link_lead=claim.id in tied_to_lead)
        )
        first = first_slug[claim.id]
        claim_records.append(Record("claim", first, record.body | {"slug": first}))

    # --- the rows other rows name, read first ----------------------------------------
    articles: list[SourceArticle] = list(of_claims(SourceArticle))
    url_key: dict[int, str] = {}
    held_keys: set[tuple[int, str]] = set()
    for article in articles:
        key = article_key(article.url) or article.url
        if (article.claim_id, key) in held_keys:
            report.notes.append(
                f"{slug[article.claim_id]} holds two articles at one address key ({key});"
                " the store keeps the first."
            )
        held_keys.add((article.claim_id, key))
        url_key[article.id] = key
    entities: dict[int, Entity] = {entity.id: entity for entity in of_claims(Entity, own)}
    entity_ids = sorted(entities)

    def of_entities(model: Any) -> Iterable[Any]:
        for start in range(0, len(entity_ids), 1000):
            yield from session.scalars(
                select(model)
                .where(model.entity_id.in_(entity_ids[start : start + 1000]))
                .order_by(*model.__table__.primary_key.columns)
            )

    matches: dict[int, EntityMatch] = {match.id: match for match in of_entities(EntityMatch)}
    names = r.Names(
        claims=slug,
        articles={a.id: (slug[a.claim_id], url_key[a.id]) for a in articles},
        matches={
            match_id: (
                slug[entities[m.entity_id].claim_id],
                str(entities[m.entity_id].type.value),
                entities[m.entity_id].name,
                m.source_name,
                m.external_id,
            )
            for match_id, m in matches.items()
        },
    )

    rest: list[Record] = []
    payloads_first: list[Record] = []
    seen_payloads: set[str] = set()

    # --- what was reported ----------------------------------------------------------
    for article in articles:
        rest.append(
            r.source_article_record(
                article, slug=slug[article.claim_id], url_key=url_key[article.id]
            )
        )
    for promise in of_claims(Promise):
        rest.append(
            r.promise_record(
                promise, slug=slug[promise.claim_id], url_key=url_key[promise.source_article_id]
            )
        )
    for statement in of_claims(ReportedStatement):
        rest.append(
            r.reported_statement_record(
                statement,
                slug=slug[statement.claim_id],
                url_key=url_key[statement.source_article_id],
                names=names,
            )
        )

    # --- entities, matches, terms ---------------------------------------------------
    for entity in entities.values():
        rest.append(r.entity_record(entity, slug=slug[entity.claim_id]))
    for link in of_entities(EntityArticle):
        entity = entities[link.entity_id]
        if link.source_article_id in url_key:
            rest.append(
                r.entity_article_record(
                    link,
                    entity=entity,
                    slug=slug[entity.claim_id],
                    url_key=url_key[link.source_article_id],
                )
            )
    for match in matches.values():
        entity = entities[match.entity_id]
        rest.append(r.entity_match_record(match, entity=entity, slug=slug[entity.claim_id]))
    for term in of_claims(ClaimTerm, own):
        rest.append(r.claim_term_record(term, slug=slug[term.claim_id]))

    # --- the records of sources: small tables, copied whole --------------------------
    for term_record in session.scalars(
        select(TermRecord).order_by(TermRecord.source_name, TermRecord.external_id)
    ):
        rest.append(r.term_source_record(term_record))
    for organisation in session.scalars(
        select(OrganisationRecord).order_by(
            OrganisationRecord.source_name, OrganisationRecord.external_id
        )
    ):
        rest.append(r.organisation_source_record(organisation))
    for paper in session.scalars(select(PaperRecord).order_by(PaperRecord.id)):
        rest.append(r.paper_source_record(paper))

    # --- evidence -------------------------------------------------------------------
    dedupe_key: dict[int, str] = {}
    trial_ids: set[tuple[str, str]] = set()
    for event in _event_rows(session, own):
        dedupe_key[event.id] = event.dedupe_key
        trial_ids.add((event.source_name, event.external_id))
        matched = matches.get(event.entity_match_id) if event.entity_match_id else None
        _keep_payload(event.raw_payload, payloads_first, seen_payloads, payloads, report)
        rest.append(
            r.evidence_event_record(
                event,
                slug=slug[event.claim_id],
                match=None if matched is None else (entities[matched.entity_id], matched),
            )
        )
    for failure in of_claims(FailureFlag, own):
        rest.append(
            r.failure_flag_record(
                failure,
                slug=slug[failure.claim_id],
                dedupe_key=dedupe_key[failure.evidence_event_id],
            )
        )
    for read in session.scalars(select(TrialRead).order_by(TrialRead.id)):
        if (read.source_name, read.trial_id) not in trial_ids:
            continue
        readings = list(
            session.scalars(
                select(Reading).where(Reading.trial_read_id == read.id).order_by(Reading.id)
            )
        )
        rest.append(r.trial_read_record(read, readings=readings))

    # --- the decisions an export reads: a match's scoring, a claim's stage reading ---
    for decision in session.scalars(
        select(DecisionLog)
        .where(DecisionLog.step.in_([ENTITY_MATCH, PAPER_MATCH, EVIDENCE_STAGE]))
        .order_by(DecisionLog.id)
    ):
        # One that names no row of this copy keeps its row id, and is left out.
        if r.natural_ref(decision.input_ref, names) != decision.input_ref:
            rest.append(r.decision_record(decision, names=names))

    for icon in session.scalars(select(OutletIcon).order_by(OutletIcon.domain)):
        rest.append(r.outlet_icon_record(icon))

    # --- actions: a published time, an archive and a merge are not a claim's fields ---
    changes: dict[int, list[ClaimChange]] = {}
    for change in session.scalars(select(ClaimChange).order_by(ClaimChange.id)):
        changes.setdefault(change.claim_id, []).append(change)
    for claim in sorted(claims, key=lambda claim: claim.id):
        for action in r.claim_actions(claim, changes.get(claim.id, []), slug):
            kind = action.body["action"]
            # Renames went before, each in its own run.
            if kind == "rename" or (kind == "archive" and claim.id in merged):
                continue
            rest.append(action)

    # A record is staged under its kind and natural key, once. Where two rows of the
    # database have one key the store can hold only one: the first is handed over.
    everything: list[Record] = []
    handed: set[tuple[str, str]] = set()
    for record in [*payloads_first, *rest]:
        if (record.kind, record.key) in handed:
            report.folded[record.kind] = report.folded.get(record.kind, 0) + 1
            continue
        handed.add((record.kind, record.key))
        everything.append(record)
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
            for record in records:
                counts[record.kind] = counts.get(record.kind, 0) + 1
                report.handed[record.kind] = report.handed.get(record.kind, 0) + 1
            db.execute(
                ingest["register_run"],
                (run, "migration", "copy", None, "copy", now.isoformat(), None, None),
            )
            db.execute(ingest["state_steps"], (run, "{}"))
            db.execute(ingest["state_counts"], (run, json.dumps(counts)))
            for start in range(0, len(records), CHUNK_RECORDS):
                chunk = [record.staged() for record in records[start : start + CHUNK_RECORDS]]
                db.execute(ingest["stage"], (run, json.dumps(chunk)))
            # As a D1 batch: every statement or none, nothing read in between.
            db.execute("BEGIN")
            try:
                for statement in merge:
                    db.execute(statement, (run,) if "?1" in statement else ())
                db.execute("COMMIT")
            except sqlite3.Error as error:
                # Before the batch is undone, what it had counted says which records
                # found no parent.
                short = [
                    f"{kind}: {stated} handed over, {resolved} with a parent found"
                    for kind, stated, resolved in db.execute(
                        "SELECT t.kind, t.records, coalesce(m.resolved, 0) FROM run_stated t"
                        " LEFT JOIN merge_report m ON m.run_id = t.run_id AND m.kind = t.kind"
                        " WHERE t.run_id = ? AND t.records <> coalesce(m.resolved, 0)",
                        (run,),
                    )
                ]
                db.execute("ROLLBACK")
                raise CopyFailed(
                    f"The store's merge undid run {run}: {error}. {'; '.join(short)}"
                ) from error
            for kind, added in db.execute(
                "SELECT kind, added FROM merge_report WHERE run_id = ?", (run,)
            ):
                report.added[kind] = report.added.get(kind, 0) + added
            db.execute("DELETE FROM stg WHERE run_id = ?", (run,))
            report.runs += 1
    finally:
        db.close()
    return report
