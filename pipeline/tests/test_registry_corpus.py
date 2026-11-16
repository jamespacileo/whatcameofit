"""Loading registry trials in bulk, replaying two recorded pages of the registry's list.
Scenario names are from openspec registry-corpus."""

from datetime import date, timedelta

import httpx
import pytest
from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from backfill_support import DemoStep, committed_sessions, remove_committed, same_session
from thenwhat.backfill.errors import AllowanceUsedUp, SourcePaused
from thenwhat.backfill.ledger import count, record_outcome
from thenwhat.backfill.link_screen import LinkScreen
from thenwhat.backfill.news_search import NewsSearch
from thenwhat.backfill.registry_load import load_trials, trial_fields
from thenwhat.backfill.runner import run_step
from thenwhat.db.models import RegistryLoad, RegistryTrial, WorkEntry
from thenwhat.domain import WorkOutcome
from thenwhat.export.build import build_export
from thenwhat.sources.base import MissingContact
from thenwhat.sources.clinicaltrials import ClinicalTrials

CONDITION = "AREA[Phase]PHASE3 AND AREA[Condition]Migraine"
REGISTRY = "clinicaltrials.gov"


class Registry:
    """Serves the two recorded pages and remembers each request's parameters."""

    def __init__(
        self, fixture_json, *, fail_on_second_page: bool = False, throttle_second_page=False
    ) -> None:
        self.first = fixture_json("clinicaltrials/list_page_1.json")
        self.second = fixture_json("clinicaltrials/list_page_2.json")
        self.fail_on_second_page = fail_on_second_page
        self.throttle_second_page = throttle_second_page
        self.asked: list[dict[str, str]] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        self.asked.append(params)
        if "pageToken" not in params:
            return httpx.Response(200, json=self.first)
        if self.throttle_second_page:
            return httpx.Response(429, headers={"Retry-After": "120"}, text="slow down")
        if self.fail_on_second_page:
            return httpx.Response(400, text="bad request")
        return httpx.Response(200, json=self.second)


def client(session: Session, fake_time, registry: Registry, contact="ops@thenwhat.test"):
    return ClinicalTrials(
        session, contact_email=contact, transport=httpx.MockTransport(registry), time=fake_time
    )


def load(session: Session, fake_time, registry: Registry, steps=(), **options):
    options.setdefault("changes_only", False)
    return load_trials(
        same_session(session),
        client(session, fake_time, registry),
        list(steps),
        condition=CONDITION,
        now=fake_time.now,
        **options,
    )


def stored(session: Session) -> list[RegistryTrial]:
    return list(session.scalars(select(RegistryTrial).order_by(RegistryTrial.external_id)))


def test_a_load_stores_every_trial_with_its_fields_payload_and_fetch_time(
    session: Session, fake_time, fixture_json
):
    """Scenarios: A trial is loaded, Loading phase 3 drug trials"""
    registry = Registry(fixture_json)

    report = load(session, fake_time, registry)

    trials = stored(session)
    assert (report.requests, report.added, report.updated) == (2, 4, 0)
    assert [trial.external_id for trial in trials] == [
        "NCT04946734",
        "NCT07792681",
        "NCT07816367",
        "NCT07835152",
    ]
    assert registry.asked[0]["filter.advanced"] == CONDITION
    assert "pageToken" in registry.asked[1]
    elismetrep = trials[2]
    assert elismetrep.registry_name == REGISTRY
    assert elismetrep.conditions == ["Migraine"]
    assert [entry["name"] for entry in elismetrep.interventions] == ["Elismetrep", "Placebo"]
    assert (elismetrep.phases, elismetrep.sponsor_class) == (["PHASE3"], "INDUSTRY")
    assert elismetrep.start_date == "2026-10-02"
    assert (elismetrep.search_name, elismetrep.search_indication) == ("Elismetrep", "migraine")
    assert elismetrep.raw_payload["protocolSection"]["identificationModule"]["nctId"] == (
        "NCT07816367"
    )
    assert elismetrep.fetched_at == fake_time.now()


def test_a_repeat_load_updates_in_place(session: Session, fake_time, fixture_json):
    """Scenario: A trial is loaded again"""
    load(session, fake_time, Registry(fixture_json))
    fake_time.advance(timedelta(days=1))
    second_load_started = fake_time.now()

    report = load(session, fake_time, Registry(fixture_json))

    assert (report.added, report.updated) == (0, 4)
    assert len(stored(session)) == 4
    assert all(trial.fetched_at >= second_load_started for trial in stored(session))


def test_a_load_that_stopped_on_the_second_page_finishes_when_started_again(
    session: Session, fake_time, fixture_json
):
    """Scenario: Interrupted load"""
    with pytest.raises(Exception, match="refused the request"):
        load(session, fake_time, Registry(fixture_json, fail_on_second_page=True))
    assert len(stored(session)) == 3
    assert session.get(RegistryLoad, (REGISTRY, CONDITION)) is None

    load(session, fake_time, Registry(fixture_json))

    assert len(stored(session)) == 4
    assert session.get(RegistryLoad, (REGISTRY, CONDITION)) is not None


