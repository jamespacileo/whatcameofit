"""The backfill commands: wiring, messages and exit codes. The rules are tested in
test_work_ledger.py, test_source_allowances.py, test_registry_corpus.py and
test_news_search.py."""

import json
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import httpx
import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from backfill_support import (
    NOW,
    ModelStep,
    QuietStep,
    add_trials,
    committed_sessions,
    remove_committed,
    same_session,
)
from thenwhat.backfill.mediacloud import Story
from thenwhat.backfill.news_search import query_for
from thenwhat.backfill.registry_load import condition_of
from thenwhat.cli import app
from thenwhat.db.models import (
    LinkLead,
    LinkLeadLabel,
    LinkLeadLink,
    LinkShare,
    LlmUsage,
    RegistryTrial,
    SourceAllowanceUse,
    TrialPaper,
    WorkEntry,
)
from thenwhat.domain import Decider, OutletKind, ScreenOutcome
from thenwhat.measure import spans as measure
from thenwhat.measure.events import RUN_ENDED, RUN_STARTED
from thenwhat.measure.files import days_held, read_day, read_events
from thenwhat.sources.clinicaltrials import ClinicalTrials
from thenwhat.sources.pubmed import Paper
from thenwhat.store.form import payload_of
from thenwhat.work.allowance import Allowances


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
    monkeypatch.setattr("thenwhat.cli.backfill.registered_steps", lambda settings, **_: [step])
    add_trials(session, 5)

    plan = run("plan")
    ran = run("run", "quiet")

    assert plan.exit_code == 0, plan.output
    assert "due: 5" in plan.output
    assert "asks no source: the due records need 0 requests" in plan.output
    assert "hours" not in plan.output and "allowance" not in plan.output
    assert ran.exit_code == 0, ran.output
    assert "quiet: 5 done, 0 found nothing, 0 failed; 0 still due." in ran.output


@pytest.mark.parametrize(("limit", "done"), [(None, 4), (1, 1), (3, 3)])
def test_a_run_of_several_workers_is_one_run(
    run, engine: Engine, monkeypatch: pytest.MonkeyPatch, tmp_path: Path, limit, done
):
    """What happens to a run is recorded as it happens: a command's workers make one
    run, which starts with its limit and its workers and ends with why and its counts,
    and every record's measurement names it."""
    step = QuietStep("quiet-workers", registry="workers-registry")
    monkeypatch.setattr("thenwhat.cli.backfill.registered_steps", lambda settings, **_: [step])
    # Each worker in a transaction of its own, as in a real run.
    monkeypatch.setattr("thenwhat.cli.session.open_session", committed_sessions(engine))
    monkeypatch.setenv("MEASURE_DIR", str(tmp_path))
    monkeypatch.setenv("MEASURE_KEEP_DAYS", "30")
    monkeypatch.setenv("MEASURE_LOOKUP_KEEP_DAYS", "7")
    with Session(engine) as session, session.begin():
        add_trials(session, 4, registry="workers-registry")

    try:
        options = ["--limit", str(limit)] if limit is not None else []
        ran = run("run", "quiet-workers", "--workers", "2", *options)
    finally:
        measure.use(None)
        remove_committed(engine, registry="workers-registry", step=step.name, source=step.source)

    assert ran.exit_code == 0, ran.output
    assert f"quiet-workers: {done} done, 0 found nothing, 0 failed; {4 - done} still due." in (
        ran.output
    )
    [day] = days_held(tmp_path)
    started, ended = read_events(tmp_path, day, [RUN_STARTED, RUN_ENDED])
    assert (started.values["limit"], started.values["workers"]) == (limit, 1 if limit == 1 else 2)
    assert ended.values["why"] == ("nothing_due" if limit is None else "limit")
    assert ended.values["counts"]["done"] == done
    assert {span.run for span in read_day(tmp_path, day)} == {started.values["run"]}


def model_step(monkeypatch: pytest.MonkeyPatch, usd_per_mtok: str | None) -> ModelStep:
    """A registered step that calls the decision backend, priced as the Decisions API is."""
    step = ModelStep()
    monkeypatch.setattr("thenwhat.cli.backfill.registered_steps", lambda settings, **_: [step])
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


# --- run ---------------------------------------------------------------------------------


def test_run_with_a_limit_reports_the_work_and_what_remains(run, session: Session, index: Index):
    """Scenario: Limited run"""
    add_trials(session, 5)

    result = run("run", "news_search", "--limit", "2")

    assert result.exit_code == 0, result.output
    assert "news_search: 1 done, 1 found nothing, 0 failed; 3 still due." in result.output


