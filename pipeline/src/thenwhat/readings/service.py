"""Asking a model to read a trial's stored record, checking what it says, and storing it.
Behavior: openspec record-readings; decision: docs/adr/0002.

The model is shown the titles and time frames of the trial's planned primary outcomes,
as the trial's facts carry them, and nothing else of the record. It answers in fixed
fields only. Each reading is checked by the pure rules before it is stored; one that
fails is not stored, and its reason is kept. Nothing here is an input to a claim's
status, a match's score or a trial's facts.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from thenwhat.db.models import Claim, EvidenceEvent, Reading, TrialRead
from thenwhat.domain import (
    TRIAL_EVENT_TYPES,
    FollowUpUnit,
    MeasureCode,
    ReadBy,
    ReadingField,
    ReadingKind,
    ReviewState,
)
from thenwhat.events.trial_facts import read_trial
from thenwhat.events.trial_records import newest_registry_record
from thenwhat.llm.errors import BudgetExceeded, LlmError, LlmNotConfigured
from thenwhat.readings.rules import FIELD_OF_KIND, Outcome, Proposed, Refusal, input_hash, refusal

if TYPE_CHECKING:
    from thenwhat.llm.client import Llm

# The ledger's name for these calls.
PURPOSE = "readings"
# Changed with any change to INSTRUCTIONS or to the answer's shape: a trial read under
# another version is read again.
INSTRUCTIONS_VERSION = "1"
INSTRUCTIONS = """\
You read the planned primary outcomes of one clinical trial, as its registry record
lists them: each has a number, a title and a time frame. You answer in the fixed fields
only. Never write a sentence, an explanation, a summary or a judgement of the trial.

For each outcome, give its number and:

follow_up: how long after the start the outcome is measured, when the time frame says so
as a number with a unit. `number` is that number, in digits as the time frame writes it.
`unit` is one of: days, weeks, months, years. `words` is the part of the time frame you
read it from, copied character for character. When the time frame gives several times,
read the last. Never convert between units and never work a number out. When the time
frame gives no such number, leave follow_up empty.

measure: what kind of measure the title names. `code` is one of:
symptom_score (a score or scale of symptoms or of how severe a condition is),
frequency (how often something happens, or how many people it happens to),
body_measure (a body measurement or a laboratory value),
scan_finding (what a scan or image shows),
survival (survival, or the time until an event),
side_effects (side effects, safety or tolerability),
use_of_treatment (how much or how long the treatment is used),
quality_of_life (quality of life or daily functioning),
physical_test (a timed or scored test of what the body can do, such as walking, grip or balance),
other (none of these, or not clear from the title).
`words` is the part of the title you read it from, copied character for character.

confidence, for each: how sure you are of the reading, from 0 to 1.
"""


# What the model may answer. Anything it adds outside these fields is dropped when the
# answer is read, so no sentence of the model's is ever kept.
class _Fixed(BaseModel):
    model_config = ConfigDict(extra="ignore")


class ProposedFollowUp(_Fixed):
    number: int
    # Checked against the list by the rules, so that a unit outside it is a refusal
    # with a reason and not a failed call.
    unit: str
    words: str
    confidence: float = Field(ge=0, le=1)


class ProposedMeasure(_Fixed):
    code: str
    words: str
    confidence: float = Field(ge=0, le=1)


class OutcomeAnswer(_Fixed):
    outcome: int
    follow_up: ProposedFollowUp | None = None
    measure: ProposedMeasure | None = None


class ReadingsAnswer(_Fixed):
    outcomes: list[OutcomeAnswer]


@dataclass(frozen=True, slots=True)
class TrialRecord:
    """What a trial's stored registry record gives the readings step."""

    source_name: str
    trial_id: str
    # The planned primary outcomes exactly as the trial's facts carry them.
    outcomes: tuple[Outcome, ...]


