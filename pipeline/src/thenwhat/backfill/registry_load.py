"""Loading trials from a registry in bulk, independently of any claim.
Behavior: openspec registry-corpus."""

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.errors import SourceStop
from thenwhat.backfill.ledger import mark_changed
from thenwhat.backfill.steps import Step
from thenwhat.backfill.trial_names import indication_words, name_under_test
from thenwhat.db.models import RegistryLoad, RegistryTrial
from thenwhat.sources.base import SourceThrottled
from thenwhat.sources.clinicaltrials import TrialPage

OpenSession = Callable[[], AbstractContextManager[Session]]

RECORD_KIND = "registry_trial"
# The registry's expression for the trials the first backfill starts from.
_DRUG_OR_BIOLOGICAL = "(AREA[InterventionType]DRUG OR AREA[InterventionType]BIOLOGICAL)"
PHASE_3_DRUG_OR_BIOLOGICAL = (
    f"AREA[StudyType]INTERVENTIONAL AND AREA[Phase]PHASE3 AND {_DRUG_OR_BIOLOGICAL}"
)
# Trials under way now in phase 2 or 3: recruiting, not yet recruiting, enrolling by
# invitation, or active and no longer recruiting. The registry counted 23,548 of them
# on 2026-11-16, 17,373 in phase 2 and 7,331 in phase 3 (a trial in both is counted in
# each).
ACTIVE_PHASE_2_OR_3 = (
    "AREA[StudyType]INTERVENTIONAL AND (AREA[Phase]PHASE2 OR AREA[Phase]PHASE3) AND "
    "AREA[OverallStatus](RECRUITING OR ACTIVE_NOT_RECRUITING OR ENROLLING_BY_INVITATION "
    f"OR NOT_YET_RECRUITING) AND {_DRUG_OR_BIOLOGICAL}"
)
# Every interventional study the registry holds, of any phase, state and kind of
# intervention. Observational studies and expanded access records are not trials and are
# left out.
INTERVENTIONAL = "AREA[StudyType]INTERVENTIONAL"
# The sets of trials a load can be asked for by name. A set is only which trials are
# stored: it says nothing of how any of them turned out.
TRIAL_SETS = {
    "phase-3": PHASE_3_DRUG_OR_BIOLOGICAL,
    "active-phase-2-3": ACTIVE_PHASE_2_OR_3,
    "interventional": INTERVENTIONAL,
}


class UnknownTrialSet(Exception):
    """No set of trials has the name given."""


def condition_of(name: str) -> str:
    """The registry's expression for a named set of trials."""
    if name not in TRIAL_SETS:
        raise UnknownTrialSet(
            f"No set of trials is named '{name}'. Sets: {', '.join(sorted(TRIAL_SETS))}."
        )
    return TRIAL_SETS[name]


class TrialList(Protocol):
    name: str

    def list_page(
        self,
        condition: str,
        *,
        page_token: str | None = None,
        updated_since: date | None = None,
    ) -> TrialPage: ...


@dataclass(slots=True)
class LoadReport:
    requests: int = 0
    added: int = 0
    updated: int = 0
    # The date changes were asked from, or None for a full load.
    changes_since: date | None = None
    # Why the load ended before its last page, when the registry may not be asked now.
    stopped: str | None = None


def _struct(status: dict[str, Any], key: str) -> dict[str, Any]:
    return status.get(key) or {}


def _posted(status: dict[str, Any], key: str) -> date | None:
    """A date the registry posted something, which it always gives as a full day. Any
    other form is left empty here and kept in the raw record."""
    value = _struct(status, key).get("date")
    try:
        return date.fromisoformat(value) if value and len(value) == 10 else None
    except ValueError:
        return None


def trial_fields(study: dict[str, Any]) -> dict[str, Any]:
    """The columns of a registry trial, read from the registry's own record. A field the
    registry leaves out is stored empty: nothing is worked out from other fields."""
    protocol = study["protocolSection"]
    status = protocol.get("statusModule", {})
    lead_sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    interventions = [
        {
            "type": intervention.get("type"),
            "name": intervention.get("name"),
            "otherNames": intervention.get("otherNames", []),
        }
        for intervention in protocol.get("armsInterventionsModule", {}).get("interventions", [])
    ]
    conditions = protocol.get("conditionsModule", {}).get("conditions", [])
    return {
        "external_id": protocol["identificationModule"]["nctId"],
        "title": protocol["identificationModule"].get("briefTitle") or "",
        "conditions": conditions,
        "interventions": interventions,
        "phases": protocol.get("designModule", {}).get("phases", []),
        "overall_status": status.get("overallStatus"),
        "start_date": _struct(status, "startDateStruct").get("date"),
        "start_date_type": _struct(status, "startDateStruct").get("type"),
        "sponsor_class": lead_sponsor.get("class"),
        "search_name": name_under_test(interventions),
        "search_indication": indication_words(conditions),
        "last_update_posted": _posted(status, "lastUpdatePostDateStruct"),
        "study_first_posted": _posted(status, "studyFirstPostDateStruct"),
        "primary_completion_date": _struct(status, "primaryCompletionDateStruct").get("date"),
        "primary_completion_date_type": (
            _struct(status, "primaryCompletionDateStruct").get("type")
        ),
        "completion_date": _struct(status, "completionDateStruct").get("date"),
        "completion_date_type": _struct(status, "completionDateStruct").get("type"),
        "results_first_posted": _posted(status, "resultsFirstPostDateStruct"),
        "has_results": study.get("hasResults"),
        "acronym": protocol["identificationModule"].get("acronym"),
        # A sponsor who is a person is not named in a column.
        "lead_sponsor_name": (
            None if lead_sponsor.get("class") == INDIVIDUAL else lead_sponsor.get("name")
        ),
    }


