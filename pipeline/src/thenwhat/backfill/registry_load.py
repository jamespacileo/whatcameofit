"""Loading trials from a registry in bulk, independently of any claim.
Behavior: openspec registry-corpus."""

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thenwhat.backfill.ledger import mark_changed
from thenwhat.backfill.steps import Step
from thenwhat.backfill.trial_names import indication_words, name_under_test
from thenwhat.db.models import RegistryLoad, RegistryTrial
from thenwhat.sources.clinicaltrials import TrialPage

OpenSession = Callable[[], AbstractContextManager[Session]]

RECORD_KIND = "registry_trial"
# The registry's expression for the trials the first backfill starts from.
PHASE_3_DRUG_OR_BIOLOGICAL = (
    "AREA[StudyType]INTERVENTIONAL AND AREA[Phase]PHASE3 AND "
    "(AREA[InterventionType]DRUG OR AREA[InterventionType]BIOLOGICAL)"
)


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


def trial_fields(study: dict[str, Any]) -> dict[str, Any]:
    """The columns of a registry trial, read from the registry's own record."""
    protocol = study["protocolSection"]
    status = protocol.get("statusModule", {})
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
        "start_date": (status.get("startDateStruct") or {}).get("date"),
        "sponsor_class": (
            protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {}).get("class")
        ),
        "search_name": name_under_test(interventions),
        "search_indication": indication_words(conditions),
    }


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
    trial.raw_payload = study
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
) -> LoadReport:
    """Load every trial that meets the condition, a page per request and a transaction
    per page.

    With `changes_only`, only trials the registry updated since the previous completed
    load of the same condition are asked for; when there is no such load, everything is.
    A load that stops part way is simply started again: trials already stored are updated
    in place, so each ends up stored once. `before_request` is called ahead of every
    request, to claim it against the registry's allowance.
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
        if before_request is not None:
            before_request()
        page = registry.list_page(condition, page_token=token, updated_since=report.changes_since)
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
