"""Status rules, tested through `derive` only.

Tests named after a scenario in openspec status-derivation carry its name in a
`Scenario:` docstring; the others pin rule text that has no scenario of its own.
"""

import ast
from datetime import date, timedelta
from itertools import count
from pathlib import Path

import pytest

from thenwhat.domain import (
    ClaimStatus,
    EventType,
    RegulatoryOutcome,
    ReviewState,
    TrialPhase,
    TrialState,
)
from thenwhat.status import rules
from thenwhat.status.rules import Derivation, Evidence, Flag, derive

FIRST_REPORTED = date(2019, 1, 1)
REGISTERED_ON = date(2020, 1, 1)
AS_OF = date(2021, 1, 1)

_ids = count(1)


def evidence(type: EventType, external_id: str, on: date, **details) -> Evidence:
    return Evidence(id=next(_ids), type=type, event_date=on, external_id=external_id, **details)


def trial(
    trial_id: str,
    phases: tuple[TrialPhase, ...],
    *states: TrialState,
    registered_on: date = REGISTERED_ON,
) -> list[Evidence]:
    """A registered event followed by one status change every 90 days."""
    events = [evidence(EventType.TRIAL_REGISTERED, trial_id, registered_on, trial_phases=phases)]
    for step, state in enumerate(states, start=1):
        events.append(
            evidence(
                EventType.TRIAL_STATUS_CHANGE,
                trial_id,
                registered_on + timedelta(days=90 * step),
                trial_phases=phases,
                trial_state=state,
            )
        )
    return events


def paper(on: date = REGISTERED_ON, doi: str = "10.1000/followup") -> Evidence:
    return evidence(EventType.FOLLOWUP_PAPER, doi, on)


def flag_on(trial_events: list[Evidence]) -> Flag:
    return Flag(trial_events[0].external_id, trial_events[-1].id)


def result(events: list[Evidence], flags: tuple[Flag, ...] = (), **inputs) -> Derivation:
    inputs.setdefault("first_reported_date", FIRST_REPORTED)
    inputs.setdefault("as_of", AS_OF)
    return derive(events, flags, **inputs)


PHASE_1 = (TrialPhase.PHASE_1,)
PHASE_2 = (TrialPhase.PHASE_2,)
PHASE_3 = (TrialPhase.PHASE_3,)
STARTED = TrialState.STARTED


# --- inputs --------------------------------------------------------------


def test_same_inputs_give_identical_results():
    """Scenario: Same inputs"""
    events = trial("NCT1", PHASE_2, STARTED) + [paper()]

    assert result(events) == result(events)


def test_pending_termination_does_not_change_status():
    """Scenario: Pending termination"""
    events = trial("NCT1", PHASE_2, STARTED)
    events.append(
        evidence(
            EventType.TRIAL_STATUS_CHANGE,
            "NCT1",
            date(2020, 9, 1),
            trial_state=TrialState.TERMINATED,
            review_state=ReviewState.PENDING,
        )
    )

    assert result(events).status is ClaimStatus.PHASE_2


def test_rejected_events_do_not_count():
    events = [
        evidence(
            EventType.TRIAL_REGISTERED,
            "NCT1",
            REGISTERED_ON,
            trial_phases=PHASE_1,
            review_state=ReviewState.REJECTED,
        )
    ]

    assert result(events).status is ClaimStatus.PRECLINICAL_ONLY


# --- standing trials and stage ---------------------------------------------


def test_suspended_trial_is_standing():
    """Scenario: Suspended trial"""
    events = trial("NCT1", PHASE_1, STARTED, TrialState.SUSPENDED)

    assert result(events).status is ClaimStatus.PHASE_1


def test_terminated_phase_1_and_recruiting_phase_2_is_phase_2():
    """Scenario: Terminated Phase 1 and recruiting Phase 2"""
    events = trial("NCT1", PHASE_1, STARTED, TrialState.TERMINATED) + trial(
        "NCT2", PHASE_2, STARTED
    )

    assert result(events).status is ClaimStatus.PHASE_2


def test_registered_but_not_started_is_trial_registered():
    """Scenario: Registered but not started"""
    assert result(trial("NCT1", PHASE_1)).status is ClaimStatus.TRIAL_REGISTERED


def test_combined_phase_trial_counts_as_the_lower_phase():
    """Scenario: Combined phase trial"""
    events = trial("NCT1", (TrialPhase.PHASE_1, TrialPhase.PHASE_2), STARTED)

    assert result(events).status is ClaimStatus.PHASE_1