def test_loading_changes_asks_only_for_trials_updated_since_the_last_load(
    session: Session, fake_time, fixture_json
):
    """Scenario: Second load"""
    first_load_day = fake_time.now().date()
    load(session, fake_time, Registry(fixture_json))
    fake_time.advance(timedelta(days=7))
    registry = Registry(fixture_json)

    report = load(session, fake_time, registry, changes_only=True)

    assert report.changes_since == first_load_day
    assert registry.asked[0]["filter.advanced"] == (
        f"({CONDITION}) AND AREA[LastUpdatePostDate]RANGE[{first_load_day.isoformat()},MAX]"
    )


def test_loading_changes_works_when_every_page_is_its_own_transaction(
    session: Session, engine: Engine, fake_time, fixture_json
):
    """As the command runs it: each read and each page commits on its own connection."""
    condition = "AREA[Condition]Migraine AND committed"
    open_session = committed_sessions(engine)

    def load_committed(**options):
        return load_trials(
            open_session,
            client(session, fake_time, Registry(fixture_json)),
            [],
            condition=condition,
            now=fake_time.now,
            **options,
        )

    try:
        first_load_day = fake_time.now().date()
        load_committed(changes_only=False)
        fake_time.advance(timedelta(days=3))

        report = load_committed(changes_only=True)

        assert (report.changes_since, report.updated) == (first_load_day, 4)
    finally:
        with open_session() as cleanup:
            cleanup.execute(delete(RegistryLoad).where(RegistryLoad.condition == condition))
        remove_committed(engine, registry=REGISTRY, step="none", source="none")


def test_loading_changes_with_no_earlier_load_loads_everything(
    session: Session, fake_time, fixture_json
):
    registry = Registry(fixture_json)

    report = load(session, fake_time, registry, changes_only=True)

    assert report.changes_since is None and report.added == 4
    assert registry.asked[0]["filter.advanced"] == CONDITION


def test_a_trial_is_due_again_only_when_a_field_a_step_reads_changed(
    session: Session, fake_time, fixture_json
):
    """Scenarios: A trial gains an intervention name, Nothing a step uses changed"""
    step = DemoStep(registry=REGISTRY)
    load(session, fake_time, Registry(fixture_json), steps=[step])
    run_step(same_session(session), step, _Counting(), now=fake_time.now, attempt_limit=3)
    assert count(session, step, 3).due == 0

    changed = Registry(fixture_json)
    renamed = changed.second["studies"][0]["protocolSection"]
    renamed["armsInterventionsModule"]["interventions"][0]["name"] = "Elismetrep succinate"
    retitled = changed.first["studies"][0]["protocolSection"]
    retitled["identificationModule"]["briefTitle"] = "A new title"
    load(session, fake_time, changed, steps=[step])

    step.ran.clear()
    run_step(same_session(session), step, _Counting(), now=fake_time.now, attempt_limit=3)
    assert step.ran == ["NCT07816367"]


def test_the_wider_record_is_stored_as_the_registry_gives_it(fixture_json):
    """Scenarios: A trial with posted results, A field the registry leaves empty"""
    page = fixture_json("clinicaltrials/list_page_wide.json")
    by_id = {fields["external_id"]: fields for fields in map(trial_fields, page["studies"])}

    kudzu = by_id["NCT01596231"]
    assert kudzu["results_first_posted"] == date(2014, 10, 21)
    assert kudzu["has_results"] is True
    assert (kudzu["completion_date"], kudzu["completion_date_type"]) == ("2014-07", "ACTUAL")
    assert kudzu["primary_completion_date"] == "2013-05"
    assert kudzu["last_update_posted"] == date(2014, 10, 21)
    assert kudzu["study_first_posted"] == date(2012, 5, 10)
    assert (kudzu["acronym"], kudzu["lead_sponsor_name"]) == ("KUDZU", "Mclean Hospital")
    # The registry gives this start date no type, and none is supplied.
    assert (kudzu["start_date"], kudzu["start_date_type"]) == ("2010-05", None)

    elismetrep = by_id["NCT07816367"]
    assert (elismetrep["completion_date"], elismetrep["completion_date_type"]) == (
        "2027-12",
        "ESTIMATED",
    )
    assert elismetrep["start_date_type"] == "ACTUAL"
    # No results, no acronym: stored empty, not derived from the state or the dates.
    assert (elismetrep["has_results"], elismetrep["results_first_posted"]) == (False, None)
    assert elismetrep["acronym"] is None

    tide = by_id["NCT02586935"]
    assert (tide["overall_status"], tide["has_results"]) == ("COMPLETED", False)
    assert tide["last_update_posted"] == date(2025, 7, 16)


def test_a_sponsor_who_is_a_person_is_not_named_in_a_column(fixture_json):
    study = fixture_json("clinicaltrials/list_page_wide.json")["studies"][0]
    study["protocolSection"]["sponsorCollaboratorsModule"]["leadSponsor"] = {
        "name": "A made-up person",
        "class": "INDIVIDUAL",
    }

    fields = trial_fields(study)

    assert (fields["sponsor_class"], fields["lead_sponsor_name"]) == ("INDIVIDUAL", None)


