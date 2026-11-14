"""Record readings: the checks (pure), reading a trial's stored record with a scripted
model, storing what passes, and the export. Scenario names are from openspec
record-readings.

The registry record is a recorded fixture with its planned primary outcomes replaced.
No model and no network is called.
"""

import copy
import json
from collections.abc import Callable
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import jsonschema
import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.claims.entry import add_article, add_claim
from thenwhat.db.models import Claim, EvidenceEvent, LlmUsage, Reading, TrialRead
from thenwhat.domain import (
    Decider,
    FollowUpUnit,
    MeasureCode,
    ReadBy,
    ReadingField,
    ReadingKind,
    ReviewState,
)
from thenwhat.events.fetch import event_row
from thenwhat.events.trial import trial_events
from thenwhat.export.build import build_export
from thenwhat.llm.client import Llm, LlmNotConfigured, LlmSettings
from thenwhat.readings.rules import Outcome, Proposed, Refusal, input_hash, number_in, refusal
from thenwhat.readings.service import (
    INSTRUCTIONS_VERSION,
    PURPOSE,
    ReadingsRun,
    read_trials,
    trials_of,
)
from thenwhat.review.decisions import record_decision
from thenwhat.sources.base import SourceRecord

FETCHED = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)
FETCHED_AGAIN = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
SLUG = "nerve-stimulation-tics"
TRIAL = "NCT02586935"
OTHER_TRIAL = "NCT04951479"
CHECKED_IN_SCHEMA = Path(__file__).resolve().parents[2] / "site" / "export.schema.json"

TIME_FRAME = "Baseline and week 4 after starting stimulation"
SCORE_TITLE = (
    "Change in Yale Global Tic Severity Scale - Revised (YGTSS-R) Total Tic Severity Score"
)
USE_TITLE = "Time Spent Using the Device Per Day of Use"
DESCRIPTION = "A sponsor's description that the model must never be shown."
OUTCOMES = [
    {"measure": SCORE_TITLE, "description": DESCRIPTION, "timeFrame": TIME_FRAME},
    {"measure": USE_TITLE, "description": DESCRIPTION, "timeFrame": "Up to 12 weeks"},
]
SENTENCE = "This trial followed people for a month and looks promising."
# What the scripted model answers for the outcomes above.
ANSWER: dict[str, Any] = {
    "outcomes": [
        {
            "outcome": 0,
            "follow_up": {"number": 4, "unit": "weeks", "words": TIME_FRAME, "confidence": 0.92},
            "measure": {
                "code": "symptom_score",
                "words": "Total Tic Severity Score",
                "confidence": 0.9,
            },
        },
        {
            "outcome": 1,
            "follow_up": {
                "number": 12,
                "unit": "weeks",
                "words": "12 weeks",
                "confidence": 0.95,
            },
            "measure": {"code": "use_of_treatment", "words": USE_TITLE, "confidence": 0.88},
        },
    ]
}


# --- the checks: pure, no database -------------------------------------------------------

PLANNED = [Outcome(SCORE_TITLE, "Baseline and week 4"), Outcome(USE_TITLE, None)]


def follow_up(**overrides: Any) -> Proposed:
    values: dict[str, Any] = {
        "outcome": 0,
        "kind": "follow_up",
        "field": "time_frame",
        "words": "week 4",
        "number": 4,
        "unit": "weeks",
    }
    return Proposed(**(values | overrides))


def measure(**overrides: Any) -> Proposed:
    values: dict[str, Any] = {
        "outcome": 1,
        "kind": "measure",
        "field": "measure",
        "words": USE_TITLE,
        "code": "use_of_treatment",
    }
    return Proposed(**(values | overrides))


def test_a_reading_whose_words_number_unit_and_code_hold_passes():
    assert refusal(follow_up(), PLANNED) is None
    assert refusal(measure(), PLANNED) is None


