"""An evidence event before it is stored."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from thenwhat.domain import EventType, RegulatoryOutcome, TrialPhase, TrialState


@dataclass(frozen=True, slots=True)
class EventDraft:
    type: EventType
    event_date: date
    date_basis: str
    source_name: str
    source_url: str
    external_id: str
    summary: str
    confidence: float
    raw_payload: dict[str, Any]
    fetched_at: datetime
    trial_phases: tuple[TrialPhase, ...] = ()
    trial_state: TrialState | None = None
    regulatory_outcome: RegulatoryOutcome | None = None
    # Hand-entered events always wait for review.
    always_review: bool = False

    @property
    def dedupe_key(self) -> str:
        """Identifies the fact, so fetching again never records it twice. The state is
        part of it so that one trial can have several status changes."""
        state = self.trial_state.value if self.trial_state else ""
        return f"{self.source_name}|{self.external_id}|{self.type.value}|{state}"
