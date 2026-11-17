"""What each way a lead step can end writes: characterisation tests.

These tests pinned the behaviour before openspec change `one-work-runner`, task 1.1, and
now pin it as the change leaves it (see LANDED below). One
record per way a step can end, at the session seam, with the fakes the steps' own tests
use: for each, the work entry's outcome, its attempts, whether the record is due again,
and for `link_read` the lead's read outcome and the exact words of its read detail. Every
page, title and model answer is synthetic. A case an existing test asserts in full is not
repeated here; it is listed with that test.

Coverage, case -> test (this module unless a module is named):

link_read
  added to claim -> test_an_article_added_to_a_claim_is_done
  new claim -> test_a_new_claim_is_done
  enough articles -> test_a_claim_with_enough_articles_finishes_the_lead
  needs vertical -> test_no_likely_vertical_needs_a_fix
  not one treatment -> test_not_one_treatment_finishes_the_lead
  business news -> test_business_news_finishes_the_lead
  identity unresolved -> test_an_overlap_left_unresolved_finishes_the_lead
  already tracked (no read outcome) -> test_a_lead_tracked_since_screening_is_nothing_found
  cannot be read: the site answered 401, 403 (one case each)
    -> test_a_site_that_refuses_the_reader_needs_a_fix
  cannot be read: the site answered 404 -> test_a_page_the_site_says_is_gone_finishes_the_lead
  put off: the site answered 503, 202 (one case each)
    -> test_a_site_that_cannot_serve_now_is_put_off
  cannot be read: the page reader does not allow the address
    -> test_an_address_the_reader_does_not_allow_finishes_the_lead
  cannot be read: too little text, no date, no headline, no outlet name (one case each)
    -> test_a_page_that_cannot_be_used_needs_a_fix
  cannot be read: the outlet answered 401 for enough pages and served none
    -> test_an_outlet_that_refuses_the_reader_needs_a_fix
  reader says not now -> test_not_now_from_the_reader_is_put_off
  outlet held -> test_a_held_outlet_is_put_off
  model read fails, outage -> test_a_model_outage_in_the_read_fails_the_lead
  model read fails, invalid output -> test_an_invalid_read_fails_the_lead
  spend ceiling during the read -> test_the_spend_ceiling_in_the_read_stops_the_run
  treatment-kind decision fails -> test_a_failed_treatment_kind_decision_fails_the_lead
  reader itself down -> test_link_reading.py::
    test_the_reader_down_ends_the_run_with_leads_due_and_attempts_unchanged
link_triage
  scored -> test_a_scored_lead_is_done
  model unreachable -> test_link_triage.py::
    test_a_model_that_cannot_be_reached_stops_the_run_and_uses_no_attempt
  one lead of a batch fails -> test_a_lead_its_batch_left_unanswered_fails_alone
link_screen
  in scope, unlisted outlet, already tracked -> test_screening_is_done_whatever_it_finds
news_search
  done, nothing found -> test_a_news_search_that_answers_is_finished
  source unavailable -> test_a_news_index_that_fails_fails_the_trial
"""

# LANDED:
# test_a_site_that_cannot_serve_now_is_put_off[503, 202]: put off, no attempt.
# test_a_site_that_refuses_the_reader_needs_a_fix[401, 403]: needs a fix.
# test_a_page_that_cannot_be_used_needs_a_fix (all four causes): needs a fix.
# test_an_outlet_that_refuses_the_reader_needs_a_fix: needs a fix (refused, 401).
# test_no_likely_vertical_needs_a_fix: needs a fix.
# test_not_now_from_the_reader_is_put_off: Deferred became a recorded "later" outcome.
# test_a_held_outlet_is_put_off: Deferred became a recorded "later" outcome.
#
# CHANGES under one-work-runner, not yet landed:
# test_a_model_outage_in_the_read_fails_the_lead: the outage stops the run, no attempt.
# test_a_failed_treatment_kind_decision_fails_the_lead[unreachable]: stops the run.
# test_a_news_index_that_fails_fails_the_trial: a source that is down may stop the run
#   ("A provider that cannot be asked stops the run"), with no attempt counted.

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backfill_support import add_trials, same_session
from test_link_reading import (
    NOW,
    Reader,
    Verticals,
    link,
    page,
    refused_earlier,
    tracked_claim,
)
from test_link_screening import claim as screened_claim
from test_link_screening import screen, share
from test_link_triage import Headlines, add_leads, triage
from test_news_search import Index, Service, media_cloud, search, story
from thenwhat.backfill.link_screen import TITLE_NAMES_CLAIM, LinkScreen
from thenwhat.backfill.link_triage import LinkTriage
from thenwhat.backfill.news_search import NewsSearch, query_for
from thenwhat.backfill.outlet_hold import keep
from thenwhat.claims.entry import add_article
from thenwhat.db.models import DecisionLog, LinkLead, LlmUsage, WorkEntry
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import BUSINESS_NEWS, NOT_ONE_TREATMENT, TREATMENT_KIND
from thenwhat.domain import ReadOutcome, ScreenOutcome, WorkOutcome
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.llm.errors import LlmCallFailed
from thenwhat.work.ledger import count, due_records
from thenwhat.work.runner import run_step
from thenwhat.work.steps import Step