def test_run_refuses_an_unknown_step_and_lists_the_known_steps(run):
    """Scenario: Unknown step"""
    result = run("run", "no-such-step")

    assert result.exit_code == 1
    assert "No step is named 'no-such-step'. Steps: " in result.output
    assert "news_search" in result.output


def test_run_refuses_a_missing_news_key(run):
    result = run("run", "news_search")

    assert result.exit_code == 1
    assert "MEDIACLOUD_API_KEY is not set" in result.output


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


# --- rekey-links -------------------------------------------------------------------------


def earlier_lead(session: Session) -> LinkLead:
    """A lead as the first form of the address key stored it."""
    lead = LinkLead(
        url="https://www.theguardian.com/science/a?mbid=synd_feed",
        url_key="theguardian.com/science/a?mbid=synd_feed",
        url_key_version=1,
        outlet="theguardian.com",
        outlet_kind=OutletKind.GENERAL_NEWS,
        title="One",
        first_shared_at=datetime(2019, 5, 3, 10, 30, tzinfo=UTC),
    )
    session.add(lead)
    session.flush()
    return lead


def test_rekey_links_says_what_it_would_do_and_does_it_when_told(run, session: Session):
    """Scenarios: Looking before bringing the leads up to date, A stored lead's key changes"""
    lead = earlier_lead(session)

    looked = run("rekey-links")
    done = run("rekey-links", "--apply")

    assert looked.exit_code == 0, looked.output
    assert "1 link leads are keyed under an earlier form" in looked.output
    assert "1 would get a new key" in looked.output
    assert done.exit_code == 0, done.output
    assert "Brought 1 link leads up to date: 0 kept their key, 1 got a new key" in done.output
    session.refresh(lead)
    assert lead.url_key == "theguardian.com/science/a"


def test_rekey_links_is_refused_while_a_step_has_just_worked_on_a_lead(
    run, session: Session, tmp_path: Path
):
    """Scenario: A run is under way"""
    run("load-links", "hackernews", str(stories_file(tmp_path)))
    run("run", "link_screen")

    result = run("rekey-links", "--apply")

    assert result.exit_code == 1
    assert "Stop every run and load" in result.output


def test_loading_and_link_steps_are_refused_until_the_leads_are_up_to_date(
    run, session: Session, tmp_path: Path
):
    """Scenario: Loading before the stored leads are up to date"""
    earlier_lead(session)

    load = run("load-links", "hackernews", str(stories_file(tmp_path)))
    step = run("run", "link_screen")

    assert (load.exit_code, step.exit_code) == (1, 1)
    assert "thenwhat backfill rekey-links --apply" in load.output
    assert "thenwhat backfill rekey-links --apply" in step.output
    assert len(session.scalars(select(LinkLead)).all()) == 1


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
    assert (
        "Triage version 1: 2 leads carry a label that counts: 1 yours, 1 an assistant's."
        in result.output
    )
    assert "You have checked none of the assistant's labels yet." in result.output
    assert "pass at or above   precision   recall   leads passed" in result.output
    spot = run("spot-check-leads")
    [listed] = [line for line in spot.output.splitlines() if "statnews.com" in line]
    assert listed.split()[:2] == [str(statnews.id), "not_health"]
    assert "0.15" not in spot.output


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
    assert "No link lead has a label yet" in result.output
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
    # Every page is asked of the page reader, under its one allowance.
    assert "  reader: 3,000 requests in 24 hours, 1 seconds apart; 0 used, 3,000 left" in reading
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


def test_labels_from_a_file_are_recorded_and_a_bad_file_records_nothing(
    run, session: Session, tmp_path: Path
):
    """Scenarios: A file of 200 labels, One bad line"""
    guardian, statnews, _ = scored_leads(run, session, tmp_path)
    good = tmp_path / "labels.tsv"
    good.write_text(f"{guardian.id}\ttreatment_report\n{statnews.id}\tnot_health\n")
    bad = tmp_path / "bad.tsv"
    bad.write_text(f"{guardian.id}\ttreatment_report\n{statnews.id}\tbreakthrough\n")

    refused = run("label-leads", str(bad), "--as-assistant")
    recorded = run("label-leads", str(good), "--as-assistant")

    assert refused.exit_code == 1 and "Line 2" in refused.output
    assert recorded.exit_code == 0, recorded.output
    assert "Recorded 2 labels from labels.tsv, as an assistant's." in recorded.output
    assert {label.labelled_by for label in session.scalars(select(LinkLeadLabel))} == {
        Decider.ASSISTANT
    }