@pytest.mark.parametrize(
    "words", ["week four", "Week 4", "week  4", "", "Baseline and week 4 after starting"]
)
def test_words_that_are_not_in_the_records_field_are_refused(words: str):
    """Scenario: Words not in the record"""
    assert refusal(follow_up(words=words), PLANNED) is Refusal.WORDS_NOT_IN_RECORD


def test_words_are_looked_for_in_the_named_field_only():
    """Scenario: Words not in the record"""
    # The title's words are not in the time frame, and the second outcome has none.
    assert refusal(follow_up(words="Tic Severity"), PLANNED) is Refusal.WORDS_NOT_IN_RECORD
    assert refusal(follow_up(outcome=1, words="week 4"), PLANNED) is Refusal.WORDS_NOT_IN_RECORD
    assert refusal(follow_up(field="measure"), PLANNED) is Refusal.WRONG_FIELD


def test_a_number_the_words_do_not_give_is_refused():
    """Scenario: Number the words do not give"""
    twelve_weeks = follow_up(number=12, words="Baseline and week 4")

    assert refusal(twelve_weeks, PLANNED) is Refusal.NUMBER_NOT_IN_WORDS


@pytest.mark.parametrize(
    ("number", "words", "found"),
    [
        (4, "week 4", True),
        (4, "4 weeks", True),
        (4, "week 14", False),
        (4, "week 40", False),
        (4, "week 4.5", False),
        (4, "four weeks", False),
        (-4, "week -4", False),
    ],
)
def test_the_number_must_be_in_the_words_as_digits_of_its_own(number: int, words: str, found: bool):
    """Scenario: Number the words do not give"""
    assert number_in(number, words) is found


def test_a_measure_code_outside_the_list_is_refused():
    """Scenario: Code outside the list"""
    assert refusal(measure(code="biomarker"), PLANNED) is Refusal.UNKNOWN_CODE
    assert refusal(measure(code=None), PLANNED) is Refusal.UNKNOWN_CODE


def test_a_kind_a_unit_or_an_outcome_outside_what_is_known_is_refused():
    """Scenario: Code outside the list"""
    assert refusal(follow_up(unit="fortnights"), PLANNED) is Refusal.UNKNOWN_UNIT
    assert refusal(follow_up(kind="dose"), PLANNED) is Refusal.UNKNOWN_KIND
    assert refusal(follow_up(outcome=2), PLANNED) is Refusal.NO_SUCH_OUTCOME
    assert refusal(follow_up(outcome=-1), PLANNED) is Refusal.NO_SUCH_OUTCOME


# --- reading a trial's stored record ----------------------------------------------------


def study_with(
    fixture_json: Callable[[str], dict[str, Any]],
    outcomes: list[dict[str, Any]],
    *,
    trial_id: str = TRIAL,
    results_posted: bool = False,
) -> dict[str, Any]:
    """A recorded registry record with its planned primary outcomes replaced."""
    study = copy.deepcopy(fixture_json("clinicaltrials/study_NCT02586935.json"))
    protocol = study["protocolSection"]
    protocol["identificationModule"]["nctId"] = trial_id
    protocol["outcomesModule"]["primaryOutcomes"] = outcomes
    if results_posted:
        # What a later fetch of the record shows: results, and so a new event.
        study["hasResults"] = True
        protocol["statusModule"]["resultsFirstPostDateStruct"] = {"date": "2026-11-12"}
    return study


def store_record(
    session: Session, claim: Claim, study: dict[str, Any], *, fetched_at: datetime = FETCHED
) -> None:
    """Store the events a fetch of the record creates, approved, each keeping the record
    as its payload. As in a real fetch, a fact the claim already has gets no second event."""
    nct_id = study["protocolSection"]["identificationModule"]["nctId"]
    record = SourceRecord(
        "clinicaltrials.gov",
        nct_id,
        f"https://clinicaltrials.gov/study/{nct_id}",
        study,
        fetched_at,
    )
    held = set(
        session.scalars(select(EvidenceEvent.dedupe_key).where(EvidenceEvent.claim_id == claim.id))
    )
    for draft in trial_events(record):
        if draft.dedupe_key in held:
            continue
        event = event_row(claim, draft)
        record_decision(event, ReviewState.APPROVED, by=Decider.RULE, now=fetched_at)
        session.add(event)
    session.flush()