# The attempt limit every run here is given, as `Reader.read` gives it.
LIMIT = 3


def entry_of(session: Session, step: Step, record: Any) -> WorkEntry | None:
    return session.scalars(
        select(WorkEntry).where(
            WorkEntry.record_kind == step.record_kind,
            WorkEntry.record_id == record.id,
            WorkEntry.step == step.name,
        )
    ).one_or_none()


def is_due(session: Session, step: Step, record: Any) -> bool:
    due = session.scalars(due_records(step, LIMIT).with_only_columns(step.model.id))
    return record.id in set(due)


def ended(session: Session, step: Step, record: Any) -> tuple[Any, ...]:
    """The entry's outcome and attempts, None for no entry, and whether it is due."""
    entry = entry_of(session, step, record)
    return (
        entry.outcome if entry else None,
        entry.attempts if entry else None,
        is_due(session, step, record),
    )


def read_ended(reader: Reader, lead: LinkLead) -> tuple[Any, ...]:
    """What a read left: the entry as `ended` gives it, then the lead's read outcome and
    read detail."""
    return (*ended(reader.session, reader.step, lead), lead.read_outcome, lead.read_detail)


def put_off(reader: Reader, lead: LinkLead) -> tuple[Any, ...]:
    """What a put-off lead holds: the entry's outcome and attempts, then the lead's read
    outcome and read detail. Whether it is due depends on the clock the step was given,
    so a test asks the ledger for a time it names."""
    outcome, attempts, _ = ended(reader.session, reader.step, lead)
    return (outcome, attempts, lead.read_outcome, lead.read_detail)


def reason_of(reader: Reader, lead: LinkLead) -> tuple[Any, ...]:
    """The reason code the lead's entry holds, the values it carries, and when the lead
    is put off until."""
    entry = entry_of(reader.session, reader.step, lead)
    assert entry is not None
    return entry.reason, entry.reason_values, entry.not_before


@pytest.fixture
def reader(session: Session, fake_time) -> Reader:
    return Reader(session, fake_time)


# --- link_read: a page that was read ------------------------------------------------------


def test_a_new_claim_is_done(reader: Reader):
    lead = reader.lead()

    report = reader.read()

    assert (report.done, report.nothing_found, report.failed) == (1, 0, 0)
    assert read_ended(reader, lead) == (WorkOutcome.DONE, 1, False, ReadOutcome.NEW_CLAIM, None)


def test_an_article_added_to_a_claim_is_done(reader: Reader):
    claim = tracked_claim(reader.session)
    reader.backend.same_claim = claim.slug
    lead = reader.lead()

    reader.read()

    assert read_ended(reader, lead) == (
        WorkOutcome.DONE,
        1,
        False,
        ReadOutcome.ADDED_TO_CLAIM,
        "read as EX-1 antibody for tooth agenesis; the same claim by decision at 0.90, none"
        " of the candidates at 0.10",
    )


def test_a_claim_with_enough_articles_finishes_the_lead(reader: Reader):
    claim = tracked_claim(reader.session, articles=3, first=date(2021, 3, 1))
    lead = reader.lead(shared_at=datetime(2022, 1, 4, tzinfo=UTC))
    link(reader.session, lead, "claim", claim.id, TITLE_NAMES_CLAIM)

    reader.read()

    assert read_ended(reader, lead) == (
        WorkOutcome.NOTHING_FOUND,
        1,
        False,
        ReadOutcome.ENOUGH_ARTICLES,
        "the claim it names has enough articles: ex-1-tooth-agenesis",
    )
    assert reader.page_reader.asked == []
    assert reason_of(reader, lead) == ("enough_articles", {"outlet": "theguardian.com"}, None)