INDIVIDUAL = "INDIVIDUAL"


def without_people(study: dict[str, Any]) -> dict[str, Any]:
    """The registry's record as stored: exactly as the registry gave it, except that the
    name of a lead sponsor or collaborator whose class is INDIVIDUAL is removed. That is
    the one thing removed, because the project keeps no personal data beyond subscriber
    emails and such a name is a person's. The class is kept, so the record still says a
    person sponsors or collaborates on the trial. The record given is not changed."""
    sponsors = study.get("protocolSection", {}).get("sponsorCollaboratorsModule")
    if not sponsors:
        return study

    def unnamed(party: dict[str, Any]) -> dict[str, Any]:
        if party.get("class") != INDIVIDUAL:
            return party
        return {key: value for key, value in party.items() if key != "name"}

    kept = dict(sponsors)
    if isinstance(sponsors.get("leadSponsor"), dict):
        kept["leadSponsor"] = unnamed(sponsors["leadSponsor"])
    if isinstance(sponsors.get("collaborators"), list):
        kept["collaborators"] = [unnamed(party) for party in sponsors["collaborators"]]
    protocol = {**study["protocolSection"], "sponsorCollaboratorsModule": kept}
    return {**study, "protocolSection": protocol}


def store_trial(
    session: Session,
    steps: Sequence[Step],
    registry: str,
    study: dict[str, Any],
    fetched_at: datetime,
) -> bool:
    """Store a trial once per registry and identifier, updating it in place when it is
    already there. A trial whose fields changed becomes due again for the steps that
    read those fields. Returns whether the trial is new."""
    fields = trial_fields(study)
    trial = session.scalars(
        select(RegistryTrial).where(
            RegistryTrial.registry_name == registry,
            RegistryTrial.external_id == fields["external_id"],
        )
    ).one_or_none()
    is_new = trial is None
    if trial is None:
        trial = RegistryTrial(registry_name=registry)
        session.add(trial)
    for column, value in fields.items():
        setattr(trial, column, value)
    trial.raw_payload = without_people(study)
    trial.fetched_at = fetched_at
    session.flush()
    if not is_new:
        mark_changed(session, steps, RECORD_KIND, trial)
    return is_new


def load_trials(
    open_session: OpenSession,
    registry: TrialList,
    steps: Sequence[Step],
    *,
    condition: str,
    changes_only: bool,
    now: Callable[[], datetime],
    before_request: Callable[[], None] | None = None,
    refused: Callable[[float | None], SourceStop] | None = None,
) -> LoadReport:
    """Load every trial that meets the condition, a page per request and a transaction
    per page.

    With `changes_only`, only trials the registry updated since the previous completed
    load of the same condition are asked for; when there is no such load, everything is.
    A load that stops part way is simply started again: trials already stored are updated
    in place, so each ends up stored once. `before_request` is called ahead of every
    request, to claim it against the registry's allowance. `refused` is called when the
    registry kept answering "too many requests", with the wait it stated, to record the
    pause for every process; it returns the stop to report. When the registry may not be
    asked now (its allowance is used up, or it said "too many requests"), the load stops
    with what it stored so far and says why; it is not recorded as completed, so the next
    load asks again from the same date.
    """
    started = now()
    report = LoadReport()
    if changes_only:
        with open_session() as session:
            previous = session.get(RegistryLoad, (registry.name, condition))
            if previous is not None:
                report.changes_since = previous.loaded_from.date()
    token: str | None = None
    while True:
        try:
            if before_request is not None:
                before_request()
            page = registry.list_page(
                condition, page_token=token, updated_since=report.changes_since
            )
        except SourceStop as stop:
            report.stopped = str(stop)
            return report
        except SourceThrottled as throttled:
            if refused is None:
                raise
            report.stopped = str(refused(throttled.retry_after))
            return report
        report.requests += 1
        with open_session() as session:
            for study in page.studies:
                if store_trial(session, steps, registry.name, study, page.fetched_at):
                    report.added += 1
                else:
                    report.updated += 1
        token = page.next_token
        if not token:
            break
    with open_session() as session:
        state = session.get(RegistryLoad, (registry.name, condition))
        if state is None:
            state = RegistryLoad(registry_name=registry.name, condition=condition)
            session.add(state)
        # Changes are next asked from the start of this load, so that nothing the
        # registry updated while it ran is missed.
        state.loaded_from = started
        state.completed_at = now()
    return report