@pytest.fixture
def claim(session: Session, fixture_json) -> Claim:
    """A published claim with one trial, whose stored record plans the two outcomes."""
    claim = add_claim(
        session,
        slug=SLUG,
        headline="A wrist device was reported to ease tics",
        vertical="mouth-and-teeth",
        intervention="Median nerve stimulation",
        indication="Tourette syndrome",
    )
    add_article(
        session,
        SLUG,
        url="https://news.example.org/2026/tics",
        outlet="Example News",
        title="Device",
        published_date=date(2026, 3, 1),
    )
    record_decision(claim, ReviewState.APPROVED, by=Decider.RULE, now=FETCHED)
    store_record(session, claim, study_with(fixture_json, OUTCOMES))
    return claim


class Scripted:
    """A model that answers every call with the next of the given answers, repeating the
    last, and keeps what it was shown."""

    def __init__(self, *answers: dict[str, Any]) -> None:
        self.answers = list(answers)
        self.shown: list[str] = []

    def respond(self, messages, info) -> ModelResponse:
        self.shown.append(str(messages))
        answer = self.answers.pop(0) if len(self.answers) > 1 else self.answers[0]
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, answer)])


def llm(session: Session, scripted: Scripted, **overrides: Any) -> Llm:
    values: dict[str, Any] = {
        "model": "test:scripted-model",
        "monthly_budget_usd": Decimal("10"),
        "input_usd_per_mtok": Decimal("3"),
        "output_usd_per_mtok": Decimal("15"),
    }
    settings = LlmSettings(**(values | overrides))
    return Llm(
        session,
        settings,
        model=FunctionModel(scripted.respond, model_name="scripted-model"),
        now=lambda: NOW,
    )


def read(session: Session, claim: Claim, scripted: Scripted, **overrides: Any) -> ReadingsRun:
    client = llm(session, scripted, **overrides)
    return read_trials(session, client, trials_of(session, claim), now=NOW)


def stored(session: Session) -> list[Reading]:
    session.flush()
    return list(session.scalars(select(Reading).order_by(Reading.outcome, Reading.kind)))


def reads(session: Session) -> list[TrialRead]:
    session.flush()
    return list(session.scalars(select(TrialRead).order_by(TrialRead.trial_id)))


def with_follow_up(**changes: Any) -> dict[str, Any]:
    """The scripted answer with the first outcome's follow-up changed."""
    answer = copy.deepcopy(ANSWER)
    answer["outcomes"][0]["follow_up"] |= changes
    return answer


def test_follow_up_is_read_as_a_number_with_a_unit_and_the_words(session: Session, claim: Claim):
    """Scenario: How long the main measure was followed"""
    read(session, claim, Scripted(ANSWER))

    reading = stored(session)[0]
    assert (reading.outcome, reading.kind) == (0, ReadingKind.FOLLOW_UP)
    assert (reading.number, reading.unit) == (4, FollowUpUnit.WEEKS)
    assert (reading.field, reading.words) == (ReadingField.TIME_FRAME, TIME_FRAME)
    assert reading.code is None
    assert reading.confidence == 0.92


def test_measure_is_read_as_a_code_with_the_title(session: Session, claim: Claim):
    """Scenario: What kind of measure"""
    read(session, claim, Scripted(ANSWER))

    reading = stored(session)[3]
    assert (reading.outcome, reading.kind) == (1, ReadingKind.MEASURE)
    assert reading.code is MeasureCode.USE_OF_TREATMENT
    assert (reading.field, reading.words) == (ReadingField.MEASURE, USE_TITLE)
    assert (reading.number, reading.unit) == (None, None)