def test_topics_shows_coverage_and_an_unknown_topic_is_refused(run, session: Session):
    """Scenarios: Leads at every stage, An unknown topic"""
    session.add(
        LinkLead(
            url="https://news.example.org/glp",
            url_key="news.example.org/glp",
            outlet="news.example.org",
            outlet_kind=OutletKind.GENERAL_NEWS,
            title="Ozempic in a synthetic trial",
            first_shared_at=datetime(2024, 1, 4, tzinfo=UTC),
        )
    )
    session.flush()

    result = run("topics")

    assert result.exit_code == 0, result.output
    assert "glp-1: 1 link leads name it" in result.output
    assert "not screened yet: 1" in result.output and "claims: 0" in result.output

    refused = run("topics", "statins")

    assert refused.exit_code == 1
    assert "No topic is named 'statins'" in refused.output


# --- asking an outlet again ------------------------------------------------------------


def test_retry_outlet_puts_its_refused_leads_back_and_refuses_an_outlet_with_none(
    run, session: Session
):
    """Scenarios: Asking an outlet again, An outlet with nothing to retry"""
    from thenwhat.backfill import link_reasons as why
    from thenwhat.backfill.link_read import LinkRead
    from thenwhat.domain import ReadOutcome, WorkOutcome

    refused = {"outlet": "news.example.org", "status": 401}
    unasked = {"outlet": "news.example.org", "pages": 5}
    for number, (reason, values) in enumerate(
        [(why.SITE_REFUSED, refused), (why.OUTLET_REFUSES, unasked)]
    ):
        detail = reason.say(values)
        lead = LinkLead(
            url=f"https://news.example.org/refused-{number}",
            url_key=f"news.example.org/refused-{number}",
            outlet="news.example.org",
            outlet_kind=OutletKind.GENERAL_NEWS,
            title="words a person wrote when sharing the link",
            first_shared_at=NOW,
            read_outcome=ReadOutcome.CANNOT_BE_READ,
            read_detail=detail,
        )
        session.add(lead)
        session.flush()
        session.add(
            WorkEntry(
                record_kind="link_lead",
                record_id=lead.id,
                step="link_read",
                step_version=LinkRead.version,
                outcome=WorkOutcome.NEEDS_FIX,
                attempts=0,
                requests_used=1,
                fingerprint="earlier",
                last_attempt_at=NOW,
                reason=reason.code,
                reason_values=values,
            )
        )
    session.flush()

    result = run("retry-outlet", "news.example.org")

    assert result.exit_code == 0, result.output
    assert "2 leads of news.example.org are due to be read again" in result.output
    leads = session.scalars(select(LinkLead).where(LinkLead.outlet == "news.example.org"))
    assert {(lead.read_outcome, lead.read_detail) for lead in leads} == {(None, None)}
    assert [entry.stale for entry in session.scalars(select(WorkEntry))] == [True, True]

    refused = run("retry-outlet", "news.example.org")

    assert refused.exit_code == 1
    assert "No lead of 'news.example.org'" in refused.output