def _widened(registry: Registry) -> Registry:
    """The same trials as the registry gives them with the wider record: every listing
    field as before, plus activity and results fields."""
    for page in (registry.first, registry.second):
        for study in page["studies"]:
            protocol = study["protocolSection"]
            protocol["statusModule"] |= {
                "lastUpdatePostDateStruct": {"date": "2026-11-12"},
                "studyFirstPostDateStruct": {"date": "2026-01-05"},
                "completionDateStruct": {"date": "2027-12", "type": "ESTIMATED"},
            }
            protocol["identificationModule"]["acronym"] = "MADE-UP"
            sponsors = protocol.setdefault("sponsorCollaboratorsModule", {})
            sponsors.setdefault("leadSponsor", {})["name"] = "A sponsor"
            study["hasResults"] = False
    return registry


def test_loading_the_wider_record_makes_no_trial_due_for_any_step(
    session: Session, fake_time, fixture_json
):
    """Scenario: The reload. The news search reads only the name and indication worked
    out from the listing fields; screening reads link leads, which a trial load never
    marks."""
    steps = [NewsSearch(time=fake_time), LinkScreen()]
    load(session, fake_time, Registry(fixture_json), steps=steps)
    news_search = steps[0]
    for trial in session.scalars(select(RegistryTrial).where(news_search.scope())):
        record_outcome(
            session, news_search, trial, WorkOutcome.DONE, requests_used=1, now=fake_time.now()
        )
    assert count(session, news_search, 3).due == 0

    fake_time.advance(timedelta(days=1))
    load(session, fake_time, _widened(Registry(fixture_json)), steps=steps)

    assert all(trial.last_update_posted == date(2026, 11, 12) for trial in stored(session))
    assert count(session, news_search, 3).due == 0
    assert not session.scalars(select(WorkEntry).where(WorkEntry.stale)).first()


def test_requests_are_claimed_before_they_are_sent(session: Session, fake_time, fixture_json):
    claimed: list[int] = []
    registry = Registry(fixture_json)

    load(session, fake_time, registry, before_request=lambda: claimed.append(len(registry.asked)))

    assert claimed == [0, 1]


def test_a_load_that_reaches_the_allowance_stops_with_what_it_stored(
    session: Session, fake_time, fixture_json
):
    """The allowance runs out after the first page: the load ends without an error, says
    why, keeps the first page's trials, and is not recorded as completed, so the next
    changes-only load asks from the same date."""
    registry = Registry(fixture_json)
    claims: list[int] = []

    def before_request() -> None:
        claims.append(1)
        if len(claims) > 1:
            raise AllowanceUsedUp("The allowance for clinicaltrials.gov is used up.")

    report = load(session, fake_time, registry, before_request=before_request)

    assert report.stopped == "The allowance for clinicaltrials.gov is used up."
    assert (report.requests, report.added, report.updated) == (1, 3, 0)
    assert len(registry.asked) == 1
    assert len(stored(session)) == 3
    assert session.get(RegistryLoad, (REGISTRY, CONDITION)) is None


def test_a_load_the_registry_asks_to_wait_records_the_pause_and_stops(
    session: Session, fake_time, fixture_json
):
    """The registry answers "too many requests" to the second page every time it is
    asked: the refusal is recorded with the wait it stated, the load ends without an
    error with the first page stored, and it is not recorded as completed."""
    registry = Registry(fixture_json, throttle_second_page=True)
    waits: list[float | None] = []

    def refused(wait: float | None) -> SourcePaused:
        waits.append(wait)
        return SourcePaused("clinicaltrials.gov said it was asked too often.")

    report = load(session, fake_time, registry, refused=refused)

    assert waits == [120.0]
    assert report.stopped == "clinicaltrials.gov said it was asked too often."
    assert (report.added, report.updated) == (3, 0)
    assert len(stored(session)) == 3
    assert session.get(RegistryLoad, (REGISTRY, CONDITION)) is None


def test_no_request_is_sent_without_a_contact_address(session: Session, fake_time, fixture_json):
    """Scenario: No contact address"""
    registry = Registry(fixture_json)
    source = client(session, fake_time, registry, contact=None)

    with pytest.raises(MissingContact, match="CONTACT_EMAIL"):
        load_trials(
            same_session(session),
            source,
            [],
            condition=CONDITION,
            changes_only=False,
            now=fake_time.now,
        )
    assert registry.asked == []


def test_the_export_is_the_same_before_and_after_a_load(session: Session, fake_time, fixture_json):
    """Scenario: Export after a load"""
    moment = fake_time.now()
    before = build_export(session, now=moment).model_dump_json()

    load(session, fake_time, Registry(fixture_json))

    assert len(stored(session)) == 4
    assert build_export(session, now=moment).model_dump_json() == before


class _Counting:
    def __init__(self) -> None:
        self.requests_made = 0
