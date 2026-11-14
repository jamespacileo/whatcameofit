"""Database tables. Terms are defined in GLOSSARY.md; behavior is specified in openspec/."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    LargeBinary,
    MetaData,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from thenwhat.domain import (
    ClaimStatus,
    Decider,
    EntityType,
    EventType,
    EvidenceStage,
    RegulatoryOutcome,
    ReviewState,
    TrialState,
)

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

TIMESTAMP = DateTime(timezone=True)


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def _enum(members: type[StrEnum], name: str) -> Enum:
    """Store enum values as text with a CHECK constraint, which is easier to migrate
    than a native Postgres enum."""
    return Enum(
        members,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=32,
        values_callable=lambda cls: [member.value for member in cls],
    )


def _review_decision_recorded() -> CheckConstraint:
    """A decision always records when it was made and who made it; a pending item has neither."""
    return CheckConstraint(
        "(review_state = 'pending') = (reviewed_at IS NULL)"
        " AND (reviewed_at IS NULL) = (reviewed_by IS NULL)",
        name="review_decision_recorded",
    )


class Reviewed:
    """Review columns shared by draft claims, matches and evidence events."""

    review_state: Mapped[ReviewState] = mapped_column(
        _enum(ReviewState, "review_state"),
        default=ReviewState.PENDING,
        server_default=ReviewState.PENDING.value,
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    reviewed_by: Mapped[Decider | None] = mapped_column(_enum(Decider, "reviewed_by"))


class Claim(Reviewed, Base):
    __tablename__ = "claim"
    __table_args__ = (
        CheckConstraint(
            "slug ~ '^[a-z0-9]+(-[a-z0-9]+)*$' AND char_length(slug) <= 60",
            name="slug_format",
        ),
        _review_decision_recorded(),
        CheckConstraint(
            "(archived_at IS NULL) = (archive_reason IS NULL)",
            name="archive_has_reason",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    headline: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    vertical: Mapped[str] = mapped_column(Text)
    # One of the configured approaches, or none. Never part of status.
    approach: Mapped[str | None] = mapped_column(Text)
    # The intervention half of a claim's identity is its intervention entity.
    indication: Mapped[str] = mapped_column(Text)
    first_reported_date: Mapped[date | None]
    evidence_stage: Mapped[EvidenceStage | None] = mapped_column(
        _enum(EvidenceStage, "evidence_stage")
    )
    current_status: Mapped[ClaimStatus] = mapped_column(
        _enum(ClaimStatus, "current_status"),
        default=ClaimStatus.PRECLINICAL_ONLY,
        server_default=ClaimStatus.PRECLINICAL_ONLY.value,
    )
    overlay_years: Mapped[int | None]
    status_updated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    # Taken off the public site by the operator. The record stays; the reason is never exported.
    archived_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    archive_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class SourceArticle(Base):
    __tablename__ = "source_article"
    __table_args__ = (UniqueConstraint("claim_id", "url", name="uq_source_article_claim_url"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    outlet: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    published_date: Mapped[date]
    content_hash: Mapped[str | None] = mapped_column(Text)
    archive_url: Mapped[str | None] = mapped_column(Text)


class Promise(Base):
    __tablename__ = "promise"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    source_article_id: Mapped[int] = mapped_column(ForeignKey("source_article.id"))
    description: Mapped[str] = mapped_column(Text)
    parsed_date: Mapped[date | None]


class Entity(Base):
    __tablename__ = "entity"
    __table_args__ = (
        Index(
            "uq_entity_origin_paper_per_claim",
            "claim_id",
            unique=True,
            postgresql_where=text("is_origin_paper"),
        ),
        CheckConstraint("NOT is_origin_paper OR type = 'paper'", name="origin_paper_is_paper"),
        CheckConstraint("doi IS NULL OR type = 'paper'", name="doi_only_on_papers"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    type: Mapped[EntityType] = mapped_column(_enum(EntityType, "type"))
    name: Mapped[str] = mapped_column(Text)
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    # Words a registry or a paper would use for an intervention that has no product
    # name. Searched for, within the claim's indication only, and never shown as a name.
    search_phrases: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}"
    )
    is_origin_paper: Mapped[bool] = mapped_column(default=False, server_default="false")
    # A DOI the article or operator gave for a paper. It is a lead for resolution,
    # not a confirmed identifier: confirmation is an approved match.
    doi: Mapped[str | None] = mapped_column(Text)


class EntityMatch(Reviewed, Base):
    __tablename__ = "entity_match"
    __table_args__ = (
        UniqueConstraint(
            "entity_id", "source_name", "external_id", name="uq_entity_match_entity_source_external"
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="score_range"),
        _review_decision_recorded(),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"), index=True)
    source_name: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str] = mapped_column(Text)
    score: Mapped[float]
    # What the registry record says, in one line, so a reviewer need not open every link.
    record_summary: Mapped[str | None] = mapped_column(Text)
    # Why the record is a candidate, as codes found by rule and without a model. The
    # site owns their wording.
    reasons: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class EvidenceEvent(Reviewed, Base):
    __tablename__ = "evidence_event"
    __table_args__ = (
        UniqueConstraint("claim_id", "dedupe_key", name="uq_evidence_event_claim_dedupe"),
        CheckConstraint("char_length(btrim(source_url)) > 0", name="source_url_present"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint(
            "(type = 'trial_status_change') = (trial_state IS NOT NULL)",
            name="status_change_has_state",
        ),
        CheckConstraint(
            "(type = 'regulatory_decision') = (regulatory_outcome IS NOT NULL)",
            name="regulatory_decision_has_outcome",
        ),
        _review_decision_recorded(),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    entity_match_id: Mapped[int | None] = mapped_column(ForeignKey("entity_match.id"))
    type: Mapped[EventType] = mapped_column(_enum(EventType, "type"))
    event_date: Mapped[date]
    date_basis: Mapped[str | None] = mapped_column(Text)
    source_name: Mapped[str] = mapped_column(Text)
    source_url: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str] = mapped_column(Text)
    trial_phases: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    trial_state: Mapped[TrialState | None] = mapped_column(_enum(TrialState, "trial_state"))
    regulatory_outcome: Mapped[RegulatoryOutcome | None] = mapped_column(
        _enum(RegulatoryOutcome, "regulatory_outcome")
    )
    summary: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float]
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    dedupe_key: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class FailureFlag(Base):
    __tablename__ = "failure_flag"
    __table_args__ = (
        UniqueConstraint("claim_id", "trial_external_id", name="uq_failure_flag_claim_trial"),
        CheckConstraint("char_length(btrim(source_url)) > 0", name="source_url_present"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    trial_external_id: Mapped[str] = mapped_column(Text)
    evidence_event_id: Mapped[int] = mapped_column(ForeignKey("evidence_event.id"))
    source_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class DecisionLog(Base):
    __tablename__ = "decision_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    step: Mapped[str] = mapped_column(Text, index=True)
    input_ref: Mapped[str] = mapped_column(Text)
    backend: Mapped[str] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    options: Mapped[list[str]] = mapped_column(JSONB)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    confidence: Mapped[float | None]
    error: Mapped[str | None] = mapped_column(Text)
    human_label: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class LlmUsage(Base):
    __tablename__ = "llm_usage"

    id: Mapped[int] = mapped_column(primary_key=True)
    purpose: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    input_tokens: Mapped[int]
    output_tokens: Mapped[int]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now(), index=True)


class HttpCache(Base):
    __tablename__ = "http_cache"

    request_key: Mapped[str] = mapped_column(Text, primary_key=True)
    source_name: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    expires_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class PaperRecord(Base):
    """The index record a paper's facts are read from (openspec paper-facts), kept once
    per paper with the time it was fetched.

    Unlike an evidence event's payload, this one is reduced before it is stored: the
    abstract, the authors, their identifiers and affiliations are removed. A row with
    no payload records that the index was asked and does not hold the paper.
    """

    __tablename__ = "paper_record"

    id: Mapped[int] = mapped_column(primary_key=True)
    # The DOI in lower case, else `pmid:<number>`, else the index's own identifier.
    identifier: Mapped[str] = mapped_column(Text, unique=True)
    source_name: Mapped[str] = mapped_column(Text)
    pubmed_id: Mapped[str | None] = mapped_column(Text, index=True)
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class OutletIcon(Base):
    """The small icon an outlet's own site serves, kept once per outlet domain.

    A row with no content records that the domain was asked and had no usable icon,
    so it is not asked again.
    """

    __tablename__ = "outlet_icon"
    __table_args__ = (
        CheckConstraint(
            "(content IS NULL) = (media_type IS NULL) AND (content IS NULL) = (icon_url IS NULL)",
            name="icon_is_whole",
        ),
    )

    domain: Mapped[str] = mapped_column(Text, primary_key=True)
    icon_url: Mapped[str | None] = mapped_column(Text)
    media_type: Mapped[str | None] = mapped_column(Text)
    content: Mapped[bytes | None] = mapped_column(LargeBinary)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)