def test_completed_trial_keeps_its_phase():
    """Scenario: Completed trial"""
    events = trial("NCT1", PHASE_2, STARTED, TrialState.COMPLETED)

    assert result(events).status is ClaimStatus.PHASE_2


@pytest.mark.parametrize(
    ("phases", "expected"),
    [
        ((TrialPhase.EARLY_PHASE_1,), ClaimStatus.PHASE_1),
        ((TrialPhase.PHASE_3,), ClaimStatus.PHASE_3),
        ((TrialPhase.PHASE_4,), ClaimStatus.PHASE_3),
        ((TrialPhase.NOT_APPLICABLE,), ClaimStatus.TRIAL_REGISTERED),
        ((), ClaimStatus.TRIAL_REGISTERED),
    ],
)
def test_started_trial_maps_its_registered_phase_to_a_stage(phases, expected):
    assert result(trial("NCT1", phases, STARTED)).status is expected


def test_completed_trial_with_no_recorded_start_still_counts_as_started():
    """Some registries give no actual start date; completion implies one."""
    events = trial("NCT1", PHASE_1, TrialState.COMPLETED)

    assert result(events).status is ClaimStatus.PHASE_1


def test_suspended_trial_with_no_recorded_start_has_not_started():
    events = trial("NCT1", PHASE_1, TrialState.SUSPENDED)

    assert result(events).status is ClaimStatus.TRIAL_REGISTERED


def test_furthest_started_trial_wins_over_an_unstarted_later_phase():
    events = trial("NCT1", PHASE_1, STARTED) + trial("NCT2", PHASE_3)

    assert result(events).status is ClaimStatus.PHASE_1


# --- claims without standing trials ----------------------------------------


def test_only_trial_failed_is_failed():
    """Scenario: Only trial failed"""
    events = trial("NCT1", PHASE_2, STARTED, TrialState.COMPLETED)

    assert result(events, (flag_on(events),)).status is ClaimStatus.FAILED


def test_every_trial_terminated_is_terminated():
    """Scenario: Every trial terminated"""
    events = trial("NCT1", PHASE_1, STARTED, TrialState.TERMINATED) + trial(
        "NCT2", PHASE_2, STARTED, TrialState.TERMINATED
    )

    assert result(events).status is ClaimStatus.TERMINATED


def test_withdrawn_trial_is_not_standing():
    events = trial("NCT1", PHASE_1, TrialState.WITHDRAWN)

    assert result(events).status is ClaimStatus.TERMINATED


def test_no_trials_is_preclinical_only():
    """Scenario: No trials"""
    assert result([paper(), paper(doi="10.1000/second")]).status is ClaimStatus.PRECLINICAL_ONLY


def test_failed_trial_and_later_standing_trial_is_the_standing_stage():
    """Scenario: Failed trial and a later standing trial"""
    failed = trial("NCT1", PHASE_2, STARTED, TrialState.COMPLETED)
    events = failed + trial("NCT2", PHASE_3, STARTED)

    assert result(events, (flag_on(failed),)).status is ClaimStatus.PHASE_3


def test_flag_resting_on_an_unapproved_event_does_not_count():
    events = trial("NCT1", PHASE_2, STARTED, TrialState.COMPLETED)
    report = evidence(
        EventType.TRIAL_RESULTS_POSTED, "NCT1", date(2020, 12, 1), review_state=ReviewState.PENDING
    )

    status = result([*events, report], (Flag("NCT1", report.id),)).status

    assert status is ClaimStatus.PHASE_2


# --- approved and retracted ------------------------------------------------

ORIGIN_DOI = "10.1000/origin"


def regulatory_decision(outcome: RegulatoryOutcome, on: date = date(2020, 6, 1)) -> Evidence:
    return evidence(
        EventType.REGULATORY_DECISION, "regulator/notice-1", on, regulatory_outcome=outcome
    )


def retraction(doi: str, on: date = date(2020, 6, 1)) -> Evidence:
    return evidence(EventType.RETRACTION, doi, on)


def test_approval_with_a_terminated_trial_is_approved():
    """Scenario: Approval with a terminated trial"""
    events = trial("NCT1", PHASE_3, STARTED, TrialState.TERMINATED)
    events.append(regulatory_decision(RegulatoryOutcome.APPROVED))

    assert result(events).status is ClaimStatus.APPROVED


def test_refusal_does_not_make_a_claim_approved():
    events = trial("NCT1", PHASE_3, STARTED, TrialState.COMPLETED)
    events.append(regulatory_decision(RegulatoryOutcome.REFUSED))

    assert result(events).status is ClaimStatus.PHASE_3


