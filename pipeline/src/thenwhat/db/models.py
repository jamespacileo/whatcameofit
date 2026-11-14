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
    NamedBy,
    OutletKind,
    RegulatoryOutcome,
    ReviewState,
    StatementBasis,
    StatementFirmness,
    StatementKind,
    StatementSpeaker,
    TermFit,
    TermRole,
    TrialState,
    WorkOutcome,
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


class ReportedStatement(Reviewed, Base):
    """Something a source article says about a claim's intervention beyond its timeline,
    in the site's own words (GLOSSARY.md). Behavior: openspec reported-statements.

    Nothing of the article's text is kept: the statement is the pipeline's own wording,
    refused by rule before it is stored when it copies the article, quotes or names
    someone.
    """

    __tablename__ = "reported_statement"
    __table_args__ = (
        UniqueConstraint(
            "source_article_id", "text_key", name="uq_reported_statement_article_text_key"
        ),
        CheckConstraint("char_length(text) BETWEEN 1 AND 200", name="text_length"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        _review_decision_recorded(),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    source_article_id: Mapped[int] = mapped_column(ForeignKey("source_article.id"), index=True)
    text: Mapped[str] = mapped_column(Text)
    # The text compared without letter case, spacing or punctuation: one per article.
    text_key: Mapped[str] = mapped_column(Text)
    kind: Mapped[StatementKind] = mapped_column(_enum(StatementKind, "kind"))
    firmness: Mapped[StatementFirmness] = mapped_column(_enum(StatementFirmness, "firmness"))
    speaker: Mapped[StatementSpeaker] = mapped_column(_enum(StatementSpeaker, "speaker"))
    basis: Mapped[StatementBasis] = mapped_column(_enum(StatementBasis, "basis"))
    # The statement check's probability that the article says this.
    confidence: Mapped[float]
    # The statement check's log reference, `source_article:<id>:statement:<place>`.
    decision_ref: Mapped[str] = mapped_column(Text)
    # When the article was read for this statement: it is of the article as read then.
    article_read_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


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
        CheckConstraint(
            "cardinality(named_by) > 0 AND named_by <@ ARRAY['article', 'registry']::text[]",
            name="named_by_known",
        ),
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
    # Where the name came from: a source article, a registry record (a trial's lead
    # sponsor), or both. Values of `NamedBy`.
    named_by: Mapped[list[str]] = mapped_column(
        ARRAY(Text),
        default=lambda: [NamedBy.ARTICLE.value],
        server_default="{article}",
    )


class EntityArticle(Base):
    """A source article that named an organisation entity of its claim, so that the
    organisation's role can give the report's address (openspec organisations)."""

    __tablename__ = "entity_article"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"), primary_key=True)
    source_article_id: Mapped[int] = mapped_column(
        ForeignKey("source_article.id"), primary_key=True
    )


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


class ClaimTerm(Reviewed, Base):
    """A subject term proposed for a claim's condition or intervention, the term of its
    intervention kind, a gene named in its intervention, or a drug source's record of
    its intervention (GLOSSARY.md).
    Behavior: openspec knowledge-cards."""

    __tablename__ = "claim_term"
    __table_args__ = (
        UniqueConstraint(
            "claim_id",
            "role",
            "source_name",
            "external_id",
            name="uq_claim_term_claim_role_source_external",
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="score_range"),
        _review_decision_recorded(),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    role: Mapped[TermRole] = mapped_column(_enum(TermRole, "role"))
    source_name: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str] = mapped_column(Text)
    # The term's label as the candidate was gathered, so the queue can name it.
    label: Mapped[str] = mapped_column(Text)
    # Empty until the term check has an answer for the candidate.
    score: Mapped[float | None]
    # Whether it was read as the claim's own condition or intervention, or as broader,
    # or is the term of the intervention's kind. Empty when it was read as something
    # else, or not read yet.
    fit: Mapped[TermFit | None] = mapped_column(_enum(TermFit, "fit"))
    # Why the term is a candidate, found by rule: each a code with its counts or name.
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class TermRecord(Base):
    """A vocabulary term's own record as its source returned it, kept once per term."""

    __tablename__ = "term_record"

    source_name: Mapped[str] = mapped_column(Text, primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class OrganisationRecord(Base):
    """An organisation's own record as the organisation registry returned it, kept once
    per record with the time it was read (openspec organisations). The match score is
    the registry's answer for one name, so it stays on the match."""

    __tablename__ = "organisation_record"

    source_name: Mapped[str] = mapped_column(Text, primary_key=True)
    external_id: Mapped[str] = mapped_column(Text, primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class EntitySubstance(Base):
    """The one substance a registry of substances lists an intervention under, as that
    registry returned it, with the development codes it lists for the substance. An
    intervention the registry does not list, or lists under more than one substance,
    has no row."""

    __tablename__ = "entity_substance"

    entity_id: Mapped[int] = mapped_column(ForeignKey("entity.id"), primary_key=True)
    source_name: Mapped[str] = mapped_column(Text)
    # The substance's identifier at the source.
    external_id: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    # The names the source marks as codes for this substance. Searched for like search
    # phrases, within the claim's indication only, and never shown as a name.
    codes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")


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
    # SQL NULL, not a JSON null, when the index does not hold the paper.
    payload: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
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


class WorkEntry(Base):
    """One step finished, or failed, for one record at one version of the step.

    The record is named by its kind and id, not by a foreign key: a step can apply to
    any table. Behavior: openspec work-ledger.
    """

    __tablename__ = "work_entry"
    __table_args__ = (
        UniqueConstraint(
            "record_kind",
            "record_id",
            "step",
            "step_version",
            name="uq_work_entry_record_step_version",
        ),
        CheckConstraint("(outcome = 'failed') = (error IS NOT NULL)", name="failure_has_error"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    record_kind: Mapped[str] = mapped_column(Text)
    record_id: Mapped[int]
    step: Mapped[str] = mapped_column(Text)
    step_version: Mapped[int]
    outcome: Mapped[WorkOutcome] = mapped_column(_enum(WorkOutcome, "outcome"))
    attempts: Mapped[int]
    requests_used: Mapped[int]
    # A hash of the fields the step read. When the record's fields change, the entry is
    # marked stale and the record is due again.
    fingerprint: Mapped[str] = mapped_column(Text)
    stale: Mapped[bool] = mapped_column(default=False, server_default="false")
    error: Mapped[str | None] = mapped_column(Text)
    last_attempt_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class SourceAllowanceUse(Base):
    """How much of a source's allowance is used in the current period, for every process
    that asks that source. Behavior: openspec source-allowances."""

    __tablename__ = "source_allowance_use"

    source_name: Mapped[str] = mapped_column(Text, primary_key=True)
    period_start: Mapped[datetime] = mapped_column(TIMESTAMP)
    requests_used: Mapped[int]
    last_request_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    # Set when the source answered "too many requests": nothing is asked before this time.
    paused_until: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    refusals: Mapped[int] = mapped_column(default=0, server_default="0")


class RegistryTrial(Base):
    """A trial as a registry lists it, kept whether or not any claim refers to it.
    Not an evidence event and never exported. Behavior: openspec registry-corpus."""

    __tablename__ = "registry_trial"
    __table_args__ = (
        UniqueConstraint(
            "registry_name", "external_id", name="uq_registry_trial_registry_external"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    registry_name: Mapped[str] = mapped_column(Text)
    external_id: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    conditions: Mapped[list[str]] = mapped_column(ARRAY(Text))
    # Each intervention as the registry gives it: type, name and other names.
    interventions: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    phases: Mapped[list[str]] = mapped_column(ARRAY(Text))
    overall_status: Mapped[str | None] = mapped_column(Text)
    # As the registry writes it, which can be a month without a day.
    start_date: Mapped[str | None] = mapped_column(Text)
    sponsor_class: Mapped[str | None] = mapped_column(Text)
    # The intervention under test as a name alone, and the indication's telling words.
    # Worked out by rule on load; empty when the registry gives no usable name.
    search_name: Mapped[str | None] = mapped_column(Text)
    search_indication: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class RegistryLoad(Base):
    """When trials matching a condition were last loaded in full, so that the next load
    can ask only for what changed since."""

    __tablename__ = "registry_load"

    registry_name: Mapped[str] = mapped_column(Text, primary_key=True)
    condition: Mapped[str] = mapped_column(Text, primary_key=True)
    # The start of the last load that completed: changes are asked for from this time.
    loaded_from: Mapped[datetime] = mapped_column(TIMESTAMP)
    completed_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class ArticleLead(Base):
    """A news article a search found for a registry trial. Unreviewed, never a source
    article and never exported. Its text is never stored. Behavior: openspec article-leads."""

    __tablename__ = "article_lead"
    __table_args__ = (
        UniqueConstraint("registry_trial_id", "url", name="uq_article_lead_trial_url"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    registry_trial_id: Mapped[int] = mapped_column(ForeignKey("registry_trial.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    outlet: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    published_date: Mapped[date | None]
    outlet_kind: Mapped[OutletKind] = mapped_column(_enum(OutletKind, "outlet_kind"))
    source_name: Mapped[str] = mapped_column(Text)
    search_query: Mapped[str] = mapped_column(Text)
    raw_result: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)