@dataclass(slots=True)
class ReadingsRun:
    """What one run of the readings step did."""

    # Trials the model was asked about.
    read: list[str] = field(default_factory=list)
    # Trials whose record and instructions are those of their stored read: not asked.
    unchanged: list[str] = field(default_factory=list)
    stored: list[Reading] = field(default_factory=list)
    # Readings the rules refused, by reason.
    refused: Counter[Refusal] = field(default_factory=Counter)
    # Trials whose call failed, with what the failure said. They keep what they had.
    failed: list[tuple[str, str]] = field(default_factory=list)
    # Said when the monthly spend ceiling stopped the run.
    stopped: str | None = None
    # Trials the run stopped before. They have no new reading.
    unread: list[str] = field(default_factory=list)


def outcomes_of(payload: dict) -> tuple[Outcome, ...]:
    """The planned primary outcomes a registry record's trial facts carry."""
    planned = read_trial(payload).facts.primary_outcomes
    return tuple(Outcome(outcome.measure, outcome.time_frame) for outcome in planned)


def trials_of(session: Session, claim: Claim) -> list[TrialRecord]:
    """The claim's trials that can be read: those behind its approved trial events that
    hold a registry record with a planned primary outcome. The record is the one the
    trial's exported facts are read from."""
    events = session.scalars(
        select(EvidenceEvent)
        .where(
            EvidenceEvent.claim_id == claim.id,
            EvidenceEvent.review_state == ReviewState.APPROVED,
            EvidenceEvent.type.in_(TRIAL_EVENT_TYPES),
        )
        .order_by(EvidenceEvent.event_date, EvidenceEvent.id)
    )
    by_trial: dict[str, list[EvidenceEvent]] = {}
    for event in events:
        by_trial.setdefault(event.external_id, []).append(event)
    trials: list[TrialRecord] = []
    for trial_id, held in sorted(by_trial.items()):
        record = newest_registry_record(held)
        if record is None:
            continue
        outcomes = outcomes_of(record.raw_payload)
        if outcomes:
            trials.append(TrialRecord(record.source_name, trial_id, outcomes))
    return trials


def published_claims(session: Session) -> list[Claim]:
    """Every published claim: approved and not archived."""
    return list(
        session.scalars(
            select(Claim)
            .where(Claim.review_state == ReviewState.APPROVED, Claim.archived_at.is_(None))
            .order_by(Claim.slug)
        )
    )


def stored_read(session: Session, source_name: str, trial_id: str) -> TrialRead | None:
    return session.scalar(
        select(TrialRead).where(
            TrialRead.source_name == source_name, TrialRead.trial_id == trial_id
        )
    )


def readings_of(session: Session, read: TrialRead) -> list[Reading]:
    return list(
        session.scalars(
            select(Reading)
            .where(Reading.trial_read_id == read.id)
            .order_by(Reading.outcome, Reading.kind, Reading.id)
        )
    )


def readings_for(
    session: Session, source_name: str, trial_id: str, outcomes: Sequence[Outcome]
) -> list[Reading]:
    """The stored readings of the trial that were read from these outcomes: none when the
    trial was never read, or was read from a record whose outcomes differ."""
    read = stored_read(session, source_name, trial_id)
    if read is None or read.input_hash != input_hash(outcomes):
        return []
    return readings_of(session, read)


def is_current(read: TrialRead | None, trial: TrialRecord) -> bool:
    """Whether the stored read is of this record under these instructions."""
    return (
        read is not None
        and read.input_hash == input_hash(trial.outcomes)
        and read.instructions_version == INSTRUCTIONS_VERSION
    )


def shown(trial: TrialRecord) -> str:
    """What the model is shown of the trial: the number, title and time frame of each
    planned primary outcome. Nothing else of the record."""
    return "\n\n".join(
        f"Outcome {number}\nTitle: {outcome.measure}\n"
        f"Time frame: {outcome.time_frame if outcome.time_frame is not None else ''}"
        for number, outcome in enumerate(trial.outcomes)
    )


