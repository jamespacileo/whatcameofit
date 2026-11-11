"""Pure status rules.

Status is a function of a claim's approved evidence events, its failure flags,
its first reported date and an as-of date. Nothing here may touch a database,
the network or the clock. Behavior: openspec status-derivation.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

from thenwhat.domain import (
    ClaimStatus,
    EventType,
    RegulatoryOutcome,
    ReviewState,
    TrialPhase,
    TrialState,
)


@dataclass(frozen=True, slots=True)
class Evidence:
    """What the rules need to know about one evidence event."""

    id: int
    type: EventType
    event_date: date
    external_id: str
    review_state: ReviewState = ReviewState.APPROVED
    trial_phases: tuple[TrialPhase, ...] = ()
    trial_state: TrialState | None = None
    regulatory_outcome: RegulatoryOutcome | None = None


@dataclass(frozen=True, slots=True)
class Flag:
    """A human-set marker that a trial missed its primary endpoint."""

    trial_external_id: str
    evidence_event_id: int


@dataclass(frozen=True, slots=True)
class Derivation:
    status: ClaimStatus
    overlay_years: int | None
    explaining_event_ids: tuple[int, ...]


TRIAL_EVENT_TYPES = frozenset(
    {
        EventType.TRIAL_REGISTERED,
        EventType.TRIAL_STATUS_CHANGE,
        EventType.TRIAL_RESULTS_POSTED,
    }
)

# A trial in one of these states no longer stands.
ENDED_WITHOUT_RESULT = frozenset({TrialState.TERMINATED, TrialState.WITHDRAWN})

# When two status changes share a date, the later entry here is the current state.
STATE_ORDER = {
    TrialState.STARTED: 0,
    TrialState.SUSPENDED: 1,
    TrialState.COMPLETED: 2,
    TrialState.TERMINATED: 3,
    TrialState.WITHDRAWN: 3,
}

# Phases with no entry (not applicable, unknown) do not move a claim past "trial registered".
PHASE_STAGE = {
    TrialPhase.EARLY_PHASE_1: 1,
    TrialPhase.PHASE_1: 1,
    TrialPhase.PHASE_2: 2,
    TrialPhase.PHASE_3: 3,
    TrialPhase.PHASE_4: 3,
}

STAGE_STATUS = {
    0: ClaimStatus.TRIAL_REGISTERED,
    1: ClaimStatus.PHASE_1,
    2: ClaimStatus.PHASE_2,
    3: ClaimStatus.PHASE_3,
}


# Statuses that describe a stage still open to further evidence. Only these carry
# the no-signal overlay; the others are outcomes.
OVERLAY_STATUSES = frozenset(
    {
        ClaimStatus.PRECLINICAL_ONLY,
        ClaimStatus.TRIAL_REGISTERED,
        ClaimStatus.PHASE_1,
        ClaimStatus.PHASE_2,
        ClaimStatus.PHASE_3,
    }
)


def _whole_years(start: date, end: date) -> int:
    anniversary_passed = (end.month, end.day) >= (start.month, start.day)
    return end.year - start.year - (0 if anniversary_passed else 1)


def _chronological(event: Evidence) -> tuple[date, int]:
    return (event.event_date, event.id)


def _trials(approved: list[Evidence]) -> dict[str, list[Evidence]]:
    """Approved trial events grouped by registry identifier, oldest first."""
    trials: dict[str, list[Evidence]] = {}
    for event in approved:
        if event.type in TRIAL_EVENT_TYPES:
            trials.setdefault(event.external_id, []).append(event)
    return trials


def _current_state(trial: list[Evidence]) -> TrialState | None:
    changes = [
        (event.event_date, STATE_ORDER[event.trial_state], event.id, event.trial_state)
        for event in trial
        if event.trial_state is not None
    ]
    return max(changes)[-1] if changes else None


def _has_started(trial: list[Evidence]) -> bool:
    return any(event.trial_state is TrialState.STARTED for event in trial)


def _stage(trial: list[Evidence]) -> int:
    """Stage of a trial from its most recently recorded phases; the lower of two."""
    phases = next((event.trial_phases for event in reversed(trial) if event.trial_phases), ())
    stages = [PHASE_STAGE[phase] for phase in phases if phase in PHASE_STAGE]
    return min(stages, default=0)


def derive(
    events: Iterable[Evidence],
    flags: Iterable[Flag] = (),
    *,
    first_reported_date: date | None,
    as_of: date,
    origin_paper_ids: frozenset[str] = frozenset(),
    no_signal_years: int = 3,
) -> Derivation:
    approved = sorted(
        (event for event in events if event.review_state is ReviewState.APPROVED),
        key=_chronological,
    )
    approved_ids = {event.id for event in approved}
    trials = _trials(approved)
    counted_flags = [
        flag
        for flag in flags
        if flag.evidence_event_id in approved_ids and flag.trial_external_id in trials
    ]
    failed = {flag.trial_external_id for flag in counted_flags}
    standing = {
        trial_id: trial
        for trial_id, trial in trials.items()
        if trial_id not in failed and _current_state(trial) not in ENDED_WITHOUT_RESULT
    }

    origin_papers = {paper_id.lower() for paper_id in origin_paper_ids}
    origin_retractions = [
        event
        for event in approved
        if event.type is EventType.RETRACTION and event.external_id.lower() in origin_papers
    ]
    approvals = [
        event for event in approved if event.regulatory_outcome is RegulatoryOutcome.APPROVED
    ]

    explaining: list[Evidence]
    if origin_retractions:
        status = ClaimStatus.RETRACTED
        explaining = origin_retractions
    elif approvals:
        status = ClaimStatus.APPROVED
        explaining = approvals
    elif standing:
        started = [trial for trial in standing.values() if _has_started(trial)]
        furthest = max((_stage(trial) for trial in started), default=0)
        status = STAGE_STATUS[furthest]
        # A phase is explained by the trials that reached it; "trial registered" by
        # every standing trial, since none has gone further.
        deciding = (
            [trial for trial in started if _stage(trial) == furthest]
            if furthest
            else list(standing.values())
        )
        explaining = [event for trial in deciding for event in trial]
    elif failed:
        status = ClaimStatus.FAILED
        reports = {flag.evidence_event_id for flag in counted_flags}
        explaining = [
            event
            for event in approved
            if event.id in reports
            or (event.type in TRIAL_EVENT_TYPES and event.external_id in failed)
        ]
    elif trials:
        status = ClaimStatus.TERMINATED
        explaining = [event for trial in trials.values() for event in trial]
    else:
        status = ClaimStatus.PRECLINICAL_ONLY
        explaining = []

    last_signal = approved[-1].event_date if approved else first_reported_date
    overlay_years = None
    if status in OVERLAY_STATUSES and last_signal is not None:
        quiet_years = _whole_years(last_signal, as_of)
        if quiet_years >= no_signal_years:
            overlay_years = quiet_years

    return Derivation(
        status=status,
        overlay_years=overlay_years,
        explaining_event_ids=tuple(event.id for event in sorted(explaining, key=_chronological)),
    )