def test_a_reading_is_kept_with_its_record_instructions_and_model_as_a_models(
    session: Session, claim: Claim
):
    run = read(session, claim, Scripted(ANSWER))

    [trial_read] = reads(session)
    [trial] = trials_of(session, claim)
    assert (trial_read.source_name, trial_read.trial_id) == ("clinicaltrials.gov", TRIAL)
    assert trial_read.input_hash == input_hash(trial.outcomes)
    assert trial_read.instructions_version == INSTRUCTIONS_VERSION
    # As the environment names them in LLM_MODEL.
    assert (trial_read.provider, trial_read.model) == ("test", "scripted-model")
    assert (trial_read.read_at, trial_read.refusals) == (NOW, [])
    assert {reading.decided_by for reading in stored(session)} == {ReadBy.MODEL}
    assert (run.read, len(run.stored)) == ([TRIAL], 4)
    [usage] = session.scalars(select(LlmUsage))
    assert usage.purpose == PURPOSE


def test_the_model_is_shown_titles_and_time_frames_and_nothing_else_of_the_record(
    session: Session, claim: Claim
):
    model = Scripted(ANSWER)

    read(session, claim, model)

    [shown] = model.shown
    for carried in (SCORE_TITLE, TIME_FRAME, USE_TITLE, "Up to 12 weeks"):
        assert carried in shown
    assert DESCRIPTION not in shown
    assert TRIAL not in shown and "Tideglusib" not in shown


def test_text_outside_the_fixed_fields_is_not_stored(session: Session, claim: Claim):
    """Scenario: Model returns a sentence"""
    answer = copy.deepcopy(ANSWER)
    answer["summary"] = SENTENCE
    answer["outcomes"][0]["note"] = SENTENCE
    answer["outcomes"][0]["follow_up"]["plain"] = SENTENCE
    answer["outcomes"][1]["measure"]["explanation"] = SENTENCE

    read(session, claim, Scripted(answer))

    assert len(stored(session)) == 4
    kept = [
        str(getattr(row, column.name))
        for row in [*stored(session), *reads(session)]
        for column in row.__table__.columns
    ]
    assert not [value for value in kept if "promising" in value]


def test_a_sentence_given_as_the_words_is_refused_and_not_kept(session: Session, claim: Claim):
    """Scenario: Words not in the record"""
    run = read(session, claim, Scripted(with_follow_up(words=SENTENCE)))

    assert run.refused == {Refusal.WORDS_NOT_IN_RECORD: 1}
    assert [(r.outcome, r.kind) for r in stored(session)] == [
        (0, ReadingKind.MEASURE),
        (1, ReadingKind.FOLLOW_UP),
        (1, ReadingKind.MEASURE),
    ]
    # The refusal names the reason, and not the words the model gave.
    [trial_read] = reads(session)
    assert trial_read.refusals == [
        {"outcome": 0, "kind": "follow_up", "reason": "words_not_in_record"}
    ]


def test_a_number_the_time_frame_does_not_give_is_not_stored(session: Session, claim: Claim):
    """Scenario: Number the words do not give"""
    run = read(session, claim, Scripted(with_follow_up(number=12, words="Baseline and week 4")))

    assert run.refused == {Refusal.NUMBER_NOT_IN_WORDS: 1}
    assert (0, ReadingKind.FOLLOW_UP) not in [(r.outcome, r.kind) for r in stored(session)]


def test_a_code_or_unit_outside_the_lists_is_not_stored(session: Session, claim: Claim):
    """Scenario: Code outside the list"""
    answer = with_follow_up(unit="fortnights")
    answer["outcomes"][1]["measure"]["code"] = "biomarker"

    run = read(session, claim, Scripted(answer))

    assert run.refused == {Refusal.UNKNOWN_UNIT: 1, Refusal.UNKNOWN_CODE: 1}
    assert [(r.outcome, r.kind) for r in stored(session)] == [
        (0, ReadingKind.MEASURE),
        (1, ReadingKind.FOLLOW_UP),
    ]


