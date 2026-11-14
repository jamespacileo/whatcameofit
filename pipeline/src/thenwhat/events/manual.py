"""Evidence events entered by hand. Behavior: openspec evidence-events.

For approvals, company events and trials in registries that have no client yet.
A hand-entered event always waits for review.
"""

from collections.abc import Sequence
from datetime import date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import (
    EntryError,
    InvalidField,
    InvalidUrl,
    MissingField,
    claim_by_slug,
    tidy,
)
from thenwhat.db.models import EvidenceEvent
from thenwhat.domain import (
    TRIAL_EVENT_TYPES,
    EventType,
    RegulatoryOutcome,
    TrialPhase,
    TrialState,
)
from thenwhat.events.draft import EventDraft
from thenwhat.events.fetch import event_row

MANUAL_SOURCE = "manual entry"


class DuplicateEvent(EntryError):
    pass


def add_manual_event(
    session: Session,
    claim_slug: str,
    *,
    type: EventType,
    event_date: date,
    source_url: str,
    summary: str,
    now: datetime,
    source_name: str = MANUAL_SOURCE,
    external_id: str | None = None,
    trial_phases: Sequence[TrialPhase] = (),
    trial_state: TrialState | None = None,
    regulatory_outcome: RegulatoryOutcome | None = None,
) -> EvidenceEvent:
    claim = claim_by_slug(session, claim_slug)
    source_url = source_url.strip()
    if not source_url.startswith(("http://", "https://")):
        raise InvalidUrl("An event needs a source link starting with http:// or https://.")
    summary = tidy(summary)
    if not summary:
        raise MissingField("summary is required.")
    external_id = (external_id or "").strip()

    if type in TRIAL_EVENT_TYPES:
        if not external_id:
            raise MissingField("A trial event needs the trial's registry identifier.")
        if not trial_phases:
            raise MissingField("A trial event needs the trial's phase (or not_applicable).")
    elif trial_phases:
        raise InvalidField("Only a trial event has a phase.")
    if type is EventType.TRIAL_STATUS_CHANGE and trial_state is None:
        raise MissingField("A trial status change needs the state it reports.")
    if type is not EventType.TRIAL_STATUS_CHANGE and trial_state is not None:
        raise InvalidField("Only a trial status change has a state.")
    if type is EventType.REGULATORY_DECISION and regulatory_outcome is None:
        raise MissingField("A regulatory decision needs its outcome: approved or refused.")
    if type is not EventType.REGULATORY_DECISION and regulatory_outcome is not None:
        raise InvalidField("Only a regulatory decision has an outcome.")

    entered = {
        "entered_by": "operator",
        "type": type.value,
        "event_date": event_date.isoformat(),
        "source_name": source_name,
        "source_url": source_url,
        "summary": summary,
        "external_id": external_id or None,
        "trial_phases": [phase.value for phase in trial_phases],
        "trial_state": trial_state.value if trial_state else None,
        "regulatory_outcome": regulatory_outcome.value if regulatory_outcome else None,
    }
    draft = EventDraft(
        type=type,
        event_date=event_date,
        date_basis="entered by operator",
        source_name=source_name.strip() or MANUAL_SOURCE,
        source_url=source_url,
        external_id=external_id or source_url,
        summary=summary,
        confidence=1.0,
        raw_payload=entered,
        fetched_at=now,
        trial_phases=tuple(trial_phases),
        trial_state=trial_state,
        regulatory_outcome=regulatory_outcome,
        always_review=True,
    )
    duplicate = session.scalars(
        select(EvidenceEvent.id).where(
            EvidenceEvent.claim_id == claim.id, EvidenceEvent.dedupe_key == draft.dedupe_key
        )
    ).first()
    if duplicate is not None:
        raise DuplicateEvent(f"Claim '{claim.slug}' already has this event from {source_url}.")
    event = event_row(claim, draft)
    session.add(event)
    session.flush()
    return event
