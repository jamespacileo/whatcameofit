"""Reading events out of one registry record, tested through the pure `trial_events`.

Starts from the recorded study and changes only the fields a test is about.
Scenario names are from openspec evidence-events.
"""

import copy
from datetime import UTC, date, datetime
from typing import Any

import pytest

from thenwhat.domain import EventType, TrialPhase, TrialState
from thenwhat.events.trial import trial_events
from thenwhat.sources.base import SourceRecord

FETCHED = datetime(2026, 11, 11, 15, 0, tzinfo=UTC)


@pytest.fixture
def study(fixture_json) -> dict[str, Any]:
    return copy.deepcopy(fixture_json("clinicaltrials/study_NCT02586935.json"))


def record(study: dict[str, Any]) -> SourceRecord:
    nct_id = study["protocolSection"]["identificationModule"]["nctId"]
    return SourceRecord(
        "clinicaltrials.gov", nct_id, f"https://clinicaltrials.gov/study/{nct_id}", study, FETCHED
    )


def status(study: dict[str, Any]) -> dict[str, Any]:
    return study["protocolSection"]["statusModule"]


def kinds(events) -> list[tuple[EventType, TrialState | None]]:
    return [(event.type, event.trial_state) for event in events]


def test_completed_trial_with_results_gives_four_events(study):
    """Scenario: Completed trial with results"""
    study["hasResults"] = True
    status(study)["resultsFirstPostDateStruct"] = {"date": "2019-06-03", "type": "ACTUAL"}

    events = trial_events(record(study))

    assert kinds(events) == [
        (EventType.TRIAL_REGISTERED, None),
        (EventType.TRIAL_STATUS_CHANGE, TrialState.STARTED),
        (EventType.TRIAL_STATUS_CHANGE, TrialState.COMPLETED),
        (EventType.TRIAL_RESULTS_POSTED, None),
    ]
    assert [event.event_date for event in events] == [
        date(2015, 10, 27),
        date(2016, 2, 10),
        date(2018, 2, 25),
        date(2019, 6, 3),
    ]


def test_recorded_study_without_results_gives_three_events(study):
    assert kinds(trial_events(record(study))) == [
        (EventType.TRIAL_REGISTERED, None),
        (EventType.TRIAL_STATUS_CHANGE, TrialState.STARTED),
        (EventType.TRIAL_STATUS_CHANGE, TrialState.COMPLETED),
    ]


def test_registered_trial_that_has_not_started_gives_one_event(study):
    """Scenario: Registered trial that has not started"""
    status(study)["overallStatus"] = "NOT_YET_RECRUITING"
    status(study)["startDateStruct"] = {"date": "2027-01", "type": "ESTIMATED"}
    status(study)["completionDateStruct"] = {"date": "2029-01", "type": "ESTIMATED"}

    assert kinds(trial_events(record(study))) == [(EventType.TRIAL_REGISTERED, None)]


def test_terminated_trial_without_a_completion_date_is_dated_from_its_last_update(study):
    """Scenario: Terminated trial without a completion date"""
    status(study)["overallStatus"] = "TERMINATED"
    del status(study)["completionDateStruct"]
    del status(study)["primaryCompletionDateStruct"]

    terminated = trial_events(record(study))[-1]

    assert terminated.trial_state is TrialState.TERMINATED
    assert terminated.event_date == date(2025, 7, 16)
    assert terminated.date_basis == "last update posted"


def test_every_event_carries_the_registry_identifier_phase_and_date_basis(study):
    events = trial_events(record(study))

    assert {event.external_id for event in events} == {"NCT02586935"}
    assert {event.trial_phases for event in events} == {(TrialPhase.PHASE_2,)}
    assert [event.date_basis for event in events] == [
        "first posted",
        "start date",
        "completion date",
    ]


def test_every_event_keeps_the_unmodified_record_and_its_fetch_time(study):
    """Scenario: Event built from a registry record"""
    events = trial_events(record(study))

    assert all(event.raw_payload == study for event in events)
    assert all(event.fetched_at == FETCHED for event in events)
    assert all(
        event.source_url == "https://clinicaltrials.gov/study/NCT02586935" for event in events
    )
    assert all(event.source_name == "clinicaltrials.gov" for event in events)


@pytest.mark.parametrize(
    ("registry_phases", "expected"),
    [
        (["EARLY_PHASE1"], (TrialPhase.EARLY_PHASE_1,)),
        (["PHASE1", "PHASE2"], (TrialPhase.PHASE_1, TrialPhase.PHASE_2)),
        (["PHASE4"], (TrialPhase.PHASE_4,)),
        (["NA"], (TrialPhase.NOT_APPLICABLE,)),
        (None, ()),
    ],
)
def test_registry_phase_spellings_become_stored_phases(study, registry_phases, expected):
    design = study["protocolSection"]["designModule"]
    if registry_phases is None:
        design.pop("phases", None)
    else:
        design["phases"] = registry_phases

    assert trial_events(record(study))[0].trial_phases == expected


@pytest.mark.parametrize(
    ("overall_status", "state"),
    [("WITHDRAWN", TrialState.WITHDRAWN), ("SUSPENDED", TrialState.SUSPENDED)],
)
def test_withdrawn_and_suspended_trials_are_dated_from_their_last_update(
    study, overall_status, state
):
    status(study)["overallStatus"] = overall_status

    last = trial_events(record(study))[-1]

    assert (last.trial_state, last.event_date, last.date_basis) == (
        state,
        date(2025, 7, 16),
        "last update posted",
    )


def test_month_only_date_is_taken_as_the_first_of_the_month_and_says_so(study):
    status(study)["startDateStruct"] = {"date": "2016-02", "type": "ACTUAL"}

    started = trial_events(record(study))[1]

    assert started.event_date == date(2016, 2, 1)
    assert started.date_basis == "start date (month only)"


def test_summaries_are_plain_statements_of_the_registry_fact(study):
    summaries = [event.summary for event in trial_events(record(study))]

    assert summaries == [
        "Trial NCT02586935 registered (Phase 2).",
        "Trial NCT02586935 started.",
        "Trial NCT02586935 completed.",
    ]


def test_events_of_one_trial_have_distinct_deduplication_keys(study):
    keys = [event.dedupe_key for event in trial_events(record(study))]

    assert keys == [
        "clinicaltrials.gov|NCT02586935|trial_registered|",
        "clinicaltrials.gov|NCT02586935|trial_status_change|started",
        "clinicaltrials.gov|NCT02586935|trial_status_change|completed",
    ]