def test_plan_uses_a_steps_measured_cost_once_a_week_is_measured(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """processing-metrics, A saving is claimed only from measurements: with a week of
    measurements the plan gives what a record did cost, not the step's estimate."""
    from datetime import timedelta

    from thenwhat.db.models import MeasureDaily

    model_step(monkeypatch, "100")
    add_trials(session, 100)
    today = datetime.now(UTC).date()
    for back in range(1, 8):
        session.add(
            MeasureDaily(
                day=today - timedelta(days=back),
                step="demo-model",
                step_version=1,
                writer="mini",
                outcome="done",
                spans=50,
                records=1000,
                reused=0,
                ran_seconds=1.0,
                waited_seconds=0.0,
                waited_by_cause={},
                requests_by_source={},
                tokens_in=0,
                tokens_out=0,
                cost_usd=Decimal("0"),
                inner_cost_usd=Decimal("1.00"),
                rows_written=0,
            )
        )
    session.flush()

    result = run("plan")

    assert result.exit_code == 0, result.output
    # A thousand records a day cost $1.00: a tenth of a cent each, so $0.10 for 100.
    assert "the due records need about $0.10 (measured over 7 days)" in result.output


def test_plan_says_when_a_cost_is_the_steps_own_estimate(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    model_step(monkeypatch, "100")
    add_trials(session, 100)

    result = run("plan")

    assert "the due records need about $0.40 (estimated)" in result.output


def test_load_trials_asks_for_a_named_set(
    run, session: Session, monkeypatch: pytest.MonkeyPatch, fake_time, fixture_json
):
    """The trials under way now in phase 2 or 3 are asked for by name, in the registry's
    own expression."""
    page = fixture_json("clinicaltrials/list_page_2.json")
    asked: list[str] = []

    def registry(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.params.get("filter.advanced", ""))
        return httpx.Response(200, json=page)

    monkeypatch.setattr(
        "thenwhat.cli.backfill.make_registry",
        lambda lookups, settings: ClinicalTrials(
            lookups,
            contact_email=settings.contact_email,
            transport=httpx.MockTransport(registry),
            time=fake_time,
        ),
    )

    result = run("load-trials", "--trials", "active-phase-2-3")

    assert result.exit_code == 0, result.output
    assert "AREA[Phase]PHASE2 OR AREA[Phase]PHASE3" in asked[0]
    assert "RECRUITING OR ACTIVE_NOT_RECRUITING" in asked[0]


def test_load_trials_stops_cleanly_when_the_allowance_is_used_up(
    run, session: Session, monkeypatch: pytest.MonkeyPatch, fake_time, fixture_json
):
    """The daily run loads changes every day: an allowance used up is a stop that is
    meant, with the counts so far, and not a failure."""
    page = fixture_json("clinicaltrials/list_page_1.json")
    asked: list[str] = []

    def registry(request: httpx.Request) -> httpx.Response:
        asked.append(request.url.params.get("filter.advanced", ""))
        return httpx.Response(200, json=page)

    monkeypatch.setattr(
        "thenwhat.cli.backfill.make_registry",
        lambda lookups, settings: ClinicalTrials(
            lookups,
            contact_email=settings.contact_email,
            transport=httpx.MockTransport(registry),
            time=fake_time,
        ),
    )
    monkeypatch.setenv(
        "SOURCE_ALLOWANCES",
        '{"clinicaltrials.gov": {"requests": 1, "period_hours": 24, "interval_seconds": 0}}',
    )

    result = run("load-trials", "--trials", "interventional", "--changes-only")

    assert result.exit_code == 0, result.output
    assert asked == ["AREA[StudyType]INTERVENTIONAL"]
    assert "Loaded 3 trials in 1 requests: 3 new, 0 already stored." in result.output
    assert "Stopped: The allowance for clinicaltrials.gov (1 requests) is used up." in (
        result.output
    )
    assert len(session.scalars(select(RegistryTrial)).all()) == 3


def test_load_trials_records_a_too_many_requests_and_stops_cleanly(
    run, session: Session, monkeypatch: pytest.MonkeyPatch, fake_time, fixture_json
):
    """The registry keeps answering 429 to the second page: the pause is recorded for
    every process, the command stops with its counts and exit 0, and a second load the
    same night sends nothing."""
    first = fixture_json("clinicaltrials/list_page_1.json")
    asked: list[bool] = []

    def registry(request: httpx.Request) -> httpx.Response:
        asked.append("pageToken" in request.url.params)
        if "pageToken" in request.url.params:
            return httpx.Response(429, headers={"Retry-After": "3600"}, text="slow down")
        return httpx.Response(200, json=first)

    monkeypatch.setattr(
        "thenwhat.cli.backfill.make_registry",
        lambda lookups, settings: ClinicalTrials(
            lookups,
            contact_email=settings.contact_email,
            transport=httpx.MockTransport(registry),
            time=fake_time,
        ),
    )

    result = run("load-trials", "--trials", "interventional", "--changes-only")

    assert result.exit_code == 0, result.output
    assert "Loaded 3 trials in 1 requests: 3 new, 0 already stored." in result.output
    assert "Stopped: clinicaltrials.gov said it was asked too often." in result.output
    use = session.get(SourceAllowanceUse, "clinicaltrials.gov")
    assert use is not None and use.paused_until is not None and use.refusals == 1

    asked.clear()
    again = run("load-trials", "--trials", "interventional", "--changes-only")

    assert again.exit_code == 0, again.output
    assert asked == []
    assert "Loaded 0 trials in 0 requests" in again.output
    assert "Stopped: clinicaltrials.gov is paused until" in again.output


def test_load_trials_refuses_a_set_it_does_not_know(run, session: Session):
    result = run("load-trials", "--trials", "successful")

    assert result.exit_code == 1
    assert (
        "No set of trials is named 'successful'. Sets: active-phase-2-3, "
        "active-phase-2-3-or-completed-2026, interventional, phase-3." in result.output
    )
    assert session.scalars(select(RegistryTrial)).all() == []


def test_the_set_of_every_trial_is_every_interventional_study():
    """Every trial means every interventional study, whatever its phase, state or kind of
    intervention; observational studies are not asked for."""
    assert condition_of("interventional") == "AREA[StudyType]INTERVENTIONAL"


def test_load_trials_refuses_a_set_and_a_condition_together(run):
    result = run("load-trials", "--trials", "phase-3", "--condition", "AREA[Phase]PHASE1")

    assert result.exit_code == 1
    assert "Give --condition or --trials, not both." in result.output


def test_trial_sets_counts_each_set_by_phase(run, session: Session):
    trials = add_trials(session, 4)
    phases_of = (["PHASE2"], ["PHASE3"], ["PHASE2", "PHASE3"])
    for stored, phases in zip(trials[:3], phases_of, strict=True):
        stored.phases = phases
        stored.overall_status = "RECRUITING"
        stored.last_update_posted = date(2026, 3, 1)
    trials[3].overall_status = "COMPLETED"
    trials[3].completion_date, trials[3].completion_date_type = "2025-09", "ACTUAL"
    trials[3].has_results = True
    trials[3].last_update_posted = date(2026, 3, 1)
    add_trials(session, 1, registry="older-registry")
    session.flush()

    result = run("trial-sets")

    assert result.exit_code == 0, result.output
    assert (
        "active-since-2025 (phase 2 or 3, under way, record updated on or after 2025-01-01): "
        f"3 trials, loaded {NOW.date()}" in result.output
    )
    assert "  phase 2: 1\n  phase 2/3: 1\n  phase 3: 1\n" in result.output
    assert "results posted): 1 trial, loaded" in result.output
    assert "1 of 5 stored trials were loaded before these fields" in result.output


def test_trial_sets_is_refused_until_trials_have_the_wider_record(run, session: Session):
    add_trials(session, 2)

    result = run("trial-sets")

    assert result.exit_code == 1
    assert "No stored trial has the activity and results fields yet." in result.output


def test_registry_claim_plan_reports_eligible_older_records_for_review(run, session: Session):
    stored = add_trials(session, 1, registry="clinicaltrials.gov")[0]
    stored.overall_status = "RECRUITING"
    stored.last_update_posted = date(2026, 3, 1)
    session.flush()

    result = run("registry-claim-plan")

    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert plan["set"] == "active-phase-2-3-or-completed-2026"
    assert plan["trial_count"] == 1
    assert plan["groups"] == []
    assert "missing_tested_arm" in plan["needs_review"][stored.external_id]["issues"]


def test_registry_claim_plan_refuses_an_unloaded_corpus(run):
    result = run("registry-claim-plan")

    assert result.exit_code == 1
    assert "No stored trial has the activity and results fields yet." in result.output


def test_registry_claim_plan_applies_an_evidence_receipt(run, session: Session, tmp_path: Path):
    stored = add_trials(session, 1, registry="clinicaltrials.gov")[0]
    stored.external_id = "NCT00000001"
    stored.overall_status = "RECRUITING"
    stored.last_update_posted = date(2026, 3, 1)
    stored.raw_payload = {
        "protocolSection": {
            "identificationModule": {"briefTitle": "Example XR for Eye Irritation"},
            "designModule": {"designInfo": {"primaryPurpose": "TREATMENT"}},
        }
    }
    session.flush()
    receipt = {
        "trial_id": stored.external_id,
        "registry_sha256": payload_of(stored.raw_payload).sha256,
        "reviewed_by": "assistant:test",
        "pairs": [
            {
                "regimen": ["Example XR"],
                "indication": "Eye Irritation",
                "intervention_quotes": ["Example XR"],
                "indication_quotes": ["Eye Irritation"],
            }
        ],
    }
    reviews = tmp_path / "reviews.json"
    reviews.write_text(json.dumps({"schema_version": 1, "reviews": [receipt]}))

    result = run("registry-claim-plan", "--reviewed-scopes", str(reviews))

    assert result.exit_code == 0, result.output
    plan = json.loads(result.output)
    assert plan["applied_reviews"] == {stored.external_id: "assistant:test"}
    assert plan["groups"][0]["indication"] == "Eye Irritation"


def test_trial_references_counts_what_the_stored_records_list(run, session: Session):
    trials = add_trials(session, 2)
    for stored in trials:
        stored.overall_status = "RECRUITING"
        stored.last_update_posted = date(2026, 3, 1)
    trials[0].raw_payload = {
        "protocolSection": {
            "referencesModule": {
                "references": [{"pmid": "1", "type": "RESULT"}, {"pmid": "2", "type": "DERIVED"}],
                "seeAlsoLinks": [{"url": "https://sponsor.example/study"}],
            }
        }
    }
    session.flush()

    result = run("trial-references", "--set", "active-since-2025")

    assert result.exit_code == 0, result.output
    assert "active-since-2025: 2 trials" in result.output
    assert "list a paper as reporting results (sponsor): 1 trials, 1 papers" in result.output
    assert "linked by the registry from PubMed: 1 trials, 1 more papers" in result.output
    assert "give a link: 1 trials, 1 links; on a listed outlet: 0 trials, 0 links" in result.output
    assert "    sponsor.example: 1" in result.output


def test_trial_references_refuses_a_set_it_does_not_know(run):
    result = run("trial-references", "--set", "elsewhere")

    assert result.exit_code == 1
    assert "No set of stored trials is named 'elsewhere'" in result.output


def test_trial_references_refuses_before_the_wider_load(run, session: Session):
    """Zeros would read as "no trial lists a paper" when no trial could be chosen."""
    add_trials(session, 2)

    result = run("trial-references")

    assert result.exit_code == 1
    assert "No stored trial has the activity and results fields yet." in result.output
    assert "0 trials" not in result.output


def test_the_plan_shows_what_a_batched_step_needs(run, session: Session):
    trials = add_trials(session, 120, registry=ClinicalTrials.name)
    for number, stored in enumerate(trials):
        stored.external_id = f"NCT{number:08d}"
        stored.overall_status = "RECRUITING"
        stored.last_update_posted = date(2026, 3, 1)
    session.flush()

    result = run("plan")

    assert result.exit_code == 0, result.output
    papers = result.output.split("pubmed_papers (version 1)")[1].split(" (version ")[0]
    # 120 trials, 50 to a search, a search and a fetch for each batch.
    assert "the due records need about 6 requests in batches" in papers
    assert "requests: about 2 for each 50 records" in run("steps").output


def test_the_paper_step_reports_on_its_trial_target_set(run, session: Session, monkeypatch):
    target_set(session, datetime.now(UTC))

    class Papers:
        name = "pubmed"
        requests_made = 0

        def papers_carrying(self, numbers):
            self.requests_made += 1
            return [Paper("11", ("NCT00000001",), {"pmid": "11"})], NOW

    monkeypatch.setattr("thenwhat.cli.backfill.make_client", lambda step, settings, a: Papers())

    result = run("run", "pubmed_papers")

    assert result.exit_code == 0, result.output
    assert "pubmed_papers: 1 done, 2 found nothing, 0 failed; 0 still due." in result.output


def test_the_paper_step_is_refused_without_a_tool_name(run, session: Session, monkeypatch):
    monkeypatch.setenv("PUBMED_TOOL", "then what")

    result = run("run", "pubmed_papers")

    assert result.exit_code == 1
    assert "PUBMED_TOOL is not set" in result.output


# --- read-set: the leads linked to a named set of trials ---------------------------------


def linked_leads(session: Session, monkeypatch: pytest.MonkeyPatch, count: int) -> None:
    """Passed leads in scope, each strongly linked to one trial of `active-since-2025`."""
    monkeypatch.setenv("LEAD_PASS_ABOVE", "0.7")
    monkeypatch.setenv("LEAD_REJECT_BELOW", "0.2")
    monkeypatch.setenv("LLM_INPUT_USD_PER_MTOK", "1")
    monkeypatch.setenv("LLM_OUTPUT_USD_PER_MTOK", "5")
    [stored] = add_trials(session, 1)
    stored.overall_status = "RECRUITING"
    stored.last_update_posted = date(2026, 3, 1)
    for number in range(count):
        lead = LinkLead(
            url=f"https://www.bbc.com/news/health-{number}",
            url_key=f"bbc.com/news/health-{number}",
            outlet="bbc.com",
            outlet_kind=OutletKind.GENERAL_NEWS,
            title="A synthetic headline",
            first_shared_at=NOW,
            screen_outcome=ScreenOutcome.IN_SCOPE,
            triage_score=0.9,
            triage_version=1,
        )
        session.add(lead)
        session.flush()
        session.add(
            LinkLeadLink(
                link_lead_id=lead.id,
                record_kind="registry_trial",
                record_id=stored.id,
                reason="synthetic",
                strength="strong",
            )
        )
    session.flush()


def test_read_set_prints_a_plan_and_reads_nothing_without_a_limit(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: A plan for the first set"""
    linked_leads(session, monkeypatch, 3)

    result = run("read-set", "active-since-2025")

    assert result.exit_code == 0, result.output
    assert "3 leads in scope are linked (exact or strong) to 1 trials of the set" in result.output
    assert "triage: 3 passed, 0 held, 0 rejected, 0 not scored; 0 already read" in result.output
    assert "would be read: 3, those linked to phase 3 trials first" in result.output
    # 3,000 tokens in at $1 and 700 out at $5 a million is $0.0065 a read.
    assert "expected cost: $0.02 at $0.0065 a read (estimated); about 1 claims" in result.output
    assert "$0.00 of the route's $15.00 share; $15.00 left" in result.output
    assert "Nothing was read. Give --limit to read." in result.output
    assert session.scalars(select(WorkEntry).where(WorkEntry.step == "link_read")).all() == []


def test_read_set_reads_nothing_when_the_cost_passes_the_routes_share(
    run, session: Session, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: The share would be passed"""
    linked_leads(session, monkeypatch, 3)
    monkeypatch.setenv("TRIAL_ROUTE_MONTHLY_USD", "0.01")

    result = run("read-set", "active-since-2025", "--limit", "3")

    assert result.exit_code == 1
    assert "Nothing was read: the reads are expected to cost $0.02 and $0.01 is left" in (
        result.output
    )
    assert session.scalars(select(WorkEntry).where(WorkEntry.step == "link_read")).all() == []


def test_read_set_refuses_a_set_or_a_strength_it_does_not_know(run):
    """Scenario: A set the command does not know"""
    unknown_set = run("read-set", "elsewhere")
    unknown_strength = run("read-set", "active-since-2025", "--strength", "certain")

    assert (unknown_set.exit_code, unknown_strength.exit_code) == (1, 1)
    assert "No set of stored trials is named 'elsewhere'" in unknown_set.output
    assert "No strength of link is named 'certain'" in unknown_strength.output


# --- the trial target set: active-or-ended-this-year -------------------------------------


def target_set(session: Session, fake_now: datetime) -> list[RegistryTrial]:
    """Three trials of the rolling set, chosen in the year of `fake_now`, and one outside."""
    trials = add_trials(session, 4, registry=ClinicalTrials.name)
    year = fake_now.year
    for number, stored in enumerate(trials, start=1):
        stored.external_id = f"NCT0000000{number}"
        stored.phases = ["PHASE1"]
        stored.overall_status = "RECRUITING"
        stored.last_update_posted = date(year, 3, 1)
        stored.has_results = False
    trials[1].last_update_posted = date(year - 2, 12, 31)
    trials[2].overall_status, trials[2].completion_date = "COMPLETED", f"{year}-02"
    trials[2].has_results = True
    trials[3].overall_status, trials[3].completion_date = "COMPLETED", f"{year - 1}-02"
    session.flush()
    return trials


def test_trial_coverage_counts_the_set_by_group_and_estimates_the_paper_index(
    run, session: Session
):
    """Scenarios: A coverage report for the set, An estimate before the paper index is asked"""
    now = datetime.now(UTC)
    trials = target_set(session, now)
    session.add(
        TrialPaper(
            registry_trial_id=trials[2].id,
            source_name="pubmed",
            pubmed_id="11",
            raw_payload={"pmid": "11"},
            fetched_at=NOW,
        )
    )
    session.flush()

    result = run("trial-coverage")

    assert result.exit_code == 0, result.output
    said = result.output
    assert f"active-or-ended-this-year, chosen in {now.year}" in said
    assert "under way: 2 trials" in said
    assert f"completed in {now.year}: 1 trials" in said
    assert f"terminated, withdrawn or suspended in {now.year}: 0 trials" in said
    whole = said.split("all: 3 trials")[1]
    assert "results posted: 1" in whole and "a paper found in PubMed by number: 1" in whole
    assert "cited by a published claim: 0" in whole
    assert f"record not updated since before {now.year - 1}: 1" in whole
    assert "PubMed has not been asked about 3 trials in scope: about 2 requests" in said
    assert "1 off-peak night under the allowance of 5,000 in 24 hours" in said
    assert "set PUBMED_API_KEY" in said
    # Counting asks nothing and marks nothing done.
    assert session.scalars(select(WorkEntry)).all() == []


def test_trial_coverage_is_refused_before_the_wider_load(run, session: Session):
    add_trials(session, 2)

    result = run("trial-coverage")

    assert result.exit_code == 1
    assert "No stored trial has the activity and results fields yet." in result.output


def test_trial_references_counts_the_trial_target_set(run, session: Session):
    target_set(session, datetime.now(UTC))

    result = run("trial-references", "--set", "active-or-ended-this-year")

    assert result.exit_code == 0, result.output
    assert "active-or-ended-this-year: 3 trials" in result.output


def test_the_funnel_counts_why_leads_were_not_read_from_their_reason_codes(run, session: Session):
    """Scenario: The funnel report (openspec lead-reading, change one-work-runner)"""
    from datetime import timedelta

    from thenwhat.backfill import link_reasons as why
    from thenwhat.backfill.link_read import LinkRead
    from thenwhat.domain import ReadOutcome, WorkOutcome

    def lead(name: str, outlet: str, outcome, reason, values, entry_outcome) -> None:
        carried = {"outlet": outlet, **values}
        said = outcome is not None
        added = LinkLead(
            url=f"https://{outlet}/{name}",
            url_key=f"{outlet}/{name}",
            outlet=outlet,
            outlet_kind=OutletKind.GENERAL_NEWS,
            title="words a person wrote when sharing the link",
            first_shared_at=NOW,
            read_outcome=outcome,
            read_detail=reason.say(carried) if said else None,
        )
        session.add(added)
        session.flush()
        later = entry_outcome is WorkOutcome.LATER
        session.add(
            WorkEntry(
                record_kind="link_lead",
                record_id=added.id,
                step="link_read",
                step_version=LinkRead.version,
                outcome=entry_outcome,
                attempts=0,
                requests_used=1,
                fingerprint="earlier",
                last_attempt_at=NOW,
                reason=reason.code,
                reason_values=carried,
                not_before=NOW + timedelta(hours=6) if later else None,
                first_put_off_at=NOW if later else None,
            )
        )

    unreadable, fix = ReadOutcome.CANNOT_BE_READ, WorkOutcome.NEEDS_FIX
    lead("a", "news.example.org", unreadable, why.SITE_REFUSED, {"status": 403}, fix)
    lead("b", "other.example.org", unreadable, why.SITE_REFUSED, {"status": 403}, fix)
    lead("c", "news.example.org", unreadable, why.NO_DATE, {}, fix)
    lead("d", "news.example.org", None, why.SITE_BUSY, {"status": 503}, WorkOutcome.LATER)
    session.flush()

    result = run("funnel")

    assert result.exit_code == 0, result.output
    assert "could not be read: 3" in result.output
    assert "  the page could not be retrieved (the site answered 403): 2" in result.output
    assert "  the page gives no publication date: 1" in result.output
    assert "outlets whose pages gave no publication date:\n  news.example.org  1" in result.output
    assert "put off, to be asked for again: 1" in result.output
    assert "  the page could not be retrieved (the site answered 503): 1" in result.output


def test_plan_counts_changed_outlets_before_each_bounded_screening_run(run, session, monkeypatch):
    from backfill_support import Client
    from test_link_screening import screen, share
    from thenwhat.backfill.link_screen import LinkScreen
    from thenwhat.db.models import LinkLead
    from thenwhat.domain import OutletKind
    from thenwhat.work.runner import run_step

    step = LinkScreen()
    for n in range(3):
        share(session, f"https://health.example.org/news/story-{n}", item=n + 1)
    screen(session, step)
    monkeypatch.setattr("thenwhat.cli.backfill.registered_steps", lambda *args, **kwargs: [step])
    monkeypatch.setattr("thenwhat.backfill.link_screen.kind_of", lambda _: OutletKind.TRADE_PRESS)

    def snapshot():
        return list(
            session.execute(select(LinkLead.id, LinkLead.outlet_kind).order_by(LinkLead.id))
        ), list(
            session.execute(
                select(WorkEntry.id, WorkEntry.stale, WorkEntry.attempts).order_by(WorkEntry.id)
            )
        )

    for due in (3, 1, 0):
        before = snapshot()
        result = run("plan")
        assert result.exit_code == 0 and f"due: {due}" in result.output, result.output
        assert snapshot() == before
        step.check_ready(session)
        report = run_step(
            same_session(session), step, Client(), now=lambda: NOW, attempt_limit=3, limit=2
        )
        assert report.done == min(2, due)
