"""The JSON export the site is built from. Behavior: openspec site-publishing.

Only approved, unarchived claims are exported, with their approved events, their
approved matches and a few candidates still awaiting review. The file is the single
interface between pipeline and site; its schema is checked in at site/export.schema.json.
"""

import base64
import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import articles_of, promises_of
from thenwhat.claims.status import refresh_status, status_history
from thenwhat.claims.verticals import GROUPS, RETIRED_VERTICALS, VERTICAL_GROUPS, VERTICALS
from thenwhat.db.models import (
    Claim,
    DecisionLog,
    Entity,
    EntityMatch,
    EvidenceEvent,
    FailureFlag,
    OutletIcon,
)
from thenwhat.decide.steps import ENTITY_MATCH
from thenwhat.domain import (
    TRIAL_EVENT_TYPES,
    ClaimStatus,
    Decider,
    EntityType,
    EventType,
    EvidenceStage,
    RegulatoryOutcome,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.outlets.icons import is_blank_icon, outlet_domain
from thenwhat.sources.base import RECORD_URLS

SCHEMA_VERSION = 1
# Registries the clients read. Always listed, as their terms ask for attribution.
SOURCES = [
    ("ClinicalTrials.gov", "https://clinicaltrials.gov/"),
    ("Europe PMC", "https://europepmc.org/"),
    ("Crossref", "https://www.crossref.org/"),
]
# Registries with no client yet, listed only when an exported event came from one.
OTHER_REGISTRIES = {"jRCT": "https://jrct.mhlw.go.jp/"}


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExportedSource(Strict):
    name: str
    url: str


class ExportedGroup(Strict):
    slug: str
    title: str


class ExportedVertical(Strict):
    slug: str
    title: str
    # The broader area the vertical is filed under, when it has one.
    group: ExportedGroup | None = None


class ExportedRetiredVertical(Strict):
    """A vertical slug renamed or retired after launch, and the vertical that replaces it."""

    slug: str
    successor: str


class ExportedOutlet(Strict):
    """An outlet's own icon, stored by the pipeline so that no page fetches it."""

    # An article's host without a leading www, as the site shows it.
    domain: str
    # The image itself as a data URI; the site never receives an address to fetch.
    icon: str = Field(pattern=r"^data:image/(png|x-icon|gif|jpeg|webp);base64,[A-Za-z0-9+/]+=*$")
    fetched_at: datetime


class ExportedIntervention(Strict):
    name: str
    synonyms: list[str]


class ExportedStatusChange(Strict):
    """The day the status became `code`, by the rules run on what was dated up to then."""

    on: date
    code: ClaimStatus


class ExportedStatus(Strict):
    code: ClaimStatus
    overlay_years: int | None
    updated_at: datetime | None
    explained_by: list[int]
    # Oldest first; the last entry's code is `code`. Absent from exports made before
    # the history was added, so the site treats a missing history as none.
    history: list[ExportedStatusChange] = []


class ExportedArticle(Strict):
    url: str
    outlet: str
    title: str
    published_date: date
    archive_url: str | None


class ExportedPromise(Strict):
    description: str
    parsed_date: date | None
    article_url: str


class ExportedEvent(Strict):
    id: int
    type: EventType
    event_date: date
    date_basis: str | None
    summary: str
    source_name: str
    source_url: str
    trial_id: str | None
    trial_phases: list[TrialPhase]
    trial_state: TrialState | None
    regulatory_outcome: RegulatoryOutcome | None


class ExportedFailureFlag(Strict):
    trial_id: str
    source_url: str


class ExportedMatch(Strict):
    # A registry record matched to the claim, with how sure the pipeline is. The site owns
    # the words: it turns `score` into "High match · 92%" and `reading` into a reason.
    source_name: str
    external_id: str
    url: str | None
    # The probability, 0 to 1, that the record is evidence for the claim.
    score: float
    # "approved" counts toward the status; "candidate" is shown apart and does not.
    state: str
    # How the record was read: "match", "other_indication", "not_a_match", or None.
    reading: str | None
    # Who approved it: "human", "rule", "seed" or "assistant". None for a candidate.
    decided_by: str | None
    # What the record says, in one line: title, conditions, phase, state.
    summary: str | None


class ExportedClaim(Strict):
    slug: str
    headline: str
    summary: str
    vertical: str
    # The kind of intervention, as a configured approach code. The site owns its wording.
    approach: str | None
    intervention: ExportedIntervention
    indication: str
    first_reported_date: date | None
    evidence_stage: EvidenceStage | None
    # True only when a person approved the claim and no assistant decision stands on
    # it, its matches or its events.
    checked_by_person: bool
    status: ExportedStatus
    articles: list[ExportedArticle]
    promises: list[ExportedPromise]
    events: list[ExportedEvent]
    failure_flags: list[ExportedFailureFlag]
    # Approved matches first, then up to five candidates, each with its confidence.
    matches: list[ExportedMatch] = []


class ExportedArchived(Strict):
    # A claim the operator took down. Its address answers 410; the reason stays private.
    slug: str
    on: date


class Export(Strict):
    schema_version: int
    generated_at: datetime
    last_checked_at: datetime | None
    # Always false since openspec auto-publish: every approved claim is published, and
    # `checked_by_person` on each claim says whether a person checked it. Kept so a site
    # built from an older export still reads it.
    preview: bool = False
    sources: list[ExportedSource]
    verticals: list[ExportedVertical]
    # Topic addresses that must keep working: each redirects to its successor's.
    retired_verticals: list[ExportedRetiredVertical] = []
    # Icons of the outlets whose articles are exported. An outlet without one is absent.
    outlets: list[ExportedOutlet]
    claims: list[ExportedClaim]
    archived: list[ExportedArchived] = []


def _group_of(vertical: str) -> ExportedGroup | None:
    slug = VERTICAL_GROUPS.get(vertical)
    return None if slug is None else ExportedGroup(slug=slug, title=GROUPS[slug])


def export_json_schema() -> dict[str, Any]:
    return Export.model_json_schema(mode="serialization")


def _decided_by_assistant(session: Session, claim: Claim) -> bool:
    """Whether the assistant made any decision that still stands on the claim, its
    matches or its events."""
    if claim.reviewed_by is Decider.ASSISTANT:
        return True
    match_ids = select(EntityMatch.id).join(Entity).where(Entity.claim_id == claim.id)
    return bool(
        session.scalar(
            select(EntityMatch.id).where(
                EntityMatch.id.in_(match_ids), EntityMatch.reviewed_by == Decider.ASSISTANT
            )
        )
        or session.scalar(
            select(EvidenceEvent.id).where(
                EvidenceEvent.claim_id == claim.id,
                EvidenceEvent.reviewed_by == Decider.ASSISTANT,
            )
        )
    )


CANDIDATES_SHOWN = 5


def _reading(session: Session, match: EntityMatch) -> str | None:
    scored = session.scalars(
        select(DecisionLog)
        .where(
            DecisionLog.step == ENTITY_MATCH,
            DecisionLog.input_ref == f"entity_match:{match.id}",
            DecisionLog.error.is_(None),
        )
        .order_by(DecisionLog.id.desc())
    ).first()
    if scored is None or scored.output is None:
        return None
    choice = scored.output.get("choice")
    return choice if isinstance(choice, str) else None


def _matches(session: Session, claim: Claim) -> list[ExportedMatch]:
    """The claim's approved matches, then its best pending candidates. Rejected ones are
    never exported. Openspec auto-publish: "Confidence is shown with every match"."""
    found = list(
        session.scalars(
            select(EntityMatch)
            .join(Entity)
            .where(
                Entity.claim_id == claim.id,
                EntityMatch.review_state.in_([ReviewState.APPROVED, ReviewState.PENDING]),
            )
            .order_by(EntityMatch.score.desc(), EntityMatch.id)
        )
    )
    approved = [m for m in found if m.review_state is ReviewState.APPROVED]
    pending = [m for m in found if m.review_state is ReviewState.PENDING][:CANDIDATES_SHOWN]
    return [
        ExportedMatch(
            source_name=match.source_name,
            external_id=match.external_id,
            url=(
                RECORD_URLS[match.source_name].format(match.external_id)
                if match.source_name in RECORD_URLS
                else None
            ),
            score=round(match.score, 4),
            state="approved" if match.review_state is ReviewState.APPROVED else "candidate",
            reading=_reading(session, match),
            decided_by=(
                match.reviewed_by.value
                if match.review_state is ReviewState.APPROVED and match.reviewed_by
                else None
            ),
            summary=match.record_summary,
        )
        for match in [*approved, *pending]
    ]


def _outlets(session: Session, claims: list[ExportedClaim]) -> list[ExportedOutlet]:
    domains = {outlet_domain(article.url) for claim in claims for article in claim.articles}
    return [
        ExportedOutlet(
            domain=icon.domain,
            icon=f"data:{icon.media_type};base64,{base64.b64encode(icon.content).decode()}",
            fetched_at=icon.fetched_at,
        )
        for icon in session.scalars(
            select(OutletIcon).where(OutletIcon.domain.in_(domains)).order_by(OutletIcon.domain)
        )
        if icon.content is not None and not is_blank_icon(icon.content)
    ]


def build_export(session: Session, *, now: datetime, no_signal_years: int = 3) -> Export:
    """Everything the site may show, as of now.

    Each claim's status is derived again first, because the no-signal overlay depends
    on today's date. A claim exported for the first time gets its published time.

    Every approved, unarchived claim is included, whoever decided it; a claim the
    assistant decided says it was not checked by a person.
    """
    claims: list[ExportedClaim] = []
    last_checked: datetime | None = None
    for claim in session.scalars(
        select(Claim)
        .where(Claim.review_state == ReviewState.APPROVED, Claim.archived_at.is_(None))
        .order_by(Claim.slug)
    ):
        # Every approved claim is published, whoever decided it (openspec auto-publish).
        # Whether a person checked it is still said, in `checked_by_person`.
        assistant = _decided_by_assistant(session, claim)
        derivation = refresh_status(
            session, claim, as_of=now.date(), now=now, no_signal_years=no_signal_years
        )
        if claim.published_at is None:
            claim.published_at = now
        events = list(
            session.scalars(
                select(EvidenceEvent)
                .where(
                    EvidenceEvent.claim_id == claim.id,
                    EvidenceEvent.review_state == ReviewState.APPROVED,
                )
                .order_by(EvidenceEvent.event_date, EvidenceEvent.id)
            )
        )
        for event in events:
            if last_checked is None or event.fetched_at > last_checked:
                last_checked = event.fetched_at
        articles = articles_of(session, claim)
        article_urls = {article.id: article.url for article in articles}
        intervention = session.scalars(
            select(Entity).where(
                Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION
            )
        ).first()
        assert intervention is not None, "every claim is created with its intervention entity"
        claims.append(
            ExportedClaim(
                slug=claim.slug,
                headline=claim.headline,
                summary=claim.summary,
                vertical=claim.vertical,
                approach=claim.approach,
                intervention=ExportedIntervention(
                    name=intervention.name, synonyms=list(intervention.synonyms)
                ),
                indication=claim.indication,
                first_reported_date=claim.first_reported_date,
                evidence_stage=claim.evidence_stage,
                checked_by_person=claim.reviewed_by is Decider.HUMAN and not assistant,
                status=ExportedStatus(
                    code=derivation.status,
                    overlay_years=derivation.overlay_years,
                    updated_at=claim.status_updated_at,
                    explained_by=list(derivation.explaining_event_ids),
                    history=[
                        ExportedStatusChange(on=change.on, code=change.status)
                        for change in status_history(session, claim)
                    ],
                ),
                articles=[
                    ExportedArticle(
                        url=article.url,
                        outlet=article.outlet,
                        title=article.title,
                        published_date=article.published_date,
                        archive_url=article.archive_url,
                    )
                    for article in articles
                ],
                promises=[
                    ExportedPromise(
                        description=promise.description,
                        parsed_date=promise.parsed_date,
                        article_url=article_urls[promise.source_article_id],
                    )
                    for promise in promises_of(session, claim)
                ],
                events=[
                    ExportedEvent(
                        id=event.id,
                        type=event.type,
                        event_date=event.event_date,
                        date_basis=event.date_basis,
                        summary=event.summary,
                        source_name=event.source_name,
                        source_url=event.source_url,
                        trial_id=event.external_id if event.type in TRIAL_EVENT_TYPES else None,
                        trial_phases=[TrialPhase(phase) for phase in event.trial_phases or []],
                        trial_state=event.trial_state,
                        regulatory_outcome=event.regulatory_outcome,
                    )
                    for event in events
                ],
                matches=_matches(session, claim),
                failure_flags=[
                    ExportedFailureFlag(trial_id=flag.trial_external_id, source_url=flag.source_url)
                    for flag in session.scalars(
                        select(FailureFlag)
                        .where(FailureFlag.claim_id == claim.id)
                        .order_by(FailureFlag.id)
                    )
                ],
            )
        )
    session.flush()
    return Export(
        schema_version=SCHEMA_VERSION,
        generated_at=now,
        last_checked_at=last_checked,
        sources=[
            ExportedSource(name=name, url=url)
            for name, url in [
                *SOURCES,
                *(
                    (name, url)
                    for name, url in OTHER_REGISTRIES.items()
                    if any(event.source_name == name for claim in claims for event in claim.events)
                ),
            ]
        ],
        verticals=[
            ExportedVertical(slug=slug, title=title, group=_group_of(slug))
            for slug, title in VERTICALS.items()
        ],
        retired_verticals=[
            ExportedRetiredVertical(slug=slug, successor=successor)
            for slug, successor in RETIRED_VERTICALS.items()
        ],
        outlets=_outlets(session, claims),
        claims=claims,
        archived=[
            ExportedArchived(slug=claim.slug, on=claim.archived_at.date())
            for claim in session.scalars(
                select(Claim)
                .where(Claim.archived_at.is_not(None), Claim.published_at.is_not(None))
                .order_by(Claim.slug)
            )
            if claim.archived_at is not None
        ],
    )


def write_export(
    session: Session,
    path: Path,
    *,
    now: datetime,
    no_signal_years: int = 3,
) -> Export:
    """Write the export to `path`, replacing any earlier file only once it is complete."""
    export = build_export(session, now=now, no_signal_years=no_signal_years)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_suffix(path.suffix + ".partial")
    partial.write_text(export.model_dump_json(indent=2) + "\n")
    partial.replace(path)
    return export


def write_schema(path: Path) -> None:
    path.write_text(json.dumps(export_json_schema(), indent=2) + "\n")
