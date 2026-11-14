"""The backfill commands: wiring, messages and exit codes. The rules are tested in
test_work_ledger.py, test_source_allowances.py, test_registry_corpus.py and
test_news_search.py."""

from collections.abc import Generator
from contextlib import contextmanager

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from backfill_support import NOW, add_trials, same_session
from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.mediacloud import Story
from thenwhat.backfill.news_search import query_for
from thenwhat.cli import app
from thenwhat.cli.backfill import _hours
from thenwhat.config import SourceAllowance
from thenwhat.db.models import ArticleLead, RegistryTrial, WorkEntry
from thenwhat.sources.clinicaltrials import ClinicalTrials


class Index:
    """A news index that finds one article for every trial whose number is even."""

    name = "mediacloud"

    def __init__(self) -> None:
        self.requests_made = 0

    def search(self, query: str, *, limit: int) -> list[Story]:
        self.requests_made += 1
        for number in range(0, 20, 2):
            if query == query_for(f"drug {number}", "condition"):
                url = f"https://www.theguardian.com/science/synthetic-{number}"
                return [Story(url, "theguardian.com", "Synthetic headline", NOW.date(), {})]
        return []


@pytest.fixture
def run(session: Session, monkeypatch: pytest.MonkeyPatch, fake_time):
    @contextmanager
    def test_session() -> Generator[Session]:
        yield session
        session.flush()

    monkeypatch.setattr("thenwhat.cli.session.open_session", test_session)
    monkeypatch.setattr(
        "thenwhat.cli.backfill.make_allowances",
        lambda settings: Allowances(same_session(session), settings.allowances(), fake_time),
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("CONTACT_EMAIL", "ops@thenwhat.test")
    monkeypatch.delenv("MEDIACLOUD_API_KEY", raising=False)
    monkeypatch.delenv("SOURCE_ALLOWANCES", raising=False)
    runner = CliRunner()

    def invoke(*arguments: str) -> Result:
        return runner.invoke(app, ["backfill", *arguments])

    return invoke


@pytest.fixture
def index(monkeypatch: pytest.MonkeyPatch) -> Index:
    index = Index()
    monkeypatch.setattr("thenwhat.cli.backfill.make_client", lambda step, settings, shared: index)
    return index


# --- steps and plan ----------------------------------------------------------------------


def test_steps_lists_each_step_with_its_source(run):
    """Scenario: Listing steps"""
    result = run("steps")

    assert result.exit_code == 0, result.output
    assert "news_search  version 1  records: registry_trial  source: mediacloud" in result.output
    assert "requests per record: 1" in result.output


def test_plan_reports_what_is_due_and_sends_nothing(run, session: Session, index: Index):
    """Scenario: Planning"""
    add_trials(session, 6)
    add_trials(session, 2, registry="unnamed", name=None)
    run("run", "news_search", "--limit", "2")
    sent = index.requests_made

    result = run("plan")

    assert result.exit_code == 0, result.output
    assert "in scope: 6 of 8 registry_trial records" in result.output
    assert "done: 1  nothing found: 1  failed: 0  due: 4" in result.output
    assert "need 4 requests, about 2 minutes" in result.output
    assert "mediacloud: 4,000 requests in 168 hours, 30 seconds apart" in result.output
    assert index.requests_made == sent


def test_plan_says_how_many_records_the_allowance_left_covers(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: More work than allowance"""
    monkeypatch.setenv(
        "SOURCE_ALLOWANCES",
        '{"mediacloud": {"requests": 4, "period_hours": 168, "interval_seconds": 30}}',
    )
    add_trials(session, 10)

    result = run("plan")

    assert "the allowance left covers 4 of the 10 due records" in result.output
    assert "the rest needs 2 more periods of 168 hours" in result.output


def test_a_large_job_is_stated_in_hours():
    """Scenario: Planning, with 43,000 records at one request every five seconds"""
    every_five_seconds = SourceAllowance(requests=50000, period_hours=24, interval_seconds=5)

    assert _hours(43000, every_five_seconds) == "about 60 hours"


# --- run ---------------------------------------------------------------------------------


def test_a_limited_run_reports_what_remains_and_a_restart_repeats_nothing(
    run, session: Session, index: Index
):
    """Scenarios: Limited run, Restart"""
    add_trials(session, 5)

    first = run("run", "news_search", "--limit", "2")
    second = run("run", "news_search")

    assert first.exit_code == 0, first.output
    assert "news_search: 1 done, 1 found nothing, 0 failed; 3 still due." in first.output
    assert "news_search: 2 done, 1 found nothing, 0 failed; 0 still due." in second.output
    assert index.requests_made == 5
    assert len(session.scalars(select(WorkEntry)).all()) == 5
    assert len(session.scalars(select(ArticleLead)).all()) == 3


def test_an_unknown_step_lists_the_steps_and_processes_nothing(run, session: Session):
    """Scenario: Unknown step"""
    add_trials(session, 2)

    result = run("run", "no-such-step")

    assert result.exit_code == 1
    assert "No step is named 'no-such-step'. Steps: news_search." in result.output
    assert session.scalars(select(WorkEntry)).all() == []


def test_a_run_without_the_news_key_is_refused_before_any_record(run, session: Session):
    add_trials(session, 2)

    result = run("run", "news_search")

    assert result.exit_code == 1
    assert "MEDIACLOUD_API_KEY is not set" in result.output
    assert session.scalars(select(WorkEntry)).all() == []


# --- load-trials ---------------------------------------------------------------------------


def test_load_trials_stores_the_registrys_pages(
    run, session: Session, monkeypatch: pytest.MonkeyPatch, fake_time, fixture_json
):
    first = fixture_json("clinicaltrials/list_page_1.json")
    second = fixture_json("clinicaltrials/list_page_2.json")

    def registry(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=second if "pageToken" in request.url.params else first)

    monkeypatch.setattr(
        "thenwhat.cli.backfill.make_registry",
        lambda lookups, settings: ClinicalTrials(
            lookups,
            contact_email=settings.contact_email,
            transport=httpx.MockTransport(registry),
            time=fake_time,
        ),
    )

    result = run("load-trials")

    assert result.exit_code == 0, result.output
    assert "Loaded 4 trials in 2 requests: 4 new, 0 already stored." in result.output
    assert len(session.scalars(select(RegistryTrial)).all()) == 4


def test_load_trials_without_a_contact_address_sends_nothing(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("CONTACT_EMAIL")

    result = run("load-trials")

    assert result.exit_code == 1
    assert "CONTACT_EMAIL is not set, so no request was sent." in result.output
    assert session.scalars(select(RegistryTrial)).all() == []


# --- leads ---------------------------------------------------------------------------------


def test_leads_reports_the_hit_rate_by_outlet_kind(run, session: Session, index: Index):
    add_trials(session, 4)
    run("run", "news_search")

    result = run("leads")

    assert result.exit_code == 0, result.output
    assert "2 of 4 searched trials (50%) have at least one article lead." in result.output
    assert "2 (50%) have one from general news" in result.output
    assert "0 (0%) have one from health or clinical trade press" in result.output


def test_leads_with_nothing_searched_says_so(run, session: Session):
    add_trials(session, 2)

    result = run("leads")

    assert result.exit_code == 0
    assert "No trial has been searched yet." in result.output