def test_a_second_reading_of_one_kind_for_one_outcome_is_refused(session: Session, claim: Claim):
    answer = copy.deepcopy(ANSWER)
    answer["outcomes"].append(copy.deepcopy(answer["outcomes"][0]))

    run = read(session, claim, Scripted(answer))

    assert run.refused == {Refusal.REPEATED: 2}
    assert len(stored(session)) == 4


def test_a_second_run_with_nothing_changed_asks_the_model_nothing(session: Session, claim: Claim):
    """Scenario: Second run with nothing changed"""
    model = Scripted(ANSWER)
    read(session, claim, model)
    before = [(r.id, r.outcome, r.kind, r.words) for r in stored(session)]

    run = read(session, claim, model)

    assert len(model.shown) == 1
    assert (run.read, run.unchanged, run.stored) == ([], [TRIAL], [])
    assert [(r.id, r.outcome, r.kind, r.words) for r in stored(session)] == before
    assert len(session.scalars(select(LlmUsage)).all()) == 1


def test_a_trial_whose_readings_were_all_refused_is_not_asked_about_again(
    session: Session, claim: Claim
):
    """Scenario: Second run with nothing changed"""
    nothing_holds = {
        "outcomes": [
            {"outcome": 0, "measure": {"code": "biomarker", "words": "Tic", "confidence": 0.5}}
        ]
    }
    model = Scripted(nothing_holds)
    read(session, claim, model)

    run = read(session, claim, model)

    assert stored(session) == []
    assert (len(model.shown), run.unchanged) == (1, [TRIAL])


def test_a_record_fetched_again_with_a_new_time_frame_is_read_again(
    session: Session, claim: Claim, fixture_json
):
    """Scenario: Record fetched again with a new time frame"""
    model = Scripted(ANSWER, with_follow_up(number=8, words="week 8"))
    read(session, claim, model)
    changed = copy.deepcopy(OUTCOMES)
    changed[0]["timeFrame"] = "Baseline and week 8 after starting stimulation"
    store_record(
        session,
        claim,
        study_with(fixture_json, changed, results_posted=True),
        fetched_at=FETCHED_AGAIN,
    )

    run = read(session, claim, model)

    assert (run.read, len(model.shown)) == ([TRIAL], 2)
    assert len(reads(session)) == 1
    readings = stored(session)
    assert len(readings) == 4
    assert (readings[0].number, readings[0].words) == (8, "week 8")
    assert TIME_FRAME not in [reading.words for reading in readings]


def test_a_trial_two_claims_share_is_read_once(session: Session, claim: Claim, fixture_json):
    other = add_claim(
        session,
        slug="second-claim",
        headline="A second report of the same device",
        vertical="mouth-and-teeth",
        intervention="Wrist stimulator",
        indication="Tourette syndrome",
    )
    store_record(session, other, study_with(fixture_json, OUTCOMES))
    model = Scripted(ANSWER)
    trials = trials_of(session, claim) + trials_of(session, other)

    run = read_trials(session, llm(session, model), trials, now=NOW)

    assert (run.read, len(model.shown)) == ([TRIAL], 1)


def test_the_run_stops_at_the_spend_ceiling_and_leaves_the_rest_unread(
    session: Session, claim: Claim, fixture_json
):
    """Scenario: Spend ceiling reached"""
    store_record(session, claim, study_with(fixture_json, OUTCOMES, trial_id=OTHER_TRIAL))
    model = Scripted(ANSWER)
    # At a dollar a token the first call alone passes the ceiling.
    dear = {"input_usd_per_mtok": Decimal("1000000"), "monthly_budget_usd": Decimal("10")}

    run = read(session, claim, model, **dear)

    assert run.stopped is not None and "monthly ceiling of $10" in run.stopped
    assert (run.read, run.unread) == ([TRIAL], [OTHER_TRIAL])
    assert len(model.shown) == 1
    assert [trial_read.trial_id for trial_read in reads(session)] == [TRIAL]
    assert len(stored(session)) == 4


