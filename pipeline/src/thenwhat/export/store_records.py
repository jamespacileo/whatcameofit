"""The export's records read from a SQLite file that has the truth store's schema
(`store/schema.sql`). Behavior: openspec truth-store, "The export is assembled once, from
either store".

The file is a snapshot of the store, opened read-only: nothing here writes, so the status
the assembly derives and a first published time stay on the objects handed over and go no
further. `first_published` names the claims that had no published time, for whoever
states the `publish` action to the store.

What differs from the pipeline's database, and how it is read:

- A record names its parent by the store's own row id. Ids are used here as the assembly
  uses them, to tie one record to another, and mean nothing outside this file.
- A raw payload is not in its record's row. It is the `payload` row with the record's
  checksum: its `body` when it is small, else the object `r2_key` names, which is read
  from `payloads`, a folder holding the objects under their keys. Every payload read is
  held to its checksum.
- Vocabulary terms, organisations and papers are rows of `source_record`.
- A trial's readings are a JSON list on its read.
- A decision names what it was made about by natural key: `claim:<slug>` for a claim,
  `entity_match:<slug>|<entity type>|<entity name>|<source>|<identifier>` for a match.
  A claim's former slugs are looked under too.
- A slug a rename replaced is a row of `claim_alias`.
"""

import hashlib
import json
import sqlite3
from collections.abc import Iterable, Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from thenwhat.db.models import (
    Claim,
    ClaimTerm,
    Entity,
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
)
from thenwhat.decide.core import Decision
from thenwhat.decide.steps import ENTITY_MATCH, EVIDENCE_STAGE, PAPER_MATCH
from thenwhat.domain import (
    ClaimStatus,
    Decider,
    EntityType,
    EventType,
    EvidenceStage,
    FollowUpUnit,
    MeasureCode,
    ReadBy,
    ReadingField,
    ReadingKind,
    RegulatoryOutcome,
    ReviewState,
    StatementBasis,
    StatementFirmness,
    StatementKind,
    StatementSpeaker,
    TermFit,
    TermRole,
    TrialState,
)
from thenwhat.sources.mesh import Mesh