def test_no_likely_vertical_needs_a_fix(reader: Reader):
    reader.backend.probability = 0.5
    lead = reader.lead()

    report = reader.read()

    assert (report.needs_fix, report.nothing_found, report.later) == (1, 0, 0)
    # No attempt is counted, and the lead waits to be made due.
    assert read_ended(reader, lead) == (
        WorkOutcome.NEEDS_FIX,
        0,
        False,
        ReadOutcome.NEEDS_VERTICAL,
        "EX-1 antibody for tooth agenesis; the nearest vertical was mouth-and-teeth at 0.50",
    )
    assert reason_of(reader, lead) == ("needs_vertical", {"outlet": "theguardian.com"}, None)


def test_not_one_treatment_finishes_the_lead(reader: Reader):
    reader.backend.report_kind = NOT_ONE_TREATMENT
    lead = reader.lead()

    reader.read()

    assert read_ended(reader, lead) == (
        WorkOutcome.NOTHING_FOUND,
        1,
        False,
        ReadOutcome.NOT_ONE_TREATMENT,
        "EX-1 antibody for tooth agenesis; about one treatment for one condition at 0.05",
    )
    assert reason_of(reader, lead) == ("not_one_treatment", {"outlet": "theguardian.com"}, None)


def test_business_news_finishes_the_lead(reader: Reader):
    reader.backend.report_kind = BUSINESS_NEWS
    lead = reader.lead()

    reader.read()

    assert read_ended(reader, lead) == (
        WorkOutcome.NOTHING_FOUND,
        1,
        False,
        ReadOutcome.BUSINESS_NEWS,
        "EX-1 antibody for tooth agenesis; no claim to join, and about what the treatment"
        " does at 0.03",
    )
    assert reason_of(reader, lead) == ("business_news", {"outlet": "theguardian.com"}, None)


def test_an_overlap_left_unresolved_finishes_the_lead(reader: Reader):
    claim = tracked_claim(reader.session)
    # The same-claim decision says the article reports none of the candidates.
    reader.backend.same_claim = None
    lead = reader.lead()

    reader.read()

    assert read_ended(reader, lead) == (
        WorkOutcome.NOTHING_FOUND,
        1,
        False,
        ReadOutcome.IDENTITY_UNRESOLVED,
        f"EX-1 antibody for tooth agenesis; names overlap {claim.slug}, but the same"
        " treatment and condition were not established, so no claim was drafted",
    )
    assert reason_of(reader, lead) == ("identity_unresolved", {"outlet": "theguardian.com"}, None)


def test_a_lead_tracked_since_screening_is_nothing_found(reader: Reader):
    claim = tracked_claim(reader.session, articles=0)
    add_article(
        reader.session,
        claim.slug,
        url="https://amp.theguardian.com/science/2019/may/04/synthetic-teeth",
        outlet="The Guardian",
        title="A synthetic headline",
        published_date=date(2019, 5, 4),
    )
    lead = reader.lead()

    reader.read()

    # No read outcome: the lead leaves the step's scope as already tracked.
    assert read_ended(reader, lead) == (WorkOutcome.NOTHING_FOUND, 1, False, None, None)
    assert (lead.screen_outcome, lead.claim_id) == (ScreenOutcome.ALREADY_TRACKED, claim.id)
    assert reason_of(reader, lead)[0] == "already_tracked"


# --- link_read: a page that cannot be read -------------------------------------------------


@pytest.mark.parametrize("status", [401, 403])
def test_a_site_that_refuses_the_reader_needs_a_fix(reader: Reader, status: int):
    lead = reader.lead(serves=None)
    reader.page_reader.site = lambda request: httpx.Response(status)

    report = reader.read()

    assert (report.needs_fix, report.nothing_found, report.later, report.deferred) == (1, 0, 0, 0)
    assert read_ended(reader, lead) == (
        WorkOutcome.NEEDS_FIX,
        0,
        False,
        ReadOutcome.CANNOT_BE_READ,
        f"the page could not be retrieved (the site answered {status})",
    )
    assert reason_of(reader, lead) == (
        "site_refused",
        {"outlet": "theguardian.com", "status": status},
        None,
    )
    assert reader.prompts == []


