"""The backfill commands: wiring, messages and exit codes. The rules are tested in
test_work_ledger.py, test_source_allowances.py, test_registry_corpus.py and
test_news_search.py."""

from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from backfill_support import NOW, ModelStep, QuietStep, add_trials, same_session
from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.mediacloud import Story
from thenwhat.backfill.news_search import query_for
from thenwhat.cli import app
from thenwhat.cli.backfill import _hours
from thenwhat.config import SourceAllowance
from thenwhat.db.models import (
    ArticleLead,
    LinkLead,
    LinkLeadLabel,
    LinkShare,
    LlmUsage,
    RegistryTrial,
    WorkEntry,
)
from thenwhat.domain import Decider
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


def test_a_step_that_asks_no_source_is_planned_and_run_without_an_allowance(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Planning a step that only reads the database"""
    step = QuietStep("quiet")
    monkeypatch.setattr("thenwhat.cli.backfill.registered_steps", lambda settings: [step])
    add_trials(session, 5)

    plan = run("plan")
    ran = run("run", "quiet")

    assert plan.exit_code == 0, plan.output
    assert "due: 5" in plan.output
    assert "asks no source: the due records need 0 requests" in plan.output
    assert "hours" not in plan.output and "allowance" not in plan.output
    assert ran.exit_code == 0, ran.output
    assert "quiet: 5 done, 0 found nothing, 0 failed; 0 still due." in ran.output


def model_step(monkeypatch: pytest.MonkeyPatch, usd_per_mtok: str | None) -> ModelStep:
    """A registered step that calls the decision backend, priced as the Decisions API is."""
    step = ModelStep()
    monkeypatch.setattr("thenwhat.cli.backfill.registered_steps", lambda settings: [step])
    monkeypatch.setenv("DECISION_BACKEND", "openai-decisions")
    monkeypatch.setenv("LLM_MONTHLY_BUDGET_USD", "13")
    if usd_per_mtok is None:
        monkeypatch.delenv("DECISIONS_INPUT_USD_PER_MTOK", raising=False)
    else:
        monkeypatch.setenv("DECISIONS_INPUT_USD_PER_MTOK", usd_per_mtok)
    return step


def spend(session: Session, dollars: str) -> None:
    session.add(
        LlmUsage(
            purpose="synthetic",
            model="synthetic-model",
            input_tokens=1,
            output_tokens=0,
            cost_usd=Decimal(dollars),
            created_at=datetime.now(UTC),
        )
    )
    session.flush()


def test_plan_gives_a_model_steps_cost_beside_the_ceiling_left(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Planning a model step"""
    model_step(monkeypatch, "100")
    add_trials(session, 100)
    spend(session, "10")

    result = run("plan")

    assert result.exit_code == 0, result.output
    # 100 records at 40 input tokens are 4,000 tokens: $0.40 at $100 a million.
    assert "calls a model: the due records need about $0.40" in result.output
    assert "$3.00 of the month's $13.00 ceiling is left, which covers them all" in result.output


def test_plan_says_how_many_records_the_ceiling_left_covers(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Planning a model step, with more work than the ceiling has left"""
    model_step(monkeypatch, "1000")
    add_trials(session, 100)
    spend(session, "10")

    result = run("plan")

    # A record is $0.04, so the due records need $4.00 and the $3.00 left pays for 75.
    assert "need about $4.00" in result.output
    assert "which covers 75 of the 100 due records" in result.output


def test_plan_gives_no_cost_while_the_price_is_not_configured(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Prices not configured"""
    model_step(monkeypatch, None)
    add_trials(session, 100)

    result = run("plan")

    assert result.exit_code == 0, result.output
    assert "no cost can be given, DECISIONS_INPUT_USD_PER_MTOK is not set" in result.output
    assert "$" not in result.output


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
    assert "No step is named 'no-such-step'. Steps: " in result.output
    assert "news_search" in result.output
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


# --- load-links --------------------------------------------------------------------------


def stories_file(folder: Path) -> Path:
    """A synthetic parquet file of five Hacker News items: three link stories, a text
    story and a comment."""
    import pyarrow as pa
    import pyarrow.parquet as parquet

    when = datetime(2019, 5, 4, 10, 30, tzinfo=UTC)
    rows = [
        {"id": 1, "type": 1, "url": "https://www.theguardian.com/science/a", "title": "One"},
        {"id": 2, "type": 1, "url": "https://www.statnews.com/2019/b", "title": "Two"},
        {"id": 3, "type": 1, "url": "https://github.com/example/c", "title": "Three"},
        {"id": 4, "type": 1, "url": "", "title": "Ask: a text story"},
        {"id": 5, "type": 2, "url": None, "title": None},
    ]
    full = [
        {**row, "time": when, "score": 10, "dead": 0, "deleted": 0, "by": "synthetic_author"}
        for row in rows
    ]
    path = folder / "2019-05.parquet"
    parquet.write_table(pa.Table.from_pylist(full), path)
    return path


def test_a_load_reports_its_counts_and_a_second_load_adds_nothing(
    run, session: Session, tmp_path: Path
):
    """Scenarios: A file of stories, The same file loaded twice"""
    path = stories_file(tmp_path)

    first = run("load-links", "hackernews", str(path))
    second = run("load-links", "hackernews", str(path))

    assert first.exit_code == 0, first.output
    assert "Read 4 posts from 2019-05.parquet: 3 new link leads" in first.output
    assert "skipped, no link: 1" in first.output
    assert "0 new link leads, 0 more shares of leads already stored, 3 already stored" in (
        second.output
    )
    assert len(session.scalars(select(LinkLead)).all()) == 3
    assert len(session.scalars(select(LinkShare)).all()) == 3


def test_a_load_for_an_unknown_platform_is_refused(run, session: Session, tmp_path: Path):
    """Scenario: A platform with no reader"""
    path = stories_file(tmp_path)

    result = run("load-links", "bluesky", str(path))

    assert result.exit_code == 1
    assert "Platforms: hackernews, reddit" in result.output
    assert session.scalars(select(LinkLead)).all() == []


def test_a_reddit_load_is_refused_while_no_community_is_configured(
    run, session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: No community configured"""
    monkeypatch.delenv("LINK_LEAD_SUBREDDITS", raising=False)
    path = tmp_path / "science_submissions.zst"
    path.write_bytes(b"")

    result = run("load-links", "reddit", str(path))

    assert result.exit_code == 1
    assert "LINK_LEAD_SUBREDDITS" in result.output
    assert session.scalars(select(LinkLead)).all() == []


# --- links -------------------------------------------------------------------------------


def test_links_reports_the_screened_leads_and_the_unlisted_domains(
    run, session: Session, tmp_path: Path
):
    """Scenario: After a load and a screening run"""
    run("load-links", "hackernews", str(stories_file(tmp_path)))
    screened = run("run", "link_screen")

    result = run("links")

    assert screened.exit_code == 0, screened.output
    assert "link_screen: 3 done, 0 found nothing, 0 failed; 0 still due." in screened.output
    assert result.exit_code == 0, result.output
    assert "hackernews: 3 link leads loaded, 3 screened" in result.output
    assert "in scope: 2 (67%): 2 general news, 0 health or clinical trade press" in result.output
    assert "on an unlisted outlet: 1 (33%)  already tracked: 0" in result.output
    assert "The unlisted domains with the most link leads:" in result.output
    assert "github.com  1" in result.output


def test_links_says_so_when_nothing_is_screened(run, session: Session, tmp_path: Path):
    """Scenario: Nothing screened yet"""
    run("load-links", "hackernews", str(stories_file(tmp_path)))

    result = run("links")

    assert result.exit_code == 0, result.output
    assert "No link lead has been screened yet." in result.output
    assert "%" not in result.output


# --- sample-leads, label-lead, evaluate-leads --------------------------------------------


def scored_leads(run, session: Session, tmp_path: Path) -> list[LinkLead]:
    """The three synthetic stories, screened, with a score each as triage would leave it."""
    run("load-links", "hackernews", str(stories_file(tmp_path)))
    run("run", "link_screen")
    leads = list(session.scalars(select(LinkLead).order_by(LinkLead.id)))
    for lead, score in zip(leads, (0.95, 0.15, 0.55), strict=True):
        lead.triage_score = score
        lead.triage_version = 1
    session.flush()
    return leads


def test_a_sample_lists_leads_without_their_scores(run, session: Session, tmp_path: Path):
    """Scenario: A sample of 200"""
    scored_leads(run, session, tmp_path)

    result = run("sample-leads", "--size", "10")

    assert result.exit_code == 0, result.output
    assert "theguardian.com" in result.output and "One" in result.output
    assert "0.95" not in result.output
    assert "is short" in result.output


def test_labels_are_recorded_and_the_report_gives_precision_and_recall(
    run, session: Session, tmp_path: Path
):
    """Scenarios: The operator labels a lead, An assistant labels a lead, After 200 labels"""
    guardian, statnews, _ = scored_leads(run, session, tmp_path)

    mine = run("label-lead", str(guardian.id), "treatment_report")
    assistants = run("label-lead", str(statnews.id), "not_health", "--as-assistant")
    result = run("evaluate-leads")

    assert "as your label" in mine.output and "as an assistant's label" in assistants.output
    by = {label.link_lead_id: label.labelled_by for label in session.scalars(select(LinkLeadLabel))}
    assert by == {guardian.id: Decider.HUMAN, statnews.id: Decider.ASSISTANT}
    assert result.exit_code == 0, result.output
    assert "Triage version 1: 1 leads carry a label of yours." in result.output
    assert "pass at or above   precision   recall   leads passed" in result.output
    assert "1 leads have only an assistant's label" in result.output


def test_a_label_that_is_not_an_option_is_refused_by_the_command(
    run, session: Session, tmp_path: Path
):
    """Scenario: A label that is not an option"""
    guardian, *_ = scored_leads(run, session, tmp_path)

    result = run("label-lead", str(guardian.id), "breakthrough")

    assert result.exit_code == 1
    assert "Labels: treatment_report, health_other, not_health" in result.output
    assert session.scalars(select(LinkLeadLabel)).all() == []


def test_the_report_says_so_when_nothing_is_labelled(run, session: Session, tmp_path: Path):
    """Scenario: No labels yet"""
    scored_leads(run, session, tmp_path)

    result = run("evaluate-leads")

    assert result.exit_code == 0, result.output
    assert "No link lead has a label of yours yet" in result.output
    assert "precision" not in result.output


# --- link_read: a limit, and the gate ------------------------------------------------------


def test_reading_is_refused_without_a_limit(run, session: Session):
    result = run("run", "link_read")

    assert result.exit_code == 1
    assert "Run it again with --limit" in result.output


def test_reading_is_refused_until_triage_is_measured(
    run, session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: Too few labels"""
    monkeypatch.setenv("LEAD_PASS_ABOVE", "0.7")
    monkeypatch.setenv("LEAD_REJECT_BELOW", "0.2")
    scored_leads(run, session, tmp_path)

    result = run("run", "link_read", "--limit", "5")

    assert result.exit_code == 1
    assert "Triage has not been measured yet: 0 of the 200 labels needed" in result.output
    assert session.scalars(select(WorkEntry).where(WorkEntry.step == "link_read")).all() == []


def test_the_plan_says_what_reading_would_ask_and_cost(
    run, session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setenv("LEAD_PASS_ABOVE", "0.7")
    monkeypatch.setenv("LEAD_REJECT_BELOW", "0.2")
    monkeypatch.setenv("LLM_INPUT_USD_PER_MTOK", "1")
    monkeypatch.setenv("LLM_OUTPUT_USD_PER_MTOK", "5")
    monkeypatch.setenv("LLM_MONTHLY_BUDGET_USD", "13")
    scored_leads(run, session, tmp_path)

    result = run("plan")

    assert result.exit_code == 0, result.output
    reading = result.output.split("link_read (version 1)")[1]
    # One lead of the three is scored at or above 0.7.
    assert "in scope: 1 of 3 link_lead records" in reading
    assert "asks outlets for 1 pages, each outlet at least 10 seconds apart" in reading
    # 3,000 tokens in at $1 and 700 out at $5 a million is $0.0065 a lead.
    assert "calls a model: the due records need about $0.01" in reading


def test_the_funnel_reports_where_the_leads_stand(run, session: Session, tmp_path: Path):
    """Scenario: After a limited run"""
    scored_leads(run, session, tmp_path)

    result = run("funnel")

    assert result.exit_code == 0, result.output
    assert "loaded: 3" in result.output and "in scope after screening: 2" in result.output
    assert "undecided: 2 (set LEAD_PASS_ABOVE and LEAD_REJECT_BELOW to pass any)" in result.output
    assert "read by the model: 0" in result.output
    assert "model cost recorded for triage: $0.00" in result.output
