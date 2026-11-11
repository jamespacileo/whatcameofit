"""Events read from the dated fields of one ClinicalTrials.gov record. Pure.

Only what the current record shows is reported: one registered event, a started
event when the start date is actual, one event for a current end state, and a
results event. Earlier states the record no longer shows are not reconstructed.
"""

from datetime import date
from typing import Any

from thenwhat.domain import EventType, TrialPhase, TrialState
from thenwhat.events.draft import EventDraft
from thenwhat.sources.base import SourceRecord

PHASES = {
    "EARLY_PHASE1": TrialPhase.EARLY_PHASE_1,
    "PHASE1": TrialPhase.PHASE_1,
    "PHASE2": TrialPhase.PHASE_2,
    "PHASE3": TrialPhase.PHASE_3,
    "PHASE4": TrialPhase.PHASE_4,
    "NA": TrialPhase.NOT_APPLICABLE,
}
PHASE_LABELS = {
    TrialPhase.EARLY_PHASE_1: "Early Phase 1",
    TrialPhase.PHASE_1: "Phase 1",
    TrialPhase.PHASE_2: "Phase 2",
    TrialPhase.PHASE_3: "Phase 3",
    TrialPhase.PHASE_4: "Phase 4",
    TrialPhase.NOT_APPLICABLE: "no phase",
}
END_STATES = {
    "COMPLETED": TrialState.COMPLETED,
    "TERMINATED": TrialState.TERMINATED,
    "WITHDRAWN": TrialState.WITHDRAWN,
    "SUSPENDED": TrialState.SUSPENDED,
}
# A completion date says when a completed or terminated trial ended. A withdrawn or
# suspended trial has no such date, so its last registry update is used.
STATES_WITH_A_COMPLETION_DATE = {TrialState.COMPLETED, TrialState.TERMINATED}


def trial_events(record: SourceRecord) -> list[EventDraft]:
    study = record.payload
    status = study["protocolSection"]["statusModule"]
    registry_phases = study["protocolSection"].get("designModule", {}).get("phases", [])
    phases = tuple(PHASES[phase] for phase in registry_phases if phase in PHASES)
    trial = record.external_id

    def event(
        type: EventType,
        dated: tuple[date, str],
        summary: str,
        state: TrialState | None = None,
    ) -> EventDraft:
        return EventDraft(
            type=type,
            event_date=dated[0],
            date_basis=dated[1],
            source_name=record.source_name,
            source_url=record.url,
            external_id=trial,
            summary=summary,
            confidence=1.0,
            raw_payload=study,
            fetched_at=record.fetched_at,
            trial_phases=phases,
            trial_state=state,
        )

    events: list[EventDraft] = []
    registered = _dated(status, "studyFirstPostDateStruct", "first posted")
    if registered:
        label = "/".join(PHASE_LABELS[phase] for phase in phases) or "phase not given"
        events.append(
            event(EventType.TRIAL_REGISTERED, registered, f"Trial {trial} registered ({label}).")
        )

    started = _dated(status, "startDateStruct", "start date", actual_only=True)
    if started:
        events.append(
            event(
                EventType.TRIAL_STATUS_CHANGE,
                started,
                f"Trial {trial} started.",
                TrialState.STARTED,
            )
        )

    end_state = END_STATES.get(status.get("overallStatus", ""))
    if end_state:
        ended = None
        if end_state in STATES_WITH_A_COMPLETION_DATE:
            ended = _dated(
                status, "completionDateStruct", "completion date", actual_only=True
            ) or _dated(
                status, "primaryCompletionDateStruct", "primary completion date", actual_only=True
            )
        ended = ended or _dated(status, "lastUpdatePostDateStruct", "last update posted")
        if ended:
            events.append(
                event(
                    EventType.TRIAL_STATUS_CHANGE,
                    ended,
                    f"Trial {trial} {end_state.value}.",
                    end_state,
                )
            )

    posted = _dated(status, "resultsFirstPostDateStruct", "results first posted")
    if study.get("hasResults") and posted:
        events.append(
            event(EventType.TRIAL_RESULTS_POSTED, posted, f"Results posted for trial {trial}.")
        )
    return events


def _dated(
    status: dict[str, Any], field: str, basis: str, *, actual_only: bool = False
) -> tuple[date, str] | None:
    """The date in a registry date field and the words that say where it came from."""
    struct = status.get(field)
    if not struct or not struct.get("date"):
        return None
    if actual_only and struct.get("type") != "ACTUAL":
        return None
    text = struct["date"]
    if len(text) == 7:  # the registry gave a year and month only
        return date.fromisoformat(f"{text}-01"), f"{basis} (month only)"
    return date.fromisoformat(text), basis