def test_origin_paper_retracted_is_retracted():
    """Scenario: Origin paper retracted"""
    events = [*trial("NCT1", PHASE_1, STARTED), retraction(ORIGIN_DOI)]

    status = result(events, origin_paper_ids=frozenset({ORIGIN_DOI})).status

    assert status is ClaimStatus.RETRACTED


def test_follow_up_paper_retracted_leaves_status_unchanged():
    """Scenario: Follow-up paper retracted"""
    events = trial("NCT1", PHASE_1, STARTED)
    with_retraction = [*events, retraction("10.1000/followup")]

    before = result(events, origin_paper_ids=frozenset({ORIGIN_DOI})).status
    after = result(with_retraction, origin_paper_ids=frozenset({ORIGIN_DOI})).status

    assert before is after is ClaimStatus.PHASE_1


def test_retraction_outranks_approval():
    events = [regulatory_decision(RegulatoryOutcome.APPROVED), retraction(ORIGIN_DOI)]

    status = result(events, origin_paper_ids=frozenset({ORIGIN_DOI})).status

    assert status is ClaimStatus.RETRACTED


def test_origin_paper_is_matched_whatever_the_letter_case_of_its_doi():
    events = [retraction("10.1000/ORIGIN")]

    status = result(events, origin_paper_ids=frozenset({ORIGIN_DOI})).status

    assert status is ClaimStatus.RETRACTED


# --- no-signal overlay -----------------------------------------------------


def test_quiet_preclinical_claim_carries_the_overlay():
    """Scenario: Quiet preclinical claim"""
    outcome = result([paper(on=date(2020, 3, 1))], as_of=date(2024, 5, 1))

    assert (outcome.status, outcome.overlay_years) == (ClaimStatus.PRECLINICAL_ONLY, 4)


def test_quiet_period_starts_at_the_report_when_the_records_are_older():
    """Scenario: Record older than the report"""
    # A trial registered years before the news report: the report is the latest signal.
    events = trial("NCT1", PHASE_1, registered_on=date(2013, 3, 20))

    outcome = result(events, first_reported_date=date(2018, 9, 11), as_of=date(2026, 11, 11))

    assert (outcome.status, outcome.overlay_years) == (ClaimStatus.TRIAL_REGISTERED, 8)


def test_report_within_the_quiet_period_means_no_overlay_despite_old_records():
    events = trial("NCT1", PHASE_1, registered_on=date(2013, 3, 20))

    outcome = result(events, first_reported_date=date(2025, 6, 1), as_of=date(2026, 11, 11))

    assert outcome.overlay_years is None


def test_recent_event_means_no_overlay():
    """Scenario: Recent event"""
    events = trial("NCT1", PHASE_1, STARTED, registered_on=date(2023, 1, 1))

    outcome = result(events, as_of=date(2024, 4, 1))

    assert (outcome.status, outcome.overlay_years) == (ClaimStatus.PHASE_1, None)


def test_terminal_status_never_carries_the_overlay():
    """Scenario: Terminal status"""
    events = [regulatory_decision(RegulatoryOutcome.APPROVED, on=date(2014, 1, 1))]

    outcome = result(events, as_of=date(2024, 1, 1))

    assert (outcome.status, outcome.overlay_years) == (ClaimStatus.APPROVED, None)


@pytest.mark.parametrize(
    ("as_of", "expected"),
    [
        (date(2023, 2, 28), None),  # one day short of three years
        (date(2023, 3, 1), 3),  # exactly three years
        (date(2026, 2, 28), 5),  # whole years only
    ],
)
def test_overlay_starts_at_three_whole_years(as_of, expected):
    outcome = result(trial("NCT1", PHASE_1, registered_on=date(2020, 3, 1)), as_of=as_of)

    assert (outcome.status, outcome.overlay_years) == (ClaimStatus.TRIAL_REGISTERED, expected)


def test_claim_with_no_events_is_measured_from_its_first_reported_date():
    outcome = result([], first_reported_date=date(2018, 6, 1), as_of=date(2024, 6, 1))

    assert (outcome.status, outcome.overlay_years) == (ClaimStatus.PRECLINICAL_ONLY, 6)


def test_claim_with_no_events_and_no_first_reported_date_has_no_overlay():
    assert result([], first_reported_date=None, as_of=date(2030, 1, 1)).overlay_years is None


def test_unapproved_events_do_not_reset_the_quiet_period():
    events = [
        paper(on=date(2019, 1, 1)),
        evidence(
            EventType.FOLLOWUP_PAPER,
            "10.1000/pending",
            date(2023, 12, 1),
            review_state=ReviewState.PENDING,
        ),
    ]

    assert result(events, as_of=date(2024, 1, 1)).overlay_years == 5