def test_a_page_the_site_says_is_gone_finishes_the_lead(reader: Reader):
    lead = reader.lead(serves=None)

    report = reader.read()

    assert (report.nothing_found, report.needs_fix, report.later) == (1, 0, 0)
    assert read_ended(reader, lead) == (
        WorkOutcome.NOTHING_FOUND,
        1,
        False,
        ReadOutcome.CANNOT_BE_READ,
        "the page could not be retrieved (the site answered 404)",
    )
    assert reason_of(reader, lead) == (
        "page_gone",
        {"outlet": "theguardian.com", "status": 404},
        None,
    )
    assert reader.prompts == []


@pytest.mark.parametrize("status", [503, 202])
def test_a_site_that_cannot_serve_now_is_put_off(reader: Reader, status: int):
    lead = reader.lead(serves=None)
    reader.page_reader.site = lambda request: httpx.Response(status)
    began = reader.time.now()

    report = reader.read(by_the_step_clock=True)

    # Put off for the configured six hours: no attempt, and the lead holds nothing.
    assert (report.later, report.needs_fix, report.nothing_found, report.deferred) == (1, 0, 0, 0)
    assert put_off(reader, lead) == (WorkOutcome.LATER, 0, None, None)
    assert reason_of(reader, lead) == (
        "site_busy",
        {"outlet": "theguardian.com", "status": status},
        began + timedelta(hours=6),
    )
    assert reader.prompts == []

    # Due again once the six hours have passed, not before.
    assert count(reader.session, reader.step, LIMIT, now=began + timedelta(hours=6)).due == 1
    assert (
        count(reader.session, reader.step, LIMIT, now=began + timedelta(hours=6, seconds=-1)).due
        == 0
    )


def test_an_address_the_reader_does_not_allow_finishes_the_lead(reader: Reader):
    lead = reader.lead()
    reader.page_reader.not_allowed["www.theguardian.com"] = "the site's rules disallow it"

    reader.read()

    assert read_ended(reader, lead) == (
        WorkOutcome.NOTHING_FOUND,
        1,
        False,
        ReadOutcome.CANNOT_BE_READ,
        "the page reader does not allow the address: the site's rules disallow it",
    )
    assert reason_of(reader, lead) == (
        "not_allowed",
        {"outlet": "theguardian.com", "why": "the site's rules disallow it"},
        None,
    )


THIN_PAGE = (
    "<html><head><title>A synthetic headline</title>"
    '<meta property="article:published_time" content="2019-05-04T08:00:00Z"></head>'
    "<body><main><p>One synthetic line.</p></main></body></html>"
)


@pytest.mark.parametrize(
    ("url", "served", "detail", "code"),
    [
        pytest.param(
            "https://www.theguardian.com/science/2019/may/04/synthetic-teeth",
            THIN_PAGE,
            "too little article text",
            "thin_page",
            id="too-little-text",
        ),
        pytest.param(
            "https://www.theguardian.com/science/2019/may/04/synthetic-teeth",
            page(published=None),
            "the page gives no publication date",
            "no_date",
            id="no-date",
        ),
        pytest.param(
            "https://www.theguardian.com/science/2019/may/04/synthetic-teeth",
            page(headline=None),
            "the page gives no headline",
            "no_headline",
            id="no-headline",
        ),
        pytest.param(
            "https://multiplesclerosisnewstoday.com/news/synthetic-report",
            page(),
            "its outlet has no display name",
            "no_outlet_name",
            id="no-outlet-name",
        ),
    ],
)
def test_a_page_that_cannot_be_used_needs_a_fix(
    reader: Reader, url: str, served: str, detail: str, code: str
):
    lead = reader.lead(url, serves=served)

    report = reader.read()

    assert (report.needs_fix, report.nothing_found, report.later) == (1, 0, 0)
    assert read_ended(reader, lead) == (
        WorkOutcome.NEEDS_FIX,
        0,
        False,
        ReadOutcome.CANNOT_BE_READ,
        detail,
    )
    assert reason_of(reader, lead) == (code, {"outlet": lead.outlet}, None)
    assert reader.prompts == []


def test_an_outlet_that_refuses_the_reader_needs_a_fix(reader: Reader):
    refused_earlier(reader, "https://www.theguardian.com/science", 5)
    lead = reader.lead()

    report = reader.read()

    assert (report.needs_fix, report.nothing_found, report.later) == (1, 0, 0)
    assert read_ended(reader, lead) == (
        WorkOutcome.NEEDS_FIX,
        0,
        False,
        ReadOutcome.CANNOT_BE_READ,
        "not asked: its outlet answered 401 to the page reader for 5 pages and served none",
    )
    assert reason_of(reader, lead) == (
        "outlet_refuses",
        {"outlet": "theguardian.com", "pages": 5},
        None,
    )
    assert reader.client.requests_made == 0


