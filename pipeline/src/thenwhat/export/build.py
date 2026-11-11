"""The JSON export the site is built from. Behavior: openspec site-publishing.

Only approved claims and their approved events are exported. The file is the single
interface between pipeline and site; its schema is checked in at site/export.schema.json.
"""

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import articles_of, promises_of
from thenwhat.claims.status import refresh_status
from thenwhat.claims.verticals import VERTICALS
from thenwhat.db.models import Claim, Entity, EvidenceEvent, FailureFlag
from thenwhat.domain import (
    ClaimStatus,
    EntityType,
    EventType,
    EvidenceStage,
    RegulatoryOutcome,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.events.manual import TRIAL_TYPES

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


class ExportedVertical(Strict):
    slug: str
    title: str


class ExportedIntervention(Strict):
    name: str
    synonyms: list[str]


class ExportedStatus(Strict):
    code: ClaimStatus
    overlay_years: int | None
    updated_at: datetime | None
    explained_by: list[int]


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


class ExportedClaim(Strict):
    slug: str
    headline: str
    summary: str
    vertical: str
    intervention: ExportedIntervention
    indication: str
    first_reported_date: date | None
    evidence_stage: EvidenceStage | None
    status: ExportedStatus
    articles: list[ExportedArticle]
    promises: list[ExportedPromise]
    events: list[ExportedEvent]
    failure_flags: list[ExportedFailureFlag]


class Export(Strict):
    schema_version: int
    generated_at: datetime
    last_checked_at: datetime | None
    sources: list[ExportedSource]
    verticals: list[ExportedVertical]
    claims: list[ExportedClaim]


def export_json_schema() -> dict[str, Any]:
    return Export.model_json_schema(mode="serialization")


def build_export(session: Session, *, now: datetime, no_signal_years: int = 3) -> Export:
    """Everything the site may show, as of now.

    Each claim's status is derived again first, because the no-signal overlay depends
    on today's date. A claim exported for the first time gets its published time.
    """
    claims: list[ExportedClaim] = []
    last_checked: datetime | None = None
    for claim in session.scalars(
        select(Claim).where(Claim.review_state == ReviewState.APPROVED).order_by(Claim.slug)
    ):
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
                intervention=ExportedIntervention(
                    name=intervention.name, synonyms=list(intervention.synonyms)
                ),
                indication=claim.indication,
                first_reported_date=claim.first_reported_date,
                evidence_stage=claim.evidence_stage,
                status=ExportedStatus(
                    code=derivation.status,
                    overlay_years=derivation.overlay_years,
                    updated_at=claim.status_updated_at,
                    explained_by=list(derivation.explaining_event_ids),
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
                        trial_id=event.external_id if event.type in TRIAL_TYPES else None,
                        trial_phases=[TrialPhase(phase) for phase in event.trial_phases or []],
                        trial_state=event.trial_state,
                        regulatory_outcome=event.regulatory_outcome,
                    )
                    for event in events
                ],
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
        verticals=[ExportedVertical(slug=slug, title=title) for slug, title in VERTICALS.items()],
        claims=claims,
    )


def write_export(
    session: Session, path: Path, *, now: datetime, no_signal_years: int = 3
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