def test_threshold_is_configurable():
    events = [paper(on=date(2022, 1, 1))]

    assert result(events, as_of=date(2024, 1, 1)).overlay_years is None
    assert result(events, as_of=date(2024, 1, 1), no_signal_years=2).overlay_years == 2


@pytest.mark.parametrize("ending", [TrialState.TERMINATED, None])
def test_failed_and_terminated_claims_carry_no_overlay(ending):
    events = trial("NCT1", PHASE_2, STARTED, ending or TrialState.COMPLETED)
    flags = () if ending else (flag_on(events),)

    outcome = result(events, flags, as_of=date(2030, 1, 1))

    assert outcome.status in {ClaimStatus.TERMINATED, ClaimStatus.FAILED}
    assert outcome.overlay_years is None


# --- explanation -----------------------------------------------------------


def ids(events: list[Evidence]) -> tuple[int, ...]:
    return tuple(event.id for event in events)


def test_phase_2_claim_is_explained_by_its_trial_events():
    """Scenario: Phase 2 claim"""
    deciding = trial("NCT1", PHASE_2, STARTED)

    outcome = result([*deciding, paper()])

    assert outcome.explaining_event_ids == ids(deciding)


def test_stage_is_explained_only_by_the_trials_that_reached_it():
    earlier = trial("NCT1", PHASE_1, STARTED, TrialState.COMPLETED)
    deciding = trial("NCT2", PHASE_2, STARTED, registered_on=date(2020, 6, 1))

    assert result(earlier + deciding).explaining_event_ids == ids(deciding)


def test_trial_registered_is_explained_by_every_standing_trial():
    first = trial("NCT1", PHASE_1)
    second = trial("NCT2", PHASE_2, registered_on=date(2020, 2, 1))

    assert result(first + second).explaining_event_ids == ids(first + second)


def test_failed_is_explained_by_the_failed_trial_and_the_report_behind_its_flag():
    failed = trial("NCT1", PHASE_2, STARTED, TrialState.COMPLETED)
    report = evidence(EventType.FOLLOWUP_PAPER, "10.1000/results", date(2021, 6, 1))

    outcome = result([*failed, report], (Flag("NCT1", report.id),), as_of=date(2022, 1, 1))

    assert outcome.status is ClaimStatus.FAILED
    assert outcome.explaining_event_ids == ids([*failed, report])


def test_terminated_is_explained_by_every_trial():
    first = trial("NCT1", PHASE_1, STARTED, TrialState.TERMINATED)
    second = trial("NCT2", PHASE_2, TrialState.WITHDRAWN, registered_on=date(2020, 2, 1))

    outcome = result(first + second)

    assert sorted(outcome.explaining_event_ids) == sorted(ids(first + second))


def test_approved_is_explained_by_the_approval():
    approval = regulatory_decision(RegulatoryOutcome.APPROVED)

    outcome = result([*trial("NCT1", PHASE_3, STARTED), approval])

    assert outcome.explaining_event_ids == (approval.id,)


def test_retracted_is_explained_by_the_retraction():
    notice = retraction(ORIGIN_DOI)

    outcome = result(
        [*trial("NCT1", PHASE_1, STARTED), notice], origin_paper_ids=frozenset({ORIGIN_DOI})
    )

    assert outcome.explaining_event_ids == (notice.id,)


def test_preclinical_only_has_no_explaining_events():
    assert result([paper()]).explaining_event_ids == ()


def test_explanation_lists_events_oldest_first():
    later = trial("NCT2", PHASE_1, registered_on=date(2020, 6, 1))
    earlier = trial("NCT1", PHASE_1, registered_on=date(2020, 1, 1))

    assert result(later + earlier).explaining_event_ids == ids(earlier + later)


# --- purity ----------------------------------------------------------------


def test_status_package_reaches_no_database_network_or_clock():
    """The rules must stay a pure function of their arguments."""
    allowed = {"collections.abc", "dataclasses", "datetime", "thenwhat.domain"}
    package = Path(rules.__file__).parent

    for source_file in package.glob("*.py"):
        source = source_file.read_text()
        imported = {
            name
            for node in ast.walk(ast.parse(source))
            for name in (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
                if isinstance(node, ast.ImportFrom)
                else []
            )
        }
        assert imported <= allowed | {"thenwhat.status.rules"}, source_file.name
        assert "today(" not in source and "now(" not in source, source_file.name
