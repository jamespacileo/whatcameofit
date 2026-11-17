"""The trial listing: one compact file of a named set of stored trials, holding only
what the site's search and its trial page need to find a trial. Registry facts as codes
and the registry's own text; nothing about how any trial turned out. The site words it.

Each trial is a row in the order of `COLUMNS`, not an object: the keys of 23,000 objects
would be a quarter of the file. Behavior: openspec trial-pages, "A trial listing built
into the site"."""

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.trial_sets import SETS
from thenwhat.db.models import Claim, Entity, EntityMatch, EvidenceEvent, RegistryTrial
from thenwhat.domain import ReviewState
from thenwhat.events.trial import PHASES
from thenwhat.events.trial_facts import STATES

LISTING_VERSION = 1
# The one registry whose identifiers the site's trial page reads on request.
REGISTRY = "clinicaltrials.gov"
REGISTRY_ID = r"^NCT\d{8}$"
COLUMNS = (
    "id",
    "title",
    "acronym",
    "phases",
    "state",
    "updated",
    "conditions",
    "interventions",
    "claim",
)

Phase = Literal["early_phase_1", "phase_1", "phase_2", "phase_3", "phase_4", "not_applicable"]
State = Literal[
    "not_started", "under_way", "completed", "suspended", "terminated", "withdrawn", "unknown"
]
# id, title, acronym, phases, state, the day the registry last changed the record,
# conditions, intervention names, and the slug of a published claim that cites it.
Row = tuple[str, str, str | None, list[Phase], State, date | None, list[str], list[str], str | None]


class TrialsListing(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = LISTING_VERSION
    # The named set of stored trials the listing holds, and no trial outside it.
    set: str
    registry: Literal["clinicaltrials.gov"] = REGISTRY
    # The latest day any listed record was read from the registry; empty for no trials.
    records_read: date | None
    columns: tuple[
        Literal["id"],
        Literal["title"],
        Literal["acronym"],
        Literal["phases"],
        Literal["state"],
        Literal["updated"],
        Literal["conditions"],
        Literal["interventions"],
        Literal["claim"],
    ] = COLUMNS
    trials: list[Row] = Field(default_factory=list)


class UnknownSet(ValueError):
    pass


def listing_json_schema() -> dict[str, Any]:
    return TrialsListing.model_json_schema(mode="serialization")


def _cited(session: Session) -> dict[str, str]:
    """For each trial a published claim cites, that claim's slug: the first by slug when
    several cite it. A claim cites a trial through an approved event or an approved
    match, as the site's own index of cited trials counts it; a candidate match counts
    for nothing. Published is what the export publishes: approved, unarchived and not
    awaiting audit."""
    published = (
        Claim.review_state == ReviewState.APPROVED,
        Claim.archived_at.is_(None),
        Claim.awaiting_audit_at.is_(None),
    )
    by_event = (
        select(EvidenceEvent.external_id, Claim.slug)
        .join(Claim, Claim.id == EvidenceEvent.claim_id)
        .where(
            EvidenceEvent.review_state == ReviewState.APPROVED,
            EvidenceEvent.external_id.regexp_match(REGISTRY_ID),
            *published,
        )
    )
    by_match = (
        select(EntityMatch.external_id, Claim.slug)
        .join(Entity, Entity.id == EntityMatch.entity_id)
        .join(Claim, Claim.id == Entity.claim_id)
        .where(
            EntityMatch.review_state == ReviewState.APPROVED,
            EntityMatch.source_name == REGISTRY,
            EntityMatch.external_id.regexp_match(REGISTRY_ID),
            *published,
        )
    )
    cited: dict[str, str] = {}
    for query in (by_event, by_match):
        for external_id, slug in session.execute(query):
            if external_id not in cited or slug < cited[external_id]:
                cited[external_id] = slug
    return cited


def build_listing(session: Session, set_name: str) -> TrialsListing:
    rule = SETS.get(set_name)
    if rule is None:
        raise UnknownSet(f'No set of trials is named "{set_name}". The sets: {", ".join(SETS)}.')
    cited = _cited(session)
    rows: list[Row] = []
    read: date | None = None
    for trial in session.execute(
        select(
            RegistryTrial.external_id,
            RegistryTrial.title,
            RegistryTrial.acronym,
            RegistryTrial.phases,
            RegistryTrial.overall_status,
            RegistryTrial.last_update_posted,
            RegistryTrial.conditions,
            RegistryTrial.interventions,
            RegistryTrial.fetched_at,
        )
        .where(
            rule(),
            RegistryTrial.registry_name == REGISTRY,
            RegistryTrial.external_id.regexp_match(REGISTRY_ID),
        )
        .order_by(RegistryTrial.external_id)
    ):
        names: list[str] = []
        for intervention in trial.interventions or []:
            name = intervention.get("name") if isinstance(intervention, dict) else None
            if isinstance(name, str) and name.strip() and name.strip() not in names:
                names.append(name.strip())
        rows.append(
            (
                trial.external_id,
                trial.title,
                trial.acronym or None,
                [PHASES[phase].value for phase in trial.phases or [] if phase in PHASES],
                STATES.get(trial.overall_status or "", "unknown"),
                trial.last_update_posted,
                list(trial.conditions or []),
                names,
                cited.get(trial.external_id),
            )
        )
        day = trial.fetched_at.date()
        if read is None or day > read:
            read = day
    return TrialsListing(set=set_name, records_read=read, trials=rows)


def write_listing(session: Session, path: Path, set_name: str) -> TrialsListing:
    """Write the listing to `path`, replacing any earlier file only once it is complete.
    One line with no spaces: the file is fetched by readers."""
    listing = build_listing(session, set_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    temporary.write_text(listing.model_dump_json() + "\n")
    temporary.replace(path)
    return listing


def write_listing_schema(path: Path) -> None:
    path.write_text(json.dumps(listing_json_schema(), indent=2) + "\n")