# --- link_read: a lead that may not be asked for now ---------------------------------------


def test_not_now_from_the_reader_is_put_off(reader: Reader):
    lead = reader.lead()
    reader.page_reader.not_now["www.theguardian.com"] = 600
    began = reader.time.now()

    report = reader.read(by_the_step_clock=True)

    # Put off until the wait the reader stated is over. It is a put-off lead, not a
    # deferred one: the ledger holds an entry, with no attempt and no read outcome.
    assert (report.processed, report.later, report.deferred, report.stopped) == (0, 1, 0, None)
    assert put_off(reader, lead) == (WorkOutcome.LATER, 0, None, None)
    assert reason_of(reader, lead) == (
        "reader_not_now",
        {"outlet": "theguardian.com"},
        began + timedelta(seconds=600),
    )
    assert reader.client.requests_made == 1
    assert count(reader.session, reader.step, LIMIT, now=began).due == 0
    assert count(reader.session, reader.step, LIMIT, now=began + timedelta(seconds=600)).due == 1


def test_a_held_outlet_is_put_off(reader: Reader):
    lead = reader.lead()
    until = keep(reader.client.allowances, lead.outlet, reader.time.now(), 3600)

    report = reader.read(by_the_step_clock=True)

    # Not asked at all, and put off until the hold ends.
    assert (report.processed, report.later, report.deferred, report.stopped) == (0, 1, 0, None)
    assert put_off(reader, lead) == (WorkOutcome.LATER, 0, None, None)
    assert reason_of(reader, lead) == ("outlet_held", {"outlet": "theguardian.com"}, until)
    assert (reader.client.requests_made, reader.page_reader.asked) == (0, [])
    assert count(reader.session, reader.step, LIMIT, now=reader.time.now()).due == 0
    assert count(reader.session, reader.step, LIMIT, now=until).due == 1


# --- link_read: the model read and the decisions --------------------------------------------

# As `Reader` configures its model: a name for the fake, the ceiling and the prices.
SETTINGS = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))