# The tables an export reads. A snapshot need hold no other.
# Every table and column an export from the store reads, and nothing else of the store:
# the store's hot tier has to hold these (`store/store-tables.md`). No registry trial,
# lead, share, ledger entry, usage or measure is read: a trial's facts on a claim's page
# come from the raw payload of the claim's own evidence event.
#
# Of the rows: `source_record` of kind term, organisation and paper; `payload` rows an
# `evidence_event` names; `decision_log` rows of the steps entity_match, paper_match and
# evidence_stage whose `input_ref` names a claim or a match.
COLUMNS_READ: dict[str, tuple[str, ...]] = {
    "claim": (
        "id",
        "slug",
        "headline",
        "summary",
        "vertical",
        "approach",
        "indication",
        "first_reported_date",
        "evidence_stage",
        "current_status",
        "overlay_years",
        "status_updated_at",
        "review_state",
        "reviewed_at",
        "reviewed_by",
        "published_at",
        "archived_at",
        "archive_reason",
        "awaiting_audit_at",
        "merged_into",
        "created_at",
    ),
    "claim_alias": ("slug", "claim_id"),
    "source_article": (
        "id",
        "claim_id",
        "url",
        "outlet",
        "title",
        "published_date",
        "content_hash",
        "archive_url",
    ),
    "promise": ("id", "claim_id", "source_article_id", "description", "parsed_date"),
    "reported_statement": (
        "id",
        "claim_id",
        "source_article_id",
        "text",
        "text_key",
        "kind",
        "firmness",
        "speaker",
        "basis",
        "confidence",
        "decision_ref",
        "article_read_at",
        "review_state",
        "reviewed_at",
        "reviewed_by",
        "created_at",
    ),
    "entity": (
        "id",
        "claim_id",
        "type",
        "name",
        "synonyms",
        "search_phrases",
        "is_origin_paper",
        "doi",
        "named_by",
    ),
    "entity_article": ("entity_id", "source_article_id"),
    "entity_match": (
        "id",
        "entity_id",
        "source_name",
        "external_id",
        "score",
        "record_summary",
        "record_facts",
        "reasons",
        "review_state",
        "reviewed_at",
        "reviewed_by",
        "created_at",
    ),
    "claim_term": (
        "id",
        "claim_id",
        "role",
        "source_name",
        "external_id",
        "label",
        "score",
        "fit",
        "reasons",
        "review_state",
        "reviewed_at",
        "reviewed_by",
        "created_at",
    ),
    "source_record": (
        "kind",
        "source_name",
        "external_id",
        "pubmed_id",
        "url",
        "body",
        "fetched_at",
    ),
    "evidence_event": (
        "id",
        "claim_id",
        "entity_match_id",
        "dedupe_key",
        "type",
        "event_date",
        "date_basis",
        "source_name",
        "source_url",
        "external_id",
        "trial_phases",
        "trial_state",
        "regulatory_outcome",
        "summary",
        "confidence",
        "payload_sha256",
        "fetched_at",
        "review_state",
        "reviewed_at",
        "reviewed_by",
        "created_at",
    ),
    "failure_flag": (
        "id",
        "claim_id",
        "trial_external_id",
        "evidence_event_id",
        "source_url",
        "created_at",
    ),
    "trial_read": ("source_name", "trial_id", "input_hash", "readings"),
    "payload": ("sha256", "body", "r2_key"),
    "decision_log": (
        "seq",
        "step",
        "input_ref",
        "output",
        "confidence",
        "error",
        "created_at",
    ),
    "outlet_icon": ("domain", "icon_url", "media_type", "content", "fetched_at"),
}
TABLES_READ = tuple(COLUMNS_READ)


class StoreFault(Exception):
    """The store file cannot give an export: a table or a payload is missing, or a
    payload is not the one its checksum names."""


def _time(text: str) -> datetime:
    return datetime.fromisoformat(text).astimezone(UTC)


def _time_or_none(text: str | None) -> datetime | None:
    return None if text is None else _time(text)


def _day_or_none(text: str | None) -> date | None:
    return None if text is None else date.fromisoformat(text[:10])


def _decider(text: str | None) -> Decider | None:
    return None if text is None else Decider(text)


def match_ref(slug: str, entity_type: str, entity_name: str, source: str, identifier: str) -> str:
    """How a decision about a match names the match in the store."""
    return f"{ENTITY_MATCH}:{slug}|{entity_type}|{entity_name}|{source}|{identifier}"


def claim_ref(slug: str) -> str:
    """How a decision about a claim names the claim in the store."""
    return f"claim:{slug}"


