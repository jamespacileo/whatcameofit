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
    ForeignKeyConstraint,
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
    FollowUpUnit,
    LeadVerdict,
    MeasureCode,
    NamedBy,
    OutletKind,
    ReadBy,
    ReadingField,
    ReadingKind,
    ReadOutcome,
    RegulatoryOutcome,
    ReviewState,
    ScreenOutcome,
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


def _article_of_claim(name: str) -> ForeignKeyConstraint:
    """A row that names a source article and a claim names the article's own claim. An
    article moved to another claim, as a duplicate's are, takes the row with it."""
    return ForeignKeyConstraint(
        ["source_article_id", "claim_id"],
        ["source_article.id", "source_article.claim_id"],
        name=name,
        onupdate="CASCADE",
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
        CheckConstraint(
            "merged_into_id IS NULL OR (archived_at IS NOT NULL AND merged_into_id <> id)",
            name="merged_is_archived",
        ),
        CheckConstraint(
            "approach IS NOT NULL OR (approach_decided_by IS NULL AND approach_basis IS NULL)",
            name="approach_record_has_approach",
        ),
        CheckConstraint(
            "approach_basis IS NULL OR approach_decided_by = 'rule'",
            name="approach_basis_is_a_rules",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(Text, unique=True)
    headline: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    vertical: Mapped[str] = mapped_column(Text)
    # One of the configured approaches, or none. Never part of status.
    approach: Mapped[str | None] = mapped_column(Text)
    # Who set the approach, and for one a rule set, what the registry says that it was
    # set on (openspec health-areas). Both empty with no approach; the first is also empty
    # for an approach stored before it was recorded, which no rule may then change.
    approach_decided_by: Mapped[Decider | None] = mapped_column(
        _enum(Decider, "approach_decided_by")
    )
    approach_basis: Mapped[dict[str, Any] | None] = mapped_column(JSONB(none_as_null=True))
    # The intervention half of a claim's identity is its intervention entity.
    indication: Mapped[str] = mapped_column(Text)
    first_reported_date: Mapped[date | None]
    evidence_stage: Mapped[EvidenceStage | None] = mapped_column(
        _enum(EvidenceStage, "evidence_stage")
    )
    current_status: Mapped[ClaimStatus] = mapped_column(
        _enum(ClaimStatus, "current_status"),
        default=ClaimStatus.NO_TRIAL_FOUND,
        server_default=ClaimStatus.NO_TRIAL_FOUND.value,
    )
    overlay_years: Mapped[int | None]
    status_updated_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    published_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    # Taken off the public site by the operator. The record stays; the reason is never exported.
    archived_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    archive_reason: Mapped[str | None] = mapped_column(Text)
    # Approved by `thenwhat prepare` for a link lead's read, and held off the site until
    # the batch it came in has been audited (`thenwhat audit clear`). Never exported.
    awaiting_audit_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    # The claim this one was merged into (`thenwhat claim merge`). A merged claim is
    # archived, stands for no intervention any more, and its address leads to that claim.
    merged_into_id: Mapped[int | None] = mapped_column(ForeignKey("claim.id"), index=True)
    # Set when the intervention gained or changed a name, so its registries are to be
    # searched again (`thenwhat prepare --due`): the time a new search was last asked
    # for. Its change makes the claim due for its search steps; a search leaves it as it is.
    registry_search_due_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class ClaimChange(Base):
    """A correction to which claim stands for a treatment, or to what its intervention
    is called: a merge of one claim into another, or a rename. Kept for good, with who
    decided it. Behavior: openspec claims, "Merging duplicate claims" and "Renaming an
    intervention"."""

    __tablename__ = "claim_change"
    __table_args__ = (
        CheckConstraint("kind IN ('merge', 'rename')", name="kind_known"),
        CheckConstraint("decided_by IN ('human', 'assistant')", name="decided_by_a_reader"),
        CheckConstraint("(kind = 'merge') = (into_claim_id IS NOT NULL)", name="merge_has_target"),
        CheckConstraint(
            "(kind = 'rename') = (old_name IS NOT NULL) AND (kind = 'rename') ="
            " (new_name IS NOT NULL)",
            name="rename_has_names",
        ),
        CheckConstraint("kind = 'rename' OR former_slug IS NULL", name="former_slug_of_a_rename"),
        CheckConstraint("(kind = 'merge') = (record IS NOT NULL)", name="merge_has_record"),
        CheckConstraint(
            "(undone_at IS NULL) = (undone_by IS NULL) AND (undone_at IS NULL OR kind = 'merge')"
            " AND (undone_by IS NULL OR undone_by IN ('human', 'assistant'))",
            name="undone_is_recorded",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    # The claim that was merged away, or whose intervention was renamed.
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    kind: Mapped[str] = mapped_column(Text)
    into_claim_id: Mapped[int | None] = mapped_column(ForeignKey("claim.id"))
    old_name: Mapped[str | None] = mapped_column(Text)
    new_name: Mapped[str | None] = mapped_column(Text)
    # The slug the claim had before a rename made it a new one. The address stays taken,
    # and leads to the claim's page wherever that now is.
    former_slug: Mapped[str | None] = mapped_column(Text, unique=True)
    # Private, like an archive reason: never exported.
    reason: Mapped[str | None] = mapped_column(Text)
    decided_by: Mapped[Decider] = mapped_column(_enum(Decider, "decided_by"))
    decided_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    # For a merge: every row it moved and every name it added, by id, with what shows
    # the two interventions are one treatment. `claim unmerge` puts back exactly these.
    record: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # Set when a merge was undone, with who undid it and why. The row is kept.
    undone_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    undone_by: Mapped[Decider | None] = mapped_column(_enum(Decider, "undone_by"))
    undone_reason: Mapped[str | None] = mapped_column(Text)


class SourceArticle(Base):
    __tablename__ = "source_article"
    __table_args__ = (
        UniqueConstraint("claim_id", "url", name="uq_source_article_claim_url"),
        # So that a row naming both an article and a claim can be held to the article's own.
        UniqueConstraint("id", "claim_id", name="uq_source_article_id_claim"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    url: Mapped[str] = mapped_column(Text)
    outlet: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    published_date: Mapped[date]
    content_hash: Mapped[str | None] = mapped_column(Text)
    archive_url: Mapped[str | None] = mapped_column(Text)
    # The registry numbers and paper DOIs the article's page names, as the page reader
    # gave them: identifiers only, never the article's text. The step `claim_named_records`
    # looks them up as candidates of the claim (openspec lead-reading).
    named_registry_numbers: Mapped[list[str]] = mapped_column(
        ARRAY(Text), default=list, server_default="{}"
    )
    named_dois: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list, server_default="{}")


class Promise(Base):
    __tablename__ = "promise"
    __table_args__ = (_article_of_claim("fk_promise_article_of_claim"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    source_article_id: Mapped[int] = mapped_column(ForeignKey("source_article.id"), index=True)
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
        _article_of_claim("fk_reported_statement_article_of_claim"),
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
        # The intervention half of a claim's identity: one, never two.
        Index(
            "uq_entity_intervention_per_claim",
            "claim_id",
            unique=True,
            postgresql_where=text("type = 'intervention'"),
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
        ForeignKey("source_article.id"), primary_key=True, index=True
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
    # The same record field by field, for a trial: title, conditions, interventions,
    # phases and state (openspec registry-record-rows). None for a paper, and for a match
    # stored before the field existed until `entity record-facts` fills it.
    record_facts: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
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
        # So that a failure flag can be held to its event's own claim.
        UniqueConstraint("id", "claim_id", name="uq_evidence_event_id_claim"),
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
    entity_match_id: Mapped[int | None] = mapped_column(ForeignKey("entity_match.id"), index=True)
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
        ForeignKeyConstraint(
            ["evidence_event_id", "claim_id"],
            ["evidence_event.id", "evidence_event.claim_id"],
            name="fk_failure_flag_event_of_claim",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    trial_external_id: Mapped[str] = mapped_column(Text)
    evidence_event_id: Mapped[int] = mapped_column(ForeignKey("evidence_event.id"), index=True)
    source_url: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class TrialRead(Base):
    """One read of a trial's stored registry record by a model (openspec
    record-readings): what the model was shown, by its hash, under which instructions,
    which model it was, and what the rules refused.

    One per trial. A trial is read again only when the hash or the instructions'
    version changes, and the new read replaces this one and its readings.
    """

    __tablename__ = "trial_read"
    __table_args__ = (UniqueConstraint("source_name", "trial_id", name="uq_trial_read_trial"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_name: Mapped[str] = mapped_column(Text)
    # The registry's identifier of the trial.
    trial_id: Mapped[str] = mapped_column(Text)
    # Of the fields shown to the model: the titles and time frames of the planned
    # primary outcomes, as the trial's facts carry them.
    input_hash: Mapped[str] = mapped_column(Text)
    instructions_version: Mapped[str] = mapped_column(Text)
    # As named by the environment.
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    # Readings the rules refused: the outcome, the kind and the reason. Never the
    # words the model gave.
    refusals: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    # When the model read the record.
    read_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class Reading(Base):
    """A record reading (openspec record-readings): a code, or a number
    with a unit, that a model read from one field of a planned primary outcome, with
    the exact words read. Stored only once the rules have checked it against the record.
    Never a sentence, and never an input to a status, a match score or a trial's facts.
    """

    __tablename__ = "reading"
    __table_args__ = (
        UniqueConstraint("trial_read_id", "outcome", "kind", name="uq_reading_outcome_kind"),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("outcome >= 0", name="outcome_index"),
        CheckConstraint("char_length(words) > 0", name="words_present"),
        CheckConstraint(
            "(kind = 'follow_up') = (number IS NOT NULL)"
            " AND (kind = 'follow_up') = (unit IS NOT NULL)"
            " AND (kind = 'measure') = (code IS NOT NULL)",
            name="value_fits_kind",
        ),
        CheckConstraint("(kind = 'follow_up') = (field = 'time_frame')", name="field_fits_kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    trial_read_id: Mapped[int] = mapped_column(
        ForeignKey("trial_read.id", ondelete="CASCADE"), index=True
    )
    # The place of the outcome among the planned primary outcomes of the trial's
    # facts, counted from 0.
    outcome: Mapped[int]
    kind: Mapped[ReadingKind] = mapped_column(_enum(ReadingKind, "kind"))
    field: Mapped[ReadingField] = mapped_column(_enum(ReadingField, "field"))
    # The words read, character for character as the field has them.
    words: Mapped[str] = mapped_column(Text)
    number: Mapped[int | None]
    unit: Mapped[FollowUpUnit | None] = mapped_column(_enum(FollowUpUnit, "unit"))
    code: Mapped[MeasureCode | None] = mapped_column(_enum(MeasureCode, "code"))
    # How sure the model said it was of the reading.
    confidence: Mapped[float]
    decided_by: Mapped[ReadBy] = mapped_column(_enum(ReadBy, "decided_by"))
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP, server_default=func.now())


class DecisionLog(Base):
    __tablename__ = "decision_log"
    # A decision is looked up by its step and what it was about; a step alone uses the
    # same index.
    __table_args__ = (Index("ix_decision_log_step_input_ref", "step", "input_ref"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    step: Mapped[str] = mapped_column(Text)
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
    __table_args__ = (
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0 AND cost_usd >= 0",
            name="amounts_not_negative",
        ),
    )

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


class RegistrySearch(Base):
    """One term of a claim's latest finished registry search: what was sent, when, and
    what came back, or why the term was not sent. The rows of a claim's search replace
    those of the search before. A claim with none was never searched. Behavior: openspec
    entity-resolution, "A registry search leaves a record"."""

    __tablename__ = "registry_search"
    __table_args__ = (
        # A term sent says what came back; a term not sent says why, and nothing else.
        CheckConstraint(
            "(not_sent_reason IS NULL) = (reported IS NOT NULL)"
            " AND (reported IS NULL) = (kept IS NULL)",
            name="sent_or_why_not",
        ),
        CheckConstraint("reported >= 0 AND kept >= 0", name="counts_not_negative"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), index=True)
    source_name: Mapped[str] = mapped_column(Text)
    term: Mapped[str] = mapped_column(Text)
    # The wording of the condition the search was narrowed by, if it was.
    condition: Mapped[str | None] = mapped_column(Text)
    ran_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    # How many records the source said it holds for the search, and how many were taken.
    reported: Mapped[int | None]
    kept: Mapped[int | None]
    # A limit left some of the reported records out.
    cut: Mapped[bool] = mapped_column(default=False, server_default="false")
    not_sent_reason: Mapped[str | None] = mapped_column(Text)


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
        CheckConstraint("attempts >= 0 AND requests_used >= 0", name="counts_not_negative"),
        # A record put off says until when, and one that waits says for what.
        CheckConstraint("(outcome = 'later') = (not_before IS NOT NULL)", name="later_has_time"),
        CheckConstraint(
            "outcome NOT IN ('later', 'needs_fix') OR reason IS NOT NULL",
            name="waiting_has_reason",
        ),
        # The unique index leads with the record, so a step's entries need their own.
        Index("ix_work_entry_step_step_version", "step", "step_version"),
        # What `thenwhat work requeue` and the plan look entries up by.
        Index(
            "ix_work_entry_step_reason",
            "step",
            "step_version",
            "reason",
            postgresql_where=text("reason IS NOT NULL"),
        ),
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
    # Why the record was not done, as a code the step declared, with the values the
    # reason carries: the status a site answered, an outlet.
    reason: Mapped[str | None] = mapped_column(Text)
    reason_values: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    # A record put off is not due before this time.
    not_before: Mapped[datetime | None] = mapped_column(TIMESTAMP)
    # When the record was first put off for the reason it is put off for now. One put
    # off for the same reason past the configured span is said to need a fix.
    first_put_off_at: Mapped[datetime | None] = mapped_column(TIMESTAMP)


class SourceAllowanceUse(Base):
    """How much of a source's allowance is used in the current period, for every process
    that asks that source. Behavior: openspec source-allowances."""

    __tablename__ = "source_allowance_use"
    __table_args__ = (
        CheckConstraint("requests_used >= 0 AND refusals >= 0", name="counts_not_negative"),
    )

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
        # What the named sets of stored trials select on (backfill/trial_sets.py).
        Index("ix_registry_trial_overall_status", "overall_status"),
        Index(
            "ix_registry_trial_completion_with_results",
            "completion_date",
            postgresql_where=text("has_results AND completion_date_type = 'ACTUAL'"),
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
    # What the registry states of the trial's activity and results, as it gives them.
    # Empty where the registry gives nothing, and on trials loaded before these were
    # asked for; never inferred. A completion date can be a month without a day, and its
    # type says whether it is ACTUAL or anticipated (ESTIMATED).
    start_date_type: Mapped[str | None] = mapped_column(Text)
    last_update_posted: Mapped[date | None] = mapped_column(index=True)
    study_first_posted: Mapped[date | None]
    primary_completion_date: Mapped[str | None] = mapped_column(Text)
    primary_completion_date_type: Mapped[str | None] = mapped_column(Text)
    completion_date: Mapped[str | None] = mapped_column(Text)
    completion_date_type: Mapped[str | None] = mapped_column(Text)
    results_first_posted: Mapped[date | None]
    has_results: Mapped[bool | None]
    acronym: Mapped[str | None] = mapped_column(Text)
    # Empty when the lead sponsor is an individual: a person's name is not kept here.
    lead_sponsor_name: Mapped[str | None] = mapped_column(Text)
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    fetched_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class TrialPaper(Base):
    """A paper a paper index returned for a stored trial's registry number, with the
    paper's own record as kept: no abstract and no author. Attached by the number the
    record carries, with no score. Not a match, not an evidence event, and never a
    results paper unless the registry record names it as one.
    Behavior: openspec trial-coverage, "Papers that carry the trial's number"."""

    __tablename__ = "trial_paper"
    __table_args__ = (
        UniqueConstraint(
            "registry_trial_id",
            "source_name",
            "pubmed_id",
            name="uq_trial_paper_trial_source_paper",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    registry_trial_id: Mapped[int] = mapped_column(ForeignKey("registry_trial.id"), index=True)
    source_name: Mapped[str] = mapped_column(Text)
    pubmed_id: Mapped[str] = mapped_column(Text, index=True)
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


class LinkLead(Base):
    """The address of an article that people shared on a social platform, kept once per
    address. Unreviewed, never a source article or an article lead, and never exported.
    Who shared it is never stored. Behavior: openspec link-leads."""

    __tablename__ = "link_lead"
    __table_args__ = (
        # A lead found already tracked points at its claim with no article, so a claim
        # may stand alone; an article may not.
        CheckConstraint(
            "source_article_id IS NULL OR claim_id IS NOT NULL", name="article_has_claim"
        ),
        CheckConstraint(
            "read_outcome IS NULL OR read_outcome NOT IN ('added_to_claim', 'new_claim')"
            " OR claim_id IS NOT NULL",
            name="made_outcome_has_claim",
        ),
        # Few leads have been read, and the funnel counts them by how the read ended.
        Index(
            "ix_link_lead_read_outcome",
            "read_outcome",
            postgresql_where=text("read_outcome IS NOT NULL"),
        ),
        _article_of_claim("fk_link_lead_article_of_claim"),
        Index(
            "ix_link_lead_source_article_id",
            "source_article_id",
            postgresql_where=text("source_article_id IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    # The address in the form the site compares addresses in: one lead per key.
    url_key: Mapped[str] = mapped_column(Text, unique=True)
    # Which form of the key that is (`address.KEY_VERSION`). Leads keyed under an
    # earlier form are brought up to date by `thenwhat backfill rekey-links`.
    url_key_version: Mapped[int] = mapped_column(server_default=text("1"))
    outlet: Mapped[str] = mapped_column(Text, index=True)
    outlet_kind: Mapped[OutletKind] = mapped_column(_enum(OutletKind, "outlet_kind"))
    # The title the article was first shared under. Private: the operator labels from
    # it and triage scores it. Never exported.
    title: Mapped[str] = mapped_column(Text)
    first_shared_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    # Set by screening (openspec lead-screening).
    screen_outcome: Mapped[ScreenOutcome | None] = mapped_column(
        _enum(ScreenOutcome, "screen_outcome")
    )
    # Set by triage (openspec lead-triage): the probability that the headline reports a
    # specific treatment for a specific condition, and the step version that gave it.
    # Indexed: reading picks its next lead by score, and without the index every pick
    # matched the topic words against every in-scope title.
    triage_score: Mapped[float | None] = mapped_column(index=True)
    triage_version: Mapped[int | None]
    # Set by reading (openspec lead-reading).
    read_outcome: Mapped[ReadOutcome | None] = mapped_column(_enum(ReadOutcome, "read_outcome"))
    read_detail: Mapped[str | None] = mapped_column(Text)
    claim_id: Mapped[int | None] = mapped_column(ForeignKey("claim.id"), index=True)
    source_article_id: Mapped[int | None] = mapped_column(ForeignKey("source_article.id"))


class LinkShare(Base):
    """One time a link lead's article was shared: where, when and with what score."""

    __tablename__ = "link_share"
    __table_args__ = (
        UniqueConstraint(
            "link_lead_id",
            "platform",
            "community",
            "shared_at",
            name="uq_link_share_lead_place_time",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    link_lead_id: Mapped[int] = mapped_column(ForeignKey("link_lead.id"), index=True)
    platform: Mapped[str] = mapped_column(Text)
    # The community within the platform; the platform's own name where it has none.
    community: Mapped[str] = mapped_column(Text)
    shared_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    score: Mapped[int]
    # The Hacker News item number. Empty for Reddit: a post's id is never kept.
    item_number: Mapped[int | None]


class LinkLeadLink(Base):
    """A stored record that screening found for a link lead, with the reason. The record
    is named by kind and id, as the ledger names one. A candidate: it approves nothing."""

    __tablename__ = "link_lead_link"
    __table_args__ = (
        UniqueConstraint(
            "link_lead_id",
            "record_kind",
            "record_id",
            "reason",
            name="uq_link_lead_link_lead_record_reason",
        ),
        CheckConstraint(
            "strength IS NULL OR strength IN ('exact', 'strong', 'named', 'candidate')",
            name="strength_is_known",
        ),
        # Reading asks which leads have an exact or strong link to a trial of a set.
        Index(
            "ix_link_lead_link_strong",
            "record_id",
            "link_lead_id",
            postgresql_where=text("strength IN ('exact', 'strong')"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    link_lead_id: Mapped[int] = mapped_column(ForeignKey("link_lead.id"), index=True)
    record_kind: Mapped[str] = mapped_column(Text)
    record_id: Mapped[int]
    reason: Mapped[str] = mapped_column(Text)
    # For a link to a registry trial: how much it says (exact, strong, named or
    # candidate; backfill/link_screen.py), the term of the trial the title holds, and
    # the word of the trial's condition found beside it. Empty on a link to a claim and
    # on links made before screening version 3.
    strength: Mapped[str | None] = mapped_column(Text)
    term: Mapped[str | None] = mapped_column(Text)
    beside: Mapped[str | None] = mapped_column(Text)


class LinkLeadLabel(Base):
    """What a person, or an assistant, says a link lead's headline is. It belongs to the
    lead, so it holds for every version of triage. Behavior: openspec lead-evaluation."""

    __tablename__ = "link_lead_label"
    __table_args__ = (
        UniqueConstraint("link_lead_id", "labelled_by", name="uq_link_lead_label_lead_by"),
        CheckConstraint("labelled_by IN ('human', 'assistant')", name="labelled_by_a_reader"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    link_lead_id: Mapped[int] = mapped_column(ForeignKey("link_lead.id"), index=True)
    label: Mapped[LeadVerdict] = mapped_column(_enum(LeadVerdict, "label"))
    labelled_by: Mapped[Decider] = mapped_column(_enum(Decider, "labelled_by"))
    labelled_at: Mapped[datetime] = mapped_column(TIMESTAMP)


class MeasureDaily(Base):
    """A day's measurements added up for one step, version, writer and outcome. These
    totals are kept for good; the single measurements they came from are not.
    Behavior: openspec processing-metrics."""

    __tablename__ = "measure_daily"
    __table_args__ = (
        UniqueConstraint(
            "day", "step", "step_version", "writer", "outcome", name="uq_measure_daily_key"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    day: Mapped[date] = mapped_column(index=True)
    step: Mapped[str] = mapped_column(Text)
    step_version: Mapped[int]
    writer: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text)
    # How many measurements, and how many records they covered between them.
    spans: Mapped[int]
    records: Mapped[int]
    reused: Mapped[int]
    ran_seconds: Mapped[float]
    waited_seconds: Mapped[float]
    # Seconds waited by what was waited on, and requests sent by source.
    waited_by_cause: Mapped[dict[str, Any]] = mapped_column(JSONB)
    requests_by_source: Mapped[dict[str, Any]] = mapped_column(JSONB)
    tokens_in: Mapped[int]
    tokens_out: Mapped[int]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    # What the measurements made inside these cost: counted in their own totals, kept
    # here so that the whole cost of a step for a record can be told.
    inner_cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6))
    rows_written: Mapped[int]


class MeasureClaim(Base):
    """What a claim took, added up from the measurements of its articles and of the
    work done on the claim itself. Behavior: openspec processing-metrics."""

    __tablename__ = "measure_claim"

    id: Mapped[int] = mapped_column(primary_key=True)
    claim_id: Mapped[int] = mapped_column(ForeignKey("claim.id"), unique=True)
    # When the first measured step on any of its articles, or on it, began.
    first_seen_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    last_step_at: Mapped[datetime] = mapped_column(TIMESTAMP)
    spans: Mapped[int]
    ran_seconds: Mapped[float]
    waited_seconds: Mapped[float]
    cost_usd: Mapped[Decimal] = mapped_column(Numeric(12, 6))


class MeasureRolledDay(Base):
    """A day whose measurements have been added into the totals, so that adding them
    again changes nothing. Behavior: openspec processing-metrics."""

    __tablename__ = "measure_rolled_day"

    day: Mapped[date] = mapped_column(primary_key=True)
    rolled_at: Mapped[datetime] = mapped_column(TIMESTAMP)