def test_no_model_configured_reads_nothing_and_says_so(session: Session, claim: Claim):
    with pytest.raises(LlmNotConfigured, match="LLM_MODEL"):
        read(session, claim, Scripted(ANSWER), model=None)

    assert reads(session) == []


def test_a_trial_entered_by_hand_or_without_outcomes_is_not_read(
    session: Session, claim: Claim, fixture_json
):
    store_record(session, claim, study_with(fixture_json, [], trial_id=OTHER_TRIAL))

    assert [trial.trial_id for trial in trials_of(session, claim)] == [TRIAL]


# --- the export --------------------------------------------------------------------------


def exported(session: Session) -> dict[str, Any]:
    return json.loads(build_export(session, now=NOW).model_dump_json())


def test_status_and_trial_facts_are_the_same_with_and_without_readings(
    session: Session, claim: Claim
):
    """Scenario: Claim with and without readings"""
    [before] = exported(session)["claims"]

    read(session, claim, Scripted(ANSWER))
    [after] = exported(session)["claims"]

    assert before["trials"][0]["readings"] == []
    assert len(after["trials"][0]["readings"]) == 4
    assert after["status"] == before["status"]
    assert after["events"] == before["events"]
    assert after["matches"] == before["matches"]
    for trial in (*before["trials"], *after["trials"]):
        del trial["readings"]
    assert after["trials"] == before["trials"]


def test_an_exported_trial_carries_its_readings_with_words_and_confidence(
    session: Session, claim: Claim
):
    """Scenario: Trial with two readings"""
    answer = {"outcomes": [ANSWER["outcomes"][0]]}
    read(session, claim, Scripted(answer))

    [trial] = exported(session)["claims"][0]["trials"]

    assert trial["facts"]["primary_outcomes"][0] == {
        "measure": SCORE_TITLE,
        "time_frame": TIME_FRAME,
    }
    assert trial["readings"] == [
        {
            "kind": "follow_up",
            "outcome": 0,
            "field": "time_frame",
            "words": TIME_FRAME,
            "number": 4,
            "unit": "weeks",
            "code": None,
            "confidence": 0.92,
            "read_on": trial["facts_as_of"],
        },
        {
            "kind": "measure",
            "outcome": 0,
            "field": "measure",
            "words": "Total Tic Severity Score",
            "number": None,
            "unit": None,
            "code": "symptom_score",
            "confidence": 0.9,
            "read_on": trial["facts_as_of"],
        },
    ]
    assert trial["facts_as_of"] == "2026-11-10T09:00:00Z"


def test_the_export_is_built_from_the_database_alone(session: Session, claim: Claim):
    """Scenario: Export with no network

    Every test runs with network connections blocked, and the export asks no model: one
    that is asked here fails the test.
    """
    read(session, claim, Scripted(ANSWER))
    kept = [(r.outcome, r.kind.value, r.words) for r in stored(session)]
    usage = len(session.scalars(select(LlmUsage)).all())

    export = exported(session)

    [trial] = export["claims"][0]["trials"]
    assert [(r["outcome"], r["kind"], r["words"]) for r in trial["readings"]] == kept
    assert len(session.scalars(select(LlmUsage)).all()) == usage
    jsonschema.validate(export, json.loads(CHECKED_IN_SCHEMA.read_text()))


def test_readings_of_an_earlier_record_are_not_exported_with_the_new_facts(
    session: Session, claim: Claim, fixture_json
):
    read(session, claim, Scripted(ANSWER))
    changed = copy.deepcopy(OUTCOMES)
    changed[0]["timeFrame"] = "Baseline and week 8 after starting stimulation"
    store_record(
        session,
        claim,
        study_with(fixture_json, changed, results_posted=True),
        fetched_at=FETCHED_AGAIN,
    )

    [trial] = exported(session)["claims"][0]["trials"]

    assert trial["facts"]["primary_outcomes"][0]["time_frame"].endswith(
        "week 8 after starting stimulation"
    )
    assert trial["readings"] == []