class StoreRecords:
    """A `Records` over a SQLite file of the store's schema. Reading only."""

    def __init__(self, path: Path, *, payloads: Path | None = None) -> None:
        if not path.is_file():
            raise StoreFault(f"No store file at {path}.")
        self.db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        self.db.row_factory = sqlite3.Row
        self.payloads = payloads
        try:
            held = {name for (name,) in self.db.execute("SELECT name FROM sqlite_master")}
            missing = [table for table in TABLES_READ if table not in held]
            lacking = [
                f"{table}.{column}"
                for table, columns in COLUMNS_READ.items()
                if table in held
                for column in columns
                if column not in {row[1] for row in self.db.execute(f"PRAGMA table_xinfo({table})")}
            ]
        except sqlite3.DatabaseError as error:
            self.db.close()
            raise StoreFault(f"{path} is not a store file: {error}.") from error
        if missing or lacking:
            self.db.close()
            said = []
            if missing:
                said.append(f"it has no table {', '.join(missing)}")
            if lacking:
                said.append(f"it has no column {', '.join(lacking)}")
            raise StoreFault(
                f"{path} does not have the store's schema as an export reads it:"
                f" {' and '.join(said)}."
            )
        # Slugs of the claims that had no published time when they were read.
        self.first_published: list[str] = []
        # What a match's decisions are filed under, by the match's id.
        self._match_names: dict[int, tuple[int, str, str]] = {}
        self._slugs: dict[int, list[str]] = {}
        self._payloads: dict[str, dict[str, Any]] = {}

    def close(self) -> None:
        self.db.close()

    def _rows(self, sql: str, *args: object) -> Iterator[sqlite3.Row]:
        return iter(self.db.execute(sql, args))

    # --- claims ---------------------------------------------------------------------

    def _claim(self, row: sqlite3.Row) -> Claim:
        return Claim(
            id=row["id"],
            slug=row["slug"],
            headline=row["headline"],
            summary=row["summary"],
            vertical=row["vertical"],
            approach=row["approach"],
            indication=row["indication"],
            first_reported_date=_day_or_none(row["first_reported_date"]),
            evidence_stage=(
                None if row["evidence_stage"] is None else EvidenceStage(row["evidence_stage"])
            ),
            current_status=ClaimStatus(row["current_status"]),
            overlay_years=row["overlay_years"],
            status_updated_at=_time_or_none(row["status_updated_at"]),
            review_state=ReviewState(row["review_state"]),
            reviewed_at=_time_or_none(row["reviewed_at"]),
            reviewed_by=_decider(row["reviewed_by"]),
            published_at=_time_or_none(row["published_at"]),
            archived_at=_time_or_none(row["archived_at"]),
            archive_reason=row["archive_reason"],
            awaiting_audit_at=_time_or_none(row["awaiting_audit_at"]),
            merged_into_id=row["merged_into"],
            created_at=_time(row["created_at"]),
        )

    def published_claims(self) -> Iterable[Claim]:
        claims = [
            self._claim(row)
            for row in self._rows(
                "SELECT * FROM claim WHERE review_state = 'approved' AND archived_at IS NULL"
                " AND awaiting_audit_at IS NULL ORDER BY slug"
            )
        ]
        self.first_published = [claim.slug for claim in claims if claim.published_at is None]
        return claims

    def held(self) -> int:
        """How many approved, unarchived claims are left out as awaiting audit."""
        return self.db.execute(
            "SELECT count(*) FROM claim WHERE review_state = 'approved' AND archived_at IS NULL"
            " AND awaiting_audit_at IS NOT NULL"
        ).fetchone()[0]

    def taken_down(self) -> Iterable[Claim]:
        return [
            self._claim(row)
            for row in self._rows(
                "SELECT * FROM claim WHERE archived_at IS NOT NULL AND published_at IS NOT NULL"
            )
        ]

    def moved(self) -> list[tuple[str, Claim]]:
        moved: dict[str, Claim] = {}
        for row in self._rows(
            "SELECT gone.slug AS former, kept.* FROM claim gone"
            " JOIN claim kept ON kept.id = gone.merged_into WHERE gone.published_at IS NOT NULL"
        ):
            moved[row["former"]] = self._claim(row)
        for row in self._rows(
            "SELECT a.slug AS former, leads.* FROM claim_alias a"
            " JOIN claim named ON named.id = a.claim_id"
            " JOIN claim leads ON leads.id = coalesce(named.merged_into, named.id)"
            " WHERE a.slug <> named.slug"
        ):
            moved[row["former"]] = self._claim(row)
        return sorted(moved.items())

    def _slugs_of(self, claim_id: int) -> list[str]:
        """The claim's slug and every slug it used to have."""
        if claim_id not in self._slugs:
            self._slugs[claim_id] = [
                row["slug"]
                for row in self._rows(
                    "SELECT slug FROM claim WHERE id = ?1"
                    " UNION SELECT slug FROM claim_alias WHERE claim_id = ?1",
                    claim_id,
                )
            ]
        return self._slugs[claim_id]

    def decided_by_assistant(self, claim: Claim) -> bool:
        if claim.reviewed_by is Decider.ASSISTANT:
            return True
        found = self.db.execute(
            "SELECT EXISTS (SELECT 1 FROM entity_match m JOIN entity e ON e.id = m.entity_id"
            "               WHERE e.claim_id = ?1 AND m.reviewed_by = 'assistant')"
            " OR EXISTS (SELECT 1 FROM evidence_event WHERE claim_id = ?1"
            "            AND reviewed_by = 'assistant')"
            " OR EXISTS (SELECT 1 FROM reported_statement WHERE claim_id = ?1"
            "            AND reviewed_by = 'assistant')",
            (claim.id,),
        ).fetchone()
        return bool(found[0])

    # --- evidence -------------------------------------------------------------------

    def _payload(self, sha256: str) -> dict[str, Any]:
        if sha256 in self._payloads:
            return self._payloads[sha256]
        row = self.db.execute(
            "SELECT body, r2_key FROM payload WHERE sha256 = ?", (sha256,)
        ).fetchone()
        if row is None:
            raise StoreFault(f"The store names the payload {sha256} and does not hold it.")
        if row["body"] is not None:
            raw = row["body"].encode()
        else:
            if self.payloads is None:
                raise StoreFault(
                    f"The payload {sha256} is the object {row['r2_key']}, and no folder of"
                    " payload objects was given (--payloads)."
                )
            held = self.payloads / row["r2_key"]
            if not held.is_file():
                raise StoreFault(f"The payload object {row['r2_key']} is not in {self.payloads}.")
            raw = held.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha256:
            raise StoreFault(f"The payload held as {sha256} does not have that checksum.")
        payload = json.loads(raw)
        # A registry record is often behind several events of one claim, and no more.
        if len(self._payloads) >= 64:
            self._payloads.clear()
        self._payloads[sha256] = payload
        return payload

    def events(self, claim: Claim) -> list[EvidenceEvent]:
        return [
            EvidenceEvent(
                id=row["id"],
                claim_id=row["claim_id"],
                entity_match_id=row["entity_match_id"],
                dedupe_key=row["dedupe_key"],
                type=EventType(row["type"]),
                event_date=date.fromisoformat(row["event_date"]),
                date_basis=row["date_basis"],
                source_name=row["source_name"],
                source_url=row["source_url"],
                external_id=row["external_id"],
                trial_phases=(
                    None if row["trial_phases"] is None else json.loads(row["trial_phases"])
                ),
                trial_state=None if row["trial_state"] is None else TrialState(row["trial_state"]),
                regulatory_outcome=(
                    None
                    if row["regulatory_outcome"] is None
                    else RegulatoryOutcome(row["regulatory_outcome"])
                ),
                summary=row["summary"],
                confidence=row["confidence"],
                raw_payload=self._payload(row["payload_sha256"]),
                fetched_at=_time(row["fetched_at"]),
                review_state=ReviewState(row["review_state"]),
                reviewed_at=_time_or_none(row["reviewed_at"]),
                reviewed_by=_decider(row["reviewed_by"]),
                created_at=_time(row["created_at"]),
            )
            for row in self._rows(
                "SELECT * FROM evidence_event WHERE claim_id = ? AND review_state = 'approved'"
                " ORDER BY event_date, id",
                claim.id,
            )
        ]

    def failure_flags(self, claim: Claim) -> list[FailureFlag]:
        return [
            FailureFlag(
                id=row["id"],
                claim_id=row["claim_id"],
                trial_external_id=row["trial_external_id"],
                evidence_event_id=row["evidence_event_id"],
                source_url=row["source_url"],
                created_at=_time(row["created_at"]),
            )
            for row in self._rows(
                "SELECT * FROM failure_flag WHERE claim_id = ? ORDER BY id", claim.id
            )
        ]

    # --- what was reported ----------------------------------------------------------

    @staticmethod
    def _article(row: sqlite3.Row, prefix: str = "") -> SourceArticle:
        return SourceArticle(
            id=row[f"{prefix}id"],
            claim_id=row[f"{prefix}claim_id"],
            url=row[f"{prefix}url"],
            outlet=row[f"{prefix}outlet"],
            title=row[f"{prefix}title"],
            published_date=date.fromisoformat(row[f"{prefix}published_date"]),
            content_hash=row[f"{prefix}content_hash"],
            archive_url=row[f"{prefix}archive_url"],
        )

    def articles(self, claim: Claim) -> list[SourceArticle]:
        return [
            self._article(row)
            for row in self._rows(
                "SELECT * FROM source_article WHERE claim_id = ? ORDER BY published_date, id",
                claim.id,
            )
        ]

    def promises(self, claim: Claim) -> list[Promise]:
        return [
            Promise(
                id=row["id"],
                claim_id=row["claim_id"],
                source_article_id=row["source_article_id"],
                description=row["description"],
                parsed_date=_day_or_none(row["parsed_date"]),
            )
            for row in self._rows(
                "SELECT p.* FROM promise p JOIN source_article a ON a.id = p.source_article_id"
                " WHERE p.claim_id = ? ORDER BY a.published_date, p.id",
                claim.id,
            )
        ]

    def statements(self, claim: Claim) -> list[tuple[ReportedStatement, SourceArticle]]:
        return [
            (
                ReportedStatement(
                    id=row["id"],
                    claim_id=row["claim_id"],
                    source_article_id=row["source_article_id"],
                    text=row["text"],
                    text_key=row["text_key"],
                    kind=StatementKind(row["kind"]),
                    firmness=StatementFirmness(row["firmness"]),
                    speaker=StatementSpeaker(row["speaker"]),
                    basis=StatementBasis(row["basis"]),
                    confidence=row["confidence"],
                    decision_ref=row["decision_ref"],
                    article_read_at=_time(row["article_read_at"]),
                    review_state=ReviewState(row["review_state"]),
                    reviewed_at=_time_or_none(row["reviewed_at"]),
                    reviewed_by=_decider(row["reviewed_by"]),
                    created_at=_time(row["created_at"]),
                ),
                self._article(row, "a_"),
            )
            for row in self._rows(
                "SELECT s.*, a.id AS a_id, a.claim_id AS a_claim_id, a.url AS a_url,"
                " a.outlet AS a_outlet, a.title AS a_title, a.published_date AS a_published_date,"
                " a.content_hash AS a_content_hash, a.archive_url AS a_archive_url"
                " FROM reported_statement s JOIN source_article a ON a.id = s.source_article_id"
                " WHERE s.claim_id = ? AND s.review_state = 'approved'"
                " ORDER BY a.published_date, a.id, s.id",
                claim.id,
            )
        ]

    # --- entities and matches -------------------------------------------------------

    def entities(self, claim: Claim) -> list[Entity]:
        return [
            Entity(
                id=row["id"],
                claim_id=row["claim_id"],
                type=EntityType(row["type"]),
                name=row["name"],
                synonyms=json.loads(row["synonyms"]),
                search_phrases=json.loads(row["search_phrases"]),
                is_origin_paper=bool(row["is_origin_paper"]),
                doi=row["doi"],
                named_by=json.loads(row["named_by"]),
            )
            for row in self._rows("SELECT * FROM entity WHERE claim_id = ? ORDER BY id", claim.id)
        ]

    def _match(self, row: sqlite3.Row) -> EntityMatch:
        self._match_names[row["id"]] = (row["claim_id"], row["entity_type"], row["entity_name"])
        return EntityMatch(
            id=row["id"],
            entity_id=row["entity_id"],
            source_name=row["source_name"],
            external_id=row["external_id"],
            score=row["score"],
            record_summary=row["record_summary"],
            record_facts=(None if row["record_facts"] is None else json.loads(row["record_facts"])),
            reasons=json.loads(row["reasons"]),
            review_state=ReviewState(row["review_state"]),
            reviewed_at=_time_or_none(row["reviewed_at"]),
            reviewed_by=_decider(row["reviewed_by"]),
            created_at=_time(row["created_at"]),
        )

    _MATCH = (
        "SELECT m.*, e.claim_id, e.type AS entity_type, e.name AS entity_name"
        " FROM entity_match m JOIN entity e ON e.id = m.entity_id"
    )

    def approved_matches(self, entity: Entity) -> list[EntityMatch]:
        return [
            self._match(row)
            for row in self._rows(
                f"{self._MATCH} WHERE m.entity_id = ? AND m.review_state = 'approved'"
                " ORDER BY m.score DESC, m.id",
                entity.id,
            )
        ]

    def shown_matches(self, claim: Claim, *, but_from: tuple[str, ...]) -> list[EntityMatch]:
        return [
            self._match(row)
            for row in self._rows(
                f"{self._MATCH} WHERE e.claim_id = ?"
                " AND m.review_state IN ('approved', 'pending') ORDER BY m.score DESC, m.id",
                claim.id,
            )
            if row["source_name"] not in but_from
        ]

    def _latest_decision(self, steps: tuple[str, ...], refs: list[str]) -> sqlite3.Row | None:
        """The latest decision of these steps about any of these names that gave no
        error: by the time it was made, then by its place in its run."""
        marks = ", ".join("?" * len(steps)), ", ".join("?" * len(refs))
        return self.db.execute(
            f"SELECT seq, output, confidence FROM decision_log WHERE step IN ({marks[0]})"
            f" AND input_ref IN ({marks[1]}) AND error IS NULL"
            " ORDER BY created_at DESC, seq DESC LIMIT 1",
            (*steps, *refs),
        ).fetchone()

    def match_reading(self, match: EntityMatch) -> str | None:
        claim_id, entity_type, entity_name = self._match_names[match.id]
        scored = self._latest_decision(
            (ENTITY_MATCH, PAPER_MATCH),
            [
                match_ref(slug, entity_type, entity_name, match.source_name, match.external_id)
                for slug in self._slugs_of(claim_id)
            ],
        )
        if scored is None or scored["output"] is None:
            return None
        output = json.loads(scored["output"])
        choice = output.get("choice") if isinstance(output, dict) else None
        return choice if isinstance(choice, str) else None

    def named_in(self, entity: Entity) -> list[int]:
        return [
            row["source_article_id"]
            for row in self._rows(
                "SELECT source_article_id FROM entity_article WHERE entity_id = ?", entity.id
            )
        ]

    def stage_reading(self, claim: Claim) -> Decision | None:
        read = self._latest_decision(
            (EVIDENCE_STAGE,), [claim_ref(slug) for slug in self._slugs_of(claim.id)]
        )
        if read is None or read["output"] is None or read["confidence"] is None:
            return None
        output = json.loads(read["output"])
        return Decision(output["choice"], output["probabilities"], read["confidence"], read["seq"])

    # --- terms and the records of sources -------------------------------------------

    def terms(self, claim: Claim) -> list[ClaimTerm]:
        return [
            ClaimTerm(
                id=row["id"],
                claim_id=row["claim_id"],
                role=TermRole(row["role"]),
                source_name=row["source_name"],
                external_id=row["external_id"],
                label=row["label"],
                score=row["score"],
                fit=None if row["fit"] is None else TermFit(row["fit"]),
                reasons=json.loads(row["reasons"]),
                review_state=ReviewState(row["review_state"]),
                reviewed_at=_time_or_none(row["reviewed_at"]),
                reviewed_by=_decider(row["reviewed_by"]),
                created_at=_time(row["created_at"]),
            )
            for row in self._rows(
                "SELECT * FROM claim_term WHERE claim_id = ? AND review_state = 'approved'"
                " ORDER BY id",
                claim.id,
            )
        ]

    def _source_record(self, kind: str, source_name: str, external_id: str) -> sqlite3.Row | None:
        return self.db.execute(
            "SELECT * FROM source_record WHERE kind = ? AND source_name = ? AND external_id = ?",
            (kind, source_name, external_id),
        ).fetchone()

    def term_record(self, source_name: str, external_id: str) -> TermRecord | None:
        row = self._source_record("term", source_name, external_id)
        if row is None or row["body"] is None:
            return None
        return TermRecord(
            source_name=row["source_name"],
            external_id=row["external_id"],
            url=row["url"],
            payload=json.loads(row["body"]),
            fetched_at=_time(row["fetched_at"]),
        )

    def mesh_records(self) -> list[TermRecord]:
        return [
            TermRecord(
                source_name=row["source_name"],
                external_id=row["external_id"],
                url=row["url"],
                payload=json.loads(row["body"]),
                fetched_at=_time(row["fetched_at"]),
            )
            for row in self._rows(
                "SELECT * FROM source_record WHERE kind = 'term' AND source_name = ?"
                " AND body IS NOT NULL ORDER BY external_id",
                Mesh.name,
            )
        ]

    def organisation_record(self, source_name: str, external_id: str) -> OrganisationRecord | None:
        row = self._source_record("organisation", source_name, external_id)
        if row is None or row["body"] is None:
            return None
        return OrganisationRecord(
            source_name=row["source_name"],
            external_id=row["external_id"],
            url=row["url"],
            payload=json.loads(row["body"]),
            fetched_at=_time(row["fetched_at"]),
        )

    def paper(
        self, *, doi: str | None, pubmed_id: str | None, identifier: str | None
    ) -> PaperRecord | None:
        for column, value in (
            ("external_id", doi.lower() if doi else None),
            ("pubmed_id", pubmed_id),
            ("external_id", identifier),
        ):
            if not value:
                continue
            row = self.db.execute(
                f"SELECT * FROM source_record WHERE kind = 'paper' AND {column} = ?"
                " ORDER BY fetched_at DESC, source_name, external_id LIMIT 1",
                (value,),
            ).fetchone()
            if row is not None:
                return PaperRecord(
                    identifier=row["external_id"],
                    source_name=row["source_name"],
                    pubmed_id=row["pubmed_id"],
                    payload=None if row["body"] is None else json.loads(row["body"]),
                    fetched_at=_time(row["fetched_at"]),
                )
        return None

    def trial_read(self, source_name: str, trial_id: str) -> tuple[str, list[Reading]] | None:
        row = self.db.execute(
            "SELECT input_hash, readings FROM trial_read WHERE source_name = ? AND trial_id = ?",
            (source_name, trial_id),
        ).fetchone()
        if row is None:
            return None
        readings = [
            Reading(
                outcome=held["outcome"],
                kind=ReadingKind(held["kind"]),
                field=ReadingField(held["field"]),
                # A writer leaves an empty field out of a reading.
                words=held.get("words"),
                number=held.get("number"),
                unit=None if held.get("unit") is None else FollowUpUnit(held["unit"]),
                code=None if held.get("code") is None else MeasureCode(held["code"]),
                confidence=held["confidence"],
                decided_by=ReadBy(held["decided_by"]),
            )
            for held in json.loads(row["readings"])
        ]
        readings.sort(key=lambda reading: (reading.outcome, reading.kind.value))
        return row["input_hash"], readings

    def outlet_icons(self, domains: set[str]) -> list[OutletIcon]:
        return [
            OutletIcon(
                domain=row["domain"],
                icon_url=row["icon_url"],
                media_type=row["media_type"],
                content=row["content"],
                fetched_at=_time(row["fetched_at"]),
            )
            for row in self._rows("SELECT * FROM outlet_icon ORDER BY domain")
            if row["domain"] in domains
        ]

    def done(self) -> None:
        """Nothing is written: the store takes a publication as an action of its own."""