def proposed(answer: ReadingsAnswer) -> list[tuple[Proposed, float]]:
    """The answer as readings to check, each with how sure the model said it was."""
    readings: list[tuple[Proposed, float]] = []
    for outcome in answer.outcomes:
        if outcome.follow_up is not None:
            readings.append(
                (
                    Proposed(
                        outcome=outcome.outcome,
                        kind=ReadingKind.FOLLOW_UP.value,
                        field=FIELD_OF_KIND[ReadingKind.FOLLOW_UP].value,
                        words=outcome.follow_up.words,
                        number=outcome.follow_up.number,
                        unit=outcome.follow_up.unit,
                    ),
                    outcome.follow_up.confidence,
                )
            )
        if outcome.measure is not None:
            readings.append(
                (
                    Proposed(
                        outcome=outcome.outcome,
                        kind=ReadingKind.MEASURE.value,
                        field=FIELD_OF_KIND[ReadingKind.MEASURE].value,
                        words=outcome.measure.words,
                        code=outcome.measure.code,
                    ),
                    outcome.measure.confidence,
                )
            )
    return readings


def read_record(
    session: Session, llm: "Llm", trial: TrialRecord, *, now: datetime, run: ReadingsRun
) -> None:
    """Read one trial, unless its stored read is of this record under these instructions.

    The model is asked for one follow-up and one measure per outcome. Each is checked by
    the rules; the trial's earlier read and readings are replaced by this read and the
    readings that pass. Raises what the model call raises, with nothing changed.
    """
    earlier = stored_read(session, trial.source_name, trial.trial_id)
    if is_current(earlier, trial):
        run.unchanged.append(trial.trial_id)
        return
    answer = llm.run(
        PURPOSE, instructions=INSTRUCTIONS, prompt=shown(trial), output_type=ReadingsAnswer
    )
    provider, _, model = (llm.model_name or "").partition(":")

    if earlier is not None:
        session.execute(delete(Reading).where(Reading.trial_read_id == earlier.id))
        session.delete(earlier)
        session.flush()
    read = TrialRead(
        source_name=trial.source_name,
        trial_id=trial.trial_id,
        input_hash=input_hash(trial.outcomes),
        instructions_version=INSTRUCTIONS_VERSION,
        provider=provider,
        model=model,
        refusals=[],
        read_at=now,
    )
    session.add(read)
    session.flush()

    refusals: list[dict[str, object]] = []
    kept: set[tuple[int, str]] = set()
    for reading, confidence in proposed(answer):
        refused = refusal(reading, trial.outcomes)
        if refused is None and (reading.outcome, reading.kind) in kept:
            refused = Refusal.REPEATED
        if refused is not None:
            run.refused[refused] += 1
            refusals.append(
                {"outcome": reading.outcome, "kind": reading.kind, "reason": refused.value}
            )
            continue
        kept.add((reading.outcome, reading.kind))
        kind = ReadingKind(reading.kind)
        stored = Reading(
            trial_read_id=read.id,
            outcome=reading.outcome,
            kind=kind,
            field=ReadingField(reading.field),
            words=reading.words,
            number=reading.number if kind is ReadingKind.FOLLOW_UP else None,
            unit=FollowUpUnit(reading.unit) if kind is ReadingKind.FOLLOW_UP else None,
            code=MeasureCode(reading.code) if kind is ReadingKind.MEASURE else None,
            confidence=confidence,
            decided_by=ReadBy.MODEL,
        )
        session.add(stored)
        run.stored.append(stored)
    read.refusals = refusals
    session.flush()
    run.read.append(trial.trial_id)


def read_trials(
    session: Session, llm: "Llm", trials: Sequence[TrialRecord], *, now: datetime
) -> ReadingsRun:
    """Read each trial once, in order. When the monthly spend ceiling is reached the run
    stops there and says so: the trials it did not reach keep what they had, which for a
    trial never read is no reading. A trial whose call fails otherwise is reported and
    the run goes on. A model that is not configured is raised: nothing can be read."""
    run = ReadingsRun()
    # A trial two claims share is read once, as the first of them holds it.
    once: dict[tuple[str, str], TrialRecord] = {}
    for trial in trials:
        once.setdefault((trial.source_name, trial.trial_id), trial)
    todo = list(once.values())
    for place, trial in enumerate(todo):
        try:
            read_record(session, llm, trial, now=now, run=run)
        except BudgetExceeded as error:
            run.stopped = str(error)
            run.unread = [
                later.trial_id
                for later in todo[place:]
                if not is_current(stored_read(session, later.source_name, later.trial_id), later)
            ]
            break
        except LlmNotConfigured:
            raise
        except LlmError as error:
            run.failed.append((trial.trial_id, str(error)))
    return run