def test_a_model_outage_in_the_read_fails_the_lead(reader: Reader):
    def offline(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise httpx.ConnectError("synthetic outage")

    model = FunctionModel(offline, model_name="scripted")
    reader.client.make_llm = lambda at: Llm(at, SETTINGS, model=model, now=lambda: NOW)
    lead = reader.lead()

    first = reader.read()

    assert (first.failed, first.stopped) == (1, None)
    assert read_ended(reader, lead) == (WorkOutcome.FAILED, 1, True, None, None)
    entry = entry_of(reader.session, reader.step, lead)
    assert entry is not None
    assert entry.error == "The language model call failed (ConnectError)."

    # Due until its attempts reach the limit, one attempt a run.
    reader.read()
    reader.read()

    assert read_ended(reader, lead) == (WorkOutcome.FAILED, LIMIT, False, None, None)
    assert reader.read().processed == 0


def test_an_invalid_read_fails_the_lead(session: Session, fake_time):
    reader = Reader(session, fake_time, {"headline": "Only a synthetic headline"})
    lead = reader.lead()

    reader.read()

    assert read_ended(reader, lead) == (WorkOutcome.FAILED, 1, True, None, None)
    entry = entry_of(session, reader.step, lead)
    assert entry is not None
    assert (entry.error or "").startswith("The model's output failed validation on every attempt.")


def test_the_spend_ceiling_in_the_read_stops_the_run(reader: Reader):
    reader.session.add(
        LlmUsage(
            purpose="synthetic earlier spend",
            model="synthetic-model",
            input_tokens=0,
            output_tokens=0,
            cost_usd=Decimal("10"),
            created_at=NOW,
        )
    )
    lead = reader.lead()

    report = reader.read()

    assert report.stopped == (
        "The monthly ceiling of $10 for language model calls has been reached. No call was made."
    )
    assert (report.processed, report.deferred, report.remaining_due) == (0, 0, 1)
    assert read_ended(reader, lead) == (None, None, True, None, None)


class TreatmentKindFails(Verticals):
    """The test backend, with the treatment-kind decision raising the fault given."""

    def __init__(self, fault: Exception) -> None:
        super().__init__()
        self.fault = fault

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        if step == TREATMENT_KIND:
            raise self.fault
        return super().answer(step, state, options)


@pytest.mark.parametrize(
    ("fault", "error"),
    [
        pytest.param(
            RuntimeError("synthetic fault"), "The fake backend failed (RuntimeError).", id="fault"
        ),
        pytest.param(
            LlmCallFailed("The decision call failed (ConnectError)."),
            "The decision call failed (ConnectError).",
            id="unreachable",
        ),
    ],
)
def test_a_failed_treatment_kind_decision_fails_the_lead(
    reader: Reader, fault: Exception, error: str
):
    reader.backend = TreatmentKindFails(fault)
    lead = reader.lead()

    report = reader.read()

    assert (report.failed, report.stopped) == (1, None)
    assert read_ended(reader, lead) == (WorkOutcome.FAILED, 1, True, None, None)
    entry = entry_of(reader.session, reader.step, lead)
    assert entry is not None and entry.error == error
    # What the failure wrote is kept: the logged decision and the read's cost.
    [logged] = reader.session.scalars(
        select(DecisionLog).where(DecisionLog.step == TREATMENT_KIND)
    ).all()
    assert logged.error == error
    assert len(reader.session.scalars(select(LlmUsage)).all()) == 1


# --- link_triage ---------------------------------------------------------------------------


def test_a_scored_lead_is_done(session: Session):
    [lead] = add_leads(session, ["A trial result"])

    report = triage(session, Headlines(session))

    assert (report.done, report.failed) == (1, 0)
    assert ended(session, LinkTriage(), lead) == (WorkOutcome.DONE, 1, False)
    assert lead.triage_score == pytest.approx(0.9)


def test_a_lead_its_batch_left_unanswered_fails_alone(session: Session):
    answered, unanswered = add_leads(session, ["A trial result", "An unanswerable headline"])

    report = triage(session, Headlines(session))

    assert (report.done, report.failed, report.stopped) == (1, 1, None)
    assert ended(session, LinkTriage(), answered) == (WorkOutcome.DONE, 1, False)
    assert ended(session, LinkTriage(), unanswered) == (WorkOutcome.FAILED, 1, True)
    entry = entry_of(session, LinkTriage(), unanswered)
    # Asked again alone, through the many-item call, which gives no answer for it.
    assert entry is not None and entry.error == "The backend gave no answer for this item."
    assert unanswered.triage_score is None


# --- link_screen ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "outcome"),
    [
        ("https://www.bbc.co.uk/news/health-synthetic-report", ScreenOutcome.IN_SCOPE),
        ("https://github.com/example/synthetic-repository", ScreenOutcome.UNLISTED_OUTLET),
        (
            "https://amp.theguardian.com/science/2019/synthetic-report?utm_source=share",
            ScreenOutcome.ALREADY_TRACKED,
        ),
    ],
    ids=["in-scope", "unlisted-outlet", "already-tracked"],
)
def test_screening_is_done_whatever_it_finds(session: Session, url: str, outcome: ScreenOutcome):
    tracked = screened_claim(session)
    add_article(
        session,
        tracked.slug,
        url="https://www.theguardian.com/science/2019/synthetic-report",
        outlet="The Guardian",
        title="A synthetic headline",
        published_date=date(2019, 5, 4),
    )
    lead = share(session, url)

    screen(session)

    assert lead.screen_outcome is outcome
    assert ended(session, LinkScreen(), lead) == (WorkOutcome.DONE, 1, False)


# --- news_search ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("stories", "outcome"),
    [([story("a")], WorkOutcome.DONE), ([], WorkOutcome.NOTHING_FOUND)],
    ids=["done", "nothing-found"],
)
def test_a_news_search_that_answers_is_finished(
    session: Session, fake_time, stories: list, outcome: WorkOutcome
):
    [trial] = add_trials(session, 1)

    step, _ = search(session, Index({query_for("drug 0", "condition"): stories}), fake_time)

    assert ended(session, step, trial) == (outcome, 1, False)


def test_a_news_index_that_fails_fails_the_trial(session: Session, fake_time):
    [trial] = add_trials(session, 1)
    client = media_cloud(session, fake_time, Service(httpx.Response(503)))
    step = NewsSearch(time=fake_time)

    report = run_step(same_session(session), step, client, now=fake_time.now, attempt_limit=LIMIT)

    assert (report.failed, report.stopped) == (1, None)
    assert ended(session, step, trial) == (WorkOutcome.FAILED, 1, True)
    entry = entry_of(session, step, trial)
    assert entry is not None
    assert entry.error == "SourceUnavailable: mediacloud answered with status 503."
