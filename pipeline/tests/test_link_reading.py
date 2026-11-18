"""Reading a passed link lead's article into a source article or a new claim. Scenario
names are from openspec lead-reading. The outlets, pages and model here are fakes, and
every word of every page is synthetic: no article text may be stored, tests included."""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backfill_support import same_session
from reader_support import SyntheticReader, retriever
from thenwhat.backfill.article_evidence import ArticleMatches
from thenwhat.backfill.link_funnel import funnel
from thenwhat.backfill.link_read import (
    CLAIM_IDENTITY_LOCK,
    NO_DATE,
    NO_HEADLINE,
    NO_NAME,
    NO_PAGE,
    NOT_ALLOWED,
    OUTLET_REFUSES,
    REFUSALS_BEFORE_STOPPING,
    LinkRead,
    NotMeasured,
    ReadClient,
    held_outlets,
    reads_naming_archived_claims,
    reads_naming_live_claims,
)
from thenwhat.backfill.link_screen import (
    CANDIDATE,
    EXACT,
    NAMED,
    REGISTRY_TRIAL,
    STRONG,
    TITLE_NAMES_CLAIM,
)
from thenwhat.backfill.outlet_hold import OUTLET_HOLD, OUTLET_TURN_LOCK
from thenwhat.backfill.trial_links import SetPlan, UnknownStrength, at_least, plan_of
from thenwhat.claims.entry import (
    add_article,
    add_claim,
    archive_claim,
    articles_of,
    slug_for,
)
from thenwhat.config import SourceAllowance
from thenwhat.db.models import (
    Base,
    Claim,
    LinkLead,
    LinkLeadLabel,
    LinkLeadLink,
    LinkShare,
    LlmUsage,
    RegistryTrial,
    SourceArticle,
    WorkEntry,
)
from thenwhat.decide.core import BackendAnswer
from thenwhat.decide.steps import (
    BUSINESS_NEWS,
    ESTABLISHED_TREATMENT,
    NEW_TREATMENT,
    NO_SUCH_CLAIM,
    NOT_ONE_TREATMENT,
    SAME_CLAIM,
    TREATMENT_KIND,
)
from thenwhat.domain import (
    Decider,
    LeadVerdict,
    OutletKind,
    ReadOutcome,
    ReviewState,
    ScreenOutcome,
    WorkOutcome,
)
from thenwhat.extract.retrieve import READER
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.review.decisions import record_decision
from thenwhat.statements.service import StatementChecker
from thenwhat.work.allowance import Allowances
from thenwhat.work.errors import CannotAsk
from thenwhat.work.ledger import count
from thenwhat.work.runner import RunReport, run_step

NOW = datetime(2026, 11, 20, 10, 0, tzinfo=UTC)
WHEN = datetime(2019, 5, 6, 10, 30, tzinfo=UTC)
MARKER = "The zebra-striped molars glowed under ultraviolet lamps."
SHARED_TITLE = "words a person wrote when sharing the link"
HEADLINE = "Antibody regrows teeth in mice, a synthetic study says"
DRAFT: dict[str, Any] = {
    "headline": "Antibody regrows teeth in mice",
    "summary": "An antibody restored missing teeth in mice.",
    "intervention": "EX-1 antibody",
    "intervention_synonyms": ["EX-1"],
    "indication": "tooth agenesis",
}


def page(*, headline: str | None = HEADLINE, published: str | None = "2019-05-04T08:00:00Z") -> str:
    head = ""
    if headline:
        head += f'<title>{headline}</title><meta property="og:title" content="{headline}">'
    if published:
        head += f'<meta property="article:published_time" content="{published}">'
    body = f"<p>Synthetic scientists say an antibody called EX-1 regrew teeth in mice. {MARKER}</p>"
    return f"<html><head>{head}</head><body><main>{body * 8}</main></body></html>"


class Web:
    """Outlets that serve synthetic pages. Counts what each host was asked for."""

    def __init__(self) -> None:
        self.pages: dict[str, str] = {}
        self.asked: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        host, path = request.url.host, request.url.path
        self.asked.append(f"{host}{path}")
        found = self.pages.get(f"{host}{path}")
        return httpx.Response(200, text=found) if found else httpx.Response(404)


class Verticals:
    """A decision backend that chooses one vertical with one probability, says which
    claim, if any, an article reports, and says every reported statement is in its
    article."""

    name = "fake"

    def __init__(self, vertical: str = "mouth-and-teeth", probability: float = 0.93) -> None:
        self.vertical = vertical
        self.probability = probability
        # The slug the same-claim decision chooses, or None for "none of these".
        self.same_claim: str | None = None
        self.same_claim_probability = 0.9
        # Or every answer's probability, spelled out, when a test needs a split vote.
        self.same_claim_chances: dict[str, float] | None = None
        # What the same-claim decision was shown, each time it was asked.
        self.same_claim_asked: list[str] = []
        # What the treatment-kind decision answers (a new treatment unless a test says
        # otherwise), with what probability, and what it was shown.
        self.report_kind = NEW_TREATMENT
        self.report_probability = 0.95
        self.report_asked: list[str] = []

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        chosen, probability = self.vertical, self.probability
        if step == TREATMENT_KIND:
            self.report_asked.append(state)
            chosen, probability = self.report_kind, self.report_probability
        if step == SAME_CLAIM:
            self.same_claim_asked.append(state)
            if self.same_claim_chances is not None:
                chances = {option: self.same_claim_chances.get(option, 0.0) for option in options}
                return BackendAnswer(max(chances, key=lambda option: chances[option]), chances)
            chosen, probability = self.same_claim or NO_SUCH_CLAIM, self.same_claim_probability
        rest = (1 - probability) / (len(options) - 1)
        chances = {option: rest for option in options}
        chances[chosen] = probability
        return BackendAnswer(chosen, chances)

    def answer_many(self, step, intro, question, items, options):
        rest = 0.1 / (len(options) - 1)
        return [
            BackendAnswer(options[0], {o: 0.9 if o == options[0] else rest for o in options})
            for _ in items
        ]


class Reader:
    """Everything a test needs to read leads: the fake web, the scripted model, the
    decision backend, and the step with thresholds of 0.7 and 0.2."""

    def __init__(self, session: Session, fake_time, *drafts: dict[str, Any]) -> None:
        self.session = session
        self.web = Web()
        self.page_reader = SyntheticReader(self.web)
        self.prompts: list[str] = []
        self.backend = Verticals()
        self.time = fake_time
        remaining = list(drafts or [DRAFT])

        def respond(messages, info) -> ModelResponse:
            self.prompts.append(str(messages))
            output = remaining.pop(0) if len(remaining) > 1 else remaining[0]
            return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, output)])

        model = FunctionModel(respond, model_name="scripted")
        settings = LlmSettings("test:scripted", Decimal("10"), Decimal("3"), Decimal("15"))
        self.client = ReadClient(
            retriever=retriever(self.page_reader),
            allowances=Allowances(
                same_session(session),
                {READER: SourceAllowance(requests=1000, period_hours=24, interval_seconds=1)},
                fake_time,
            ),
            make_llm=lambda at: Llm(at, settings, model=model, now=lambda: NOW),
            make_checker=lambda at: StatementChecker(self.backend),
            make_backend=lambda at: self.backend,
        )
        self.step = step(time=fake_time)

    def lead(
        self,
        url: str = "https://www.theguardian.com/science/2019/may/04/synthetic-teeth",
        *,
        score: float | None = 0.9,
        shares: int = 10,
        shared_at: datetime = WHEN,
        serves: str | None = "",
    ) -> LinkLead:
        from thenwhat.backfill.address import article_key

        key = article_key(url) or url
        outlet = key.split("/", 1)[0]
        record = LinkLead(
            url=url,
            url_key=key,
            outlet=outlet,
            outlet_kind=OutletKind.GENERAL_NEWS,
            title=SHARED_TITLE,
            first_shared_at=shared_at,
            screen_outcome=ScreenOutcome.IN_SCOPE,
            triage_score=score,
            triage_version=1 if score is not None else None,
        )
        self.session.add(record)
        self.session.flush()
        self.session.add(
            LinkShare(
                link_lead_id=record.id,
                platform="reddit",
                community="science",
                shared_at=shared_at,
                score=shares,
            )
        )
        self.session.flush()
        if serves is not None:
            split = httpx.URL(url)
            self.web.pages[f"{split.host}{split.path}"] = serves or page()
        return record

    def read(self, limit: int | None = None, *, by_the_step_clock: bool = False) -> RunReport:
        """One run. It is given a fixed time, unless `by_the_step_clock`: then the run's
        time is the test's, which the step's waits are counted from, so that a lead put
        off comes back when the test moves time on."""
        return run_step(
            same_session(self.session),
            self.step,
            self.client,
            now=self.time.now if by_the_step_clock else (lambda: NOW),
            attempt_limit=3,
            limit=limit,
        )

    def entry(self, record: LinkLead) -> WorkEntry:
        return self.session.scalars(
            select(WorkEntry).where(WorkEntry.step == "link_read", WorkEntry.record_id == record.id)
        ).one()


def step(**changes: Any) -> LinkRead:
    settings: dict[str, Any] = {
        "pass_above": 0.7,
        "reject_below": 0.2,
        "triage_version": 1,
        "min_labels": 2,
        "reads_per_claim": 3,
        "vertical_accept_above": 0.8,
        "approve_drafts_by_rule": True,
    }
    return LinkRead(**(settings | changes))


@pytest.fixture
def reader(session: Session, fake_time) -> Reader:
    return Reader(session, fake_time)


def tracked_claim(session: Session, articles: int = 1, first: date = date(2021, 3, 1)) -> Claim:
    claim = add_claim(
        session,
        slug="ex-1-tooth-agenesis",
        headline="The reviewed headline",
        vertical="mouth-and-teeth",
        intervention="EX-1 antibody",
        indication="tooth agenesis",
        summary="The reviewed summary.",
    )
    for number in range(articles):
        add_article(
            session,
            claim.slug,
            url=f"https://news.example.org/2021/teeth-{number}",
            outlet="The Example",
            title="A synthetic headline",
            published_date=first,
        )
    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    session.flush()
    return claim


def claim_of(session: Session, lead: LinkLead) -> Claim:
    """The claim a read lead points at."""
    return session.scalars(select(Claim).where(Claim.id == lead.claim_id)).one()


def stored_everywhere(session: Session) -> str:
    """Every value in every table, as one text to search."""
    found = []
    for table in Base.metadata.sorted_tables:
        for row in session.execute(text(f'SELECT * FROM "{table.name}"')):  # noqa: S608
            found.append(repr(tuple(row)))
    return "\n".join(found)


# --- a new claim -----------------------------------------------------------------------


def test_a_read_measures_its_waits_for_a_turn_under_their_own_causes(reader: Reader):
    """Scenario: A read that waits for the claim turn (openspec processing-metrics,
    "Every wait is given its cause"). A read that waits for nobody still names the turns
    it took, so a slow one shows under them."""
    from test_measure import AT, Kept, Ticks
    from thenwhat.measure import spans as measure

    reader.lead("https://www.theguardian.com/science/2019/may/04/synthetic-teeth")
    kept = Kept()
    measure.use(measure.Recorder(out=kept, writer="test", clock=Ticks(), now=lambda: AT))
    try:
        report = reader.read()
    finally:
        measure.use(None)

    assert report.done == 1
    waited = {cause for span in kept.spans for cause in span.waited}
    assert {"claim_turn", "outlet_turn"} <= waited


def test_a_passed_lead_is_read_into_a_new_claim_from_its_own_page(reader: Reader):
    """Scenarios: A named intervention, A listed outlet, A date the page gives in a tag,
    A shared title that differs from the headline"""
    lead = reader.lead(
        "https://www.theguardian.com/science/2019/may/04/synthetic-teeth?utm_source=reddit"
    )

    report = reader.read()

    assert (report.done, lead.read_outcome) == (1, ReadOutcome.NEW_CLAIM)
    claim = claim_of(reader.session, lead)
    assert (claim.slug, claim.vertical) == ("ex-1-antibody-tooth-agenesis", "mouth-and-teeth")
    # Not approved by the read: it waits for its registries to be searched.
    assert (claim.review_state, claim.reviewed_by) == (ReviewState.PENDING, None)
    [article] = articles_of(reader.session, claim)
    assert article.id == lead.source_article_id
    assert (article.outlet, article.title) == ("The Guardian", HEADLINE)
    assert article.published_date == date(2019, 5, 4)
    assert claim.first_reported_date == date(2019, 5, 4)
    # Published without what would say where it was shared.
    assert article.url == "https://www.theguardian.com/science/2019/may/04/synthetic-teeth"
    assert article.content_hash
    assert reader.entry(lead).outcome is WorkOutcome.DONE


def test_the_articles_text_is_stored_nowhere_and_it_is_read_once(reader: Reader):
    """Scenario: After a read"""
    reader.lead()

    reader.read()
    again = reader.read()

    assert MARKER in reader.prompts[0]  # the model was shown the article
    assert MARKER not in stored_everywhere(reader.session)
    assert (again.processed, len(reader.prompts)) == (0, 1)


def test_a_backfill_window_checks_the_share_and_the_publisher_date(reader: Reader):
    first, last = date(2019, 5, 4), date(2019, 5, 9)
    reader.step = step(time=reader.time, window=(first, last))
    outside = reader.lead("https://www.bbc.com/news/future", shared_at=WHEN + timedelta(days=4))
    old_page = reader.lead(
        "https://www.bbc.com/news/archived",
        shared_at=WHEN + timedelta(days=3, hours=13),
        serves=page(published="2019-05-03T11:00:00Z"),
    )

    report = reader.read()

    assert report.processed == 1
    assert outside.read_outcome is None
    assert old_page.claim_id is None
    assert reader.prompts == []
    assert reader.entry(old_page).reason == "outside_publication_window"


def test_a_daily_batch_keeps_an_earlier_publisher_date_in_the_full_window(reader: Reader):
    reader.step = step(
        time=reader.time,
        window=(date(2019, 5, 4), date(2019, 5, 9)),
        batch_day=WHEN.date(),
    )
    in_batch = reader.lead()
    next_day = reader.lead("https://www.bbc.com/news/next", shared_at=WHEN + timedelta(days=1))

    report = reader.read()

    assert report.processed == 1
    assert next_day.read_outcome is None
    article = reader.session.get(SourceArticle, in_batch.source_article_id)
    assert article is not None and article.published_date == date(2019, 5, 4)


# --- a claim that exists ---------------------------------------------------------------


def test_an_article_for_a_tracked_claim_is_added_and_the_claim_is_left_as_reviewed(
    reader: Reader,
):
    """Scenarios: An earlier report of a tracked claim, A decided claim"""
    claim = tracked_claim(reader.session)
    reader.backend.same_claim = claim.slug
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    assert len(articles_of(reader.session, claim)) == 2
    assert claim.first_reported_date == date(2019, 5, 4)
    assert (claim.headline, claim.summary) == ("The reviewed headline", "The reviewed summary.")
    assert (claim.review_state, claim.reviewed_by) == (ReviewState.APPROVED, Decider.HUMAN)
    assert reader.session.scalars(select(Claim)).all() == [claim]
    assert len(reader.backend.same_claim_asked) == 1


def test_a_lead_whose_article_became_tracked_is_not_fetched_or_read(reader: Reader):
    """Scenario: Tracked since it was screened"""
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

    assert (lead.screen_outcome, lead.claim_id) == (ScreenOutcome.ALREADY_TRACKED, claim.id)
    assert (reader.web.asked, reader.prompts) == ([], [])


# --- what is settled without the model ---------------------------------------------------


def test_a_lead_that_is_held_rejected_or_unscored_is_not_read(reader: Reader):
    """Scenario: A held lead"""
    for number, score in enumerate((0.5, 0.1, None)):
        reader.lead(f"https://www.theguardian.com/science/2019/may/04/other-{number}", score=score)

    report = reader.read()

    assert (report.processed, reader.web.asked, reader.prompts) == (0, [], [])


def test_with_a_threshold_unset_nothing_is_in_scope(reader: Reader):
    reader.lead()
    reader.step = step(pass_above=None)

    assert reader.read().processed == 0


def test_a_calibrated_read_uses_only_scores_from_its_own_triage_version(reader: Reader):
    reader.lead("https://example.com/old-score", score=0.9)
    current = reader.lead("https://example.com/current-score", score=0.8)
    below = reader.lead("https://example.com/below-cutoff", score=0.78)
    current.triage_version = below.triage_version = 2
    reader.session.flush()
    calibrated = step(
        pass_above=0.7883,
        reject_below=0.7883,
        triage_version=2,
        use_current_triage_only=True,
    )

    assert list(reader.session.scalars(select(LinkLead.id).where(calibrated.scope()))) == [
        current.id
    ]


def test_a_lead_the_reader_does_not_allow_cannot_be_read_and_is_not_retried(reader: Reader):
    """Scenario: Not allowed"""
    lead = reader.lead()
    reader.page_reader.not_allowed["www.theguardian.com"] = "the site's rules disallow it"

    first = reader.read()
    second = reader.read()

    assert lead.read_outcome is ReadOutcome.CANNOT_BE_READ
    assert lead.read_detail == f"{NOT_ALLOWED}: the site's rules disallow it"
    assert (first.nothing_found, second.processed) == (1, 0)
    assert (reader.web.asked, reader.prompts) == ([], [])


def test_a_lead_whose_site_cannot_be_asked_now_is_put_off_and_the_run_goes_on(reader: Reader):
    """Scenario: Not now"""
    busy = reader.lead()
    other = reader.lead("https://www.bbc.co.uk/news/health-synthetic-teeth")
    reader.page_reader.not_now["www.theguardian.com"] = 600
    began = reader.time.now()

    report = reader.read(by_the_step_clock=True)

    # Put off until the wait the reader stated is over: no outcome on the lead, no
    # attempt, the reason a code. The other outlet's lead is read.
    assert (report.later, report.needs_fix) == (1, 0)
    assert (busy.read_outcome, busy.read_detail) == (None, None)
    entry = reader.entry(busy)
    assert (entry.outcome, entry.attempts, entry.reason) == (
        WorkOutcome.LATER,
        0,
        "reader_not_now",
    )
    assert entry.reason_values is not None and entry.reason_values["outlet"] == "theguardian.com"
    assert entry.not_before == began + timedelta(seconds=600)
    assert other.read_outcome is ReadOutcome.NEW_CLAIM
    assert (report.remaining_due, count(reader.session, reader.step, 3, now=began).due) == (0, 0)

    # Not due while the wait lasts; due once it is over, and then, the site answering,
    # read.
    assert entry.not_before is not None
    reader.time.advance(entry.not_before - timedelta(seconds=1) - reader.time.now())
    assert count(reader.session, reader.step, 3, now=reader.time.now()).due == 0
    reader.page_reader.not_now.clear()
    reader.time.advance(timedelta(seconds=1))
    assert count(reader.session, reader.step, 3, now=reader.time.now()).due == 1
    reader.read(by_the_step_clock=True)

    # Read now: the other lead's claim has the same names, so it is left unresolved.
    assert busy.read_outcome is not None
    entry = reader.entry(busy)
    assert (entry.outcome, entry.attempts, entry.not_before) == (WorkOutcome.NOTHING_FOUND, 1, None)


# Four leads of a stopped outlet: three left unasked while it is held, one that was told.
WAITING = [
    (WorkOutcome.LATER, 0, "outlet_held"),
    (WorkOutcome.LATER, 0, "outlet_held"),
    (WorkOutcome.LATER, 0, "outlet_held"),
    (WorkOutcome.LATER, 0, "reader_not_now"),
]


def test_an_outlet_the_reader_has_stopped_is_not_asked_until_its_wait_is_over(reader: Reader):
    """Scenario: An outlet the reader has stopped is left until its wait is over"""
    stopped = [
        reader.lead(f"https://www.theguardian.com/science/2019/may/0{n}/synthetic-teeth-{n}")
        for n in range(1, 5)
    ]
    other = reader.lead("https://www.bbc.co.uk/news/health-synthetic-teeth")
    reader.page_reader.not_now["www.theguardian.com"] = 7200

    def asked_of_the_outlet() -> int:
        return sum("theguardian.com" in body["url"] for body in reader.page_reader.asked)

    def waiting() -> list[tuple[WorkOutcome, int, str | None]]:
        return sorted(
            (
                (entry.outcome, entry.attempts, entry.reason)
                for entry in (reader.entry(lead) for lead in stopped)
            ),
            key=lambda held: held[2] or "",
        )

    began = reader.time.now()
    first = reader.read(by_the_step_clock=True)

    # One request told the pipeline; the outlet's other leads cost none. Another outlet
    # is read as usual. All four are put off until the wait the reader stated is over.
    assert (asked_of_the_outlet(), first.later) == (1, 4)
    assert other.read_outcome is ReadOutcome.NEW_CLAIM
    assert waiting() == WAITING
    assert {reader.entry(lead).not_before for lead in stopped} == {began + timedelta(seconds=7200)}
    # The plan still says which outlet is held, for how long and how many leads wait.
    [held] = held_outlets(reader.session, reader.step, 3, reader.time.now())
    assert (held.outlet, held.leads) == ("theguardian.com", 4)
    assert held.until == began + timedelta(seconds=7200)
    assert all(lead.read_outcome is None for lead in stopped)
    assert count(reader.session, reader.step, 3, now=reader.time.now()).due == 0

    # The next run, an hour on, is a new step with nothing remembered: still no request,
    # no attempt, no outcome, and the four are not due.
    reader.time.advance(timedelta(hours=1))
    reader.step = step(time=reader.time)
    second = reader.read(by_the_step_clock=True)

    assert (asked_of_the_outlet(), second.later, second.processed) == (1, 0, 0)
    assert all(lead.read_outcome is None for lead in stopped)
    assert waiting() == WAITING

    # After the wait the outlet is asked again and, answering, is read.
    reader.page_reader.not_now.clear()
    reader.time.advance(timedelta(hours=1, seconds=1))
    assert count(reader.session, reader.step, 3, now=reader.time.now()).due == 4
    reader.step = step(time=reader.time)
    reader.read(by_the_step_clock=True)

    assert asked_of_the_outlet() == 5
    assert all(lead.read_outcome is not None for lead in stopped)
    assert held_outlets(reader.session, reader.step, 3, reader.time.now()) == []


def test_the_reader_down_ends_the_run_with_leads_due_and_attempts_unchanged(reader: Reader):
    """Scenario: The reader's machine is down during a backfill run"""
    first = reader.lead()
    reader.lead("https://www.bbc.co.uk/news/health-synthetic-teeth")
    reader.page_reader.answer = lambda: httpx.Response(503)

    report = reader.read()

    assert report.stopped is not None and "page reader" in report.stopped
    assert (report.processed, report.remaining_due) == (0, 2)
    assert first.read_outcome is None
    assert (
        reader.session.scalars(select(WorkEntry).where(WorkEntry.step == "link_read")).all() == []
    )


def test_an_outlet_with_no_display_name_is_not_fetched(reader: Reader):
    """Scenario: An outlet with no display name"""
    lead = reader.lead("https://multiplesclerosisnewstoday.com/news/synthetic-report")

    reader.read()

    assert (lead.read_outcome, lead.read_detail) == (ReadOutcome.CANNOT_BE_READ, NO_NAME)
    assert (reader.web.asked, reader.prompts) == ([], [])


def test_a_page_with_no_date_is_not_read_by_the_model(reader: Reader):
    """Scenarios: A page with no date, A date that cannot be read"""
    undated = reader.lead(serves=page(published=None))
    unreadable = reader.lead(
        "https://www.theguardian.com/science/2019/may/04/other", serves=page(published="last week")
    )

    reader.read()

    assert (undated.read_outcome, undated.read_detail) == (ReadOutcome.CANNOT_BE_READ, NO_DATE)
    assert unreadable.read_detail == NO_DATE
    assert reader.prompts == []
    assert reader.session.scalars(select(Claim)).all() == []


def test_a_page_with_no_headline_is_not_read_by_the_model(reader: Reader):
    """Scenario: A page with no headline"""
    lead = reader.lead(serves=page(headline=None))

    reader.read()

    assert (lead.read_detail, reader.prompts) == (NO_HEADLINE, [])


def test_a_page_the_site_did_not_serve_cannot_be_read(reader: Reader):
    """Scenario: The site did not serve the page"""
    lead = reader.lead(serves=None)

    reader.read()

    assert lead.read_outcome is ReadOutcome.CANNOT_BE_READ
    assert lead.read_detail == f"{NO_PAGE} (the site answered 404)"
    assert reader.prompts == []


def refused_earlier(reader: Reader, outlet_url: str, count: int, *, days_ago: int = 1) -> None:
    """Leads of the outlet read before, each answered 401 by the site, `days_ago` by
    the test's clock, which the step is given."""
    reader.step = step(time=reader.time)
    for number in range(count):
        earlier = reader.lead(f"{outlet_url}/refused-{number}", score=None, serves=None)
        earlier.read_outcome = ReadOutcome.CANNOT_BE_READ
        earlier.read_detail = f"{NO_PAGE} (the site answered 401)"
        reader.session.add(
            WorkEntry(
                record_kind="link_lead",
                record_id=earlier.id,
                step="link_read",
                step_version=1,
                outcome=WorkOutcome.NOTHING_FOUND,
                attempts=1,
                requests_used=1,
                fingerprint="earlier",
                last_attempt_at=reader.time.now() - timedelta(days=days_ago),
            )
        )
    reader.session.flush()


def test_an_outlets_old_refusals_lapse(reader: Reader):
    """Scenario: Refusals that have lapsed"""
    refused_earlier(
        reader, "https://www.theguardian.com/science", REFUSALS_BEFORE_STOPPING, days_ago=31
    )
    lead = reader.lead()

    reader.read()

    assert reader.client.requests_made == 1
    assert lead.read_detail is None or OUTLET_REFUSES not in lead.read_detail


def test_an_outlet_that_refuses_the_reader_page_after_page_is_not_asked_again(reader: Reader):
    """Scenario: An outlet that refuses the reader"""
    refused_earlier(reader, "https://www.theguardian.com/science", REFUSALS_BEFORE_STOPPING)
    lead = reader.lead()

    reader.read()

    assert lead.read_outcome is ReadOutcome.CANNOT_BE_READ
    assert lead.read_detail == (
        f"{OUTLET_REFUSES} for {REFUSALS_BEFORE_STOPPING} pages and served none"
    )
    assert (reader.client.requests_made, reader.prompts) == (0, [])


def test_an_outlet_that_served_a_page_is_still_asked(reader: Reader):
    """Scenario: An outlet that served a page"""
    refused_earlier(reader, "https://www.theguardian.com/science", REFUSALS_BEFORE_STOPPING)
    served = reader.lead("https://www.theguardian.com/science/served", score=None, serves=None)
    served.read_outcome = ReadOutcome.NOT_ONE_TREATMENT
    lead = reader.lead()

    reader.read()

    assert reader.client.requests_made == 1
    assert lead.read_detail is None or OUTLET_REFUSES not in lead.read_detail


def test_two_leads_on_one_outlet_are_both_asked_of_the_reader(reader: Reader):
    """Scenario: Two articles of one outlet read side by side. How far apart the outlet
    is asked is the reader's doing: the pipeline keeps only the reader's allowance."""
    reader.lead()
    reader.lead(
        "https://www.theguardian.com/science/2019/may/04/other", serves=page(published=None)
    )

    reader.read()

    assert [body["url"] for body in reader.page_reader.asked] == [
        "https://www.theguardian.com/science/2019/may/04/synthetic-teeth",
        "https://www.theguardian.com/science/2019/may/04/other",
    ]
    assert reader.time.slept == [1.0]  # the reader's allowance, not the outlet's


# --- enough articles, and the order of reading -------------------------------------------


def link(
    session: Session,
    lead: LinkLead,
    kind: str,
    record_id: int,
    reason: str,
    strength: str | None = None,
) -> None:
    session.add(
        LinkLeadLink(
            link_lead_id=lead.id,
            record_kind=kind,
            record_id=record_id,
            reason=reason,
            strength=strength,
        )
    )
    session.flush()


def test_a_lead_for_a_claim_with_enough_articles_is_held_unless_it_is_earlier(reader: Reader):
    """Scenarios: A much-reported claim, An earlier article"""
    claim = tracked_claim(reader.session, articles=3, first=date(2021, 3, 1))
    reader.backend.same_claim = claim.slug
    later = reader.lead(
        "https://www.theguardian.com/science/2022/jan/04/later",
        shared_at=datetime(2022, 1, 4, tzinfo=UTC),
    )
    earlier = reader.lead(shared_at=datetime(2019, 5, 6, tzinfo=UTC))
    for lead in (later, earlier):
        link(reader.session, lead, "claim", claim.id, TITLE_NAMES_CLAIM)

    reader.read()

    assert later.read_outcome is ReadOutcome.ENOUGH_ARTICLES
    assert "ex-1-tooth-agenesis" in (later.read_detail or "")
    assert earlier.read_outcome is ReadOutcome.ADDED_TO_CLAIM
    assert reader.web.asked == ["www.theguardian.com/science/2019/may/04/synthetic-teeth"]


def test_a_lead_linked_to_a_registry_trial_is_read_first(reader: Reader):
    """Scenario: Two leads, one linked to a trial"""
    widely_shared = reader.lead(
        "https://www.theguardian.com/science/2019/may/04/widely-shared", shares=5000
    )
    linked = reader.lead("https://www.bbc.com/news/health-1", shares=3)
    link(reader.session, linked, REGISTRY_TRIAL, 1, "synthetic")

    reader.read(limit=1)

    assert reader.web.asked == ["www.bbc.com/news/health-1"]
    assert (linked.read_outcome, widely_shared.read_outcome) == (ReadOutcome.NEW_CLAIM, None)


# --- a set of trials being worked (openspec trial-report-links) -------------------------


def under_way(session: Session, phases: tuple[str, ...] = ("PHASE3",)) -> RegistryTrial:
    """A stored trial in the set `active-since-2025`."""
    number = session.scalar(select(func.count()).select_from(RegistryTrial)) or 0
    record = RegistryTrial(
        registry_name="demo-registry",
        external_id=f"S{number:04d}",
        title="A synthetic trial",
        conditions=["synthetic condition"],
        interventions=[],
        phases=list(phases),
        overall_status="RECRUITING",
        last_update_posted=date(2026, 3, 1),
        raw_payload={},
        fetched_at=NOW,
    )
    session.add(record)
    session.flush()
    return record


def test_a_held_lead_is_read_only_on_a_strong_link_to_the_set_being_worked(reader: Reader):
    """Scenarios: A held lead with a strong link, A rejected lead with a strong link"""
    reader.step = step(trial_set="active-since-2025")
    in_the_set = under_way(reader.session)
    held_strong = reader.lead("https://www.bbc.com/news/health-40", score=0.4)
    held_exact = reader.lead("https://www.bbc.com/news/health-41", score=0.4)
    held_named = reader.lead("https://www.bbc.com/news/health-42", score=0.4)
    held_candidate = reader.lead("https://www.bbc.com/news/health-43", score=0.4)
    rejected = reader.lead("https://www.bbc.com/news/health-44", score=0.1)
    for lead, strength in (
        (held_strong, STRONG),
        (held_exact, EXACT),
        (held_named, NAMED),
        (held_candidate, CANDIDATE),
        (rejected, STRONG),
    ):
        link(reader.session, lead, REGISTRY_TRIAL, in_the_set.id, "synthetic", strength)

    reader.read()

    assert held_strong.read_outcome is not None and held_exact.read_outcome is not None
    assert (held_named.read_outcome, held_candidate.read_outcome) == (None, None)
    assert rejected.read_outcome is None


def test_a_held_lead_strongly_linked_to_a_trial_outside_the_set_is_not_read(reader: Reader):
    reader.step = step(trial_set="active-since-2025")
    outside = under_way(reader.session)
    outside.overall_status = "COMPLETED"
    held = reader.lead("https://www.bbc.com/news/health-45", score=0.4)
    link(reader.session, held, REGISTRY_TRIAL, outside.id, "synthetic", STRONG)

    reader.read()

    assert held.read_outcome is None


def test_leads_strongly_linked_to_the_sets_phase_3_trials_are_read_first(reader: Reader):
    """Scenario: Two due leads"""
    reader.step = step(trial_set="active-since-2025")
    phase_3 = under_way(reader.session)
    phase_2 = under_way(reader.session, ("PHASE2",))
    most_shared = reader.lead("https://www.bbc.com/news/health-50", shares=5000)
    candidate = reader.lead("https://www.bbc.com/news/health-51", shares=500)
    to_phase_2 = reader.lead("https://www.bbc.com/news/health-52", shares=50)
    to_phase_3 = reader.lead("https://www.bbc.com/news/health-53", shares=5)
    link(reader.session, candidate, REGISTRY_TRIAL, phase_3.id, "synthetic", CANDIDATE)
    link(reader.session, to_phase_2, REGISTRY_TRIAL, phase_2.id, "synthetic", STRONG)
    link(reader.session, to_phase_3, REGISTRY_TRIAL, phase_3.id, "synthetic", STRONG)

    for _ in range(4):
        reader.read(limit=1)

    assert reader.web.asked == [
        "www.bbc.com/news/health-53",
        "www.bbc.com/news/health-52",
        "www.bbc.com/news/health-51",
        "www.bbc.com/news/health-50",
    ]
    assert most_shared.read_outcome is not None


def test_a_read_narrowed_to_a_set_reads_only_leads_linked_to_it(reader: Reader):
    """Scenario: Reading the leads of a set"""
    in_the_set = under_way(reader.session)
    linked = reader.lead("https://www.bbc.com/news/health-60")
    by_name = reader.lead("https://www.bbc.com/news/health-61")
    unlinked = reader.lead("https://www.bbc.com/news/health-62", shares=5000)
    link(reader.session, linked, REGISTRY_TRIAL, in_the_set.id, "synthetic", STRONG)
    link(reader.session, by_name, REGISTRY_TRIAL, in_the_set.id, "synthetic", CANDIDATE)

    reader.step = step(trial_set="active-since-2025", only_trial_set=True)
    reader.read()
    assert (linked.read_outcome is None, by_name.read_outcome, unlinked.read_outcome) == (
        False,
        None,
        None,
    )

    reader.step = step(trial_set="active-since-2025", only_trial_set=True, least_strength=CANDIDATE)
    reader.read()
    assert by_name.read_outcome is not None and unlinked.read_outcome is None


def test_the_plan_counts_the_leads_linked_to_a_set_by_where_triage_left_them(reader: Reader):
    """Scenario: A plan for the first set"""
    in_the_set = under_way(reader.session)
    other = under_way(reader.session)
    other.overall_status = "COMPLETED"
    scores = (0.9, 0.9, 0.4, 0.1, None)
    leads = [
        reader.lead(f"https://www.bbc.com/news/health-7{number}", score=score)
        for number, score in enumerate(scores)
    ]
    for lead in leads:
        link(reader.session, lead, REGISTRY_TRIAL, in_the_set.id, "synthetic", STRONG)
    weaker = reader.lead("https://www.bbc.com/news/health-80")
    link(reader.session, weaker, REGISTRY_TRIAL, in_the_set.id, "synthetic", CANDIDATE)
    elsewhere = reader.lead("https://www.bbc.com/news/health-81")
    link(reader.session, elsewhere, REGISTRY_TRIAL, other.id, "synthetic", STRONG)
    reader.step = step(trial_set="active-since-2025", only_trial_set=True)
    reader.read(limit=1)

    def plan(strength: str) -> SetPlan:
        return plan_of(
            reader.session,
            "active-since-2025",
            at_least(strength),
            pass_above=0.7,
            reject_below=0.2,
            read_step="link_read",
            now=NOW,
        )

    strong = plan(STRONG)
    assert (strong.leads, strong.trials) == (5, 1)
    assert (strong.passed, strong.held, strong.rejected, strong.not_scored) == (2, 1, 1, 1)
    assert (strong.already_read, strong.read_this_month) == (1, 1)
    assert plan(CANDIDATE).leads == 6
    with pytest.raises(UnknownStrength, match="Strengths, strongest first: exact, strong"):
        at_least("certain")


# --- no claim --------------------------------------------------------------------------


def test_an_unsure_vertical_makes_no_claim_and_lists_the_lead(reader: Reader):
    """Scenario: No confident vertical"""
    reader.backend.probability = 0.5
    lead = reader.lead()

    report = reader.read()

    assert (report.needs_fix, report.nothing_found) == (1, 0)
    assert lead.read_outcome is ReadOutcome.NEEDS_VERTICAL
    assert "EX-1 antibody for tooth agenesis" in (lead.read_detail or "")
    entry = reader.entry(lead)
    assert (entry.outcome, entry.attempts, entry.reason) == (
        WorkOutcome.NEEDS_FIX,
        0,
        "needs_vertical",
    )
    assert entry.reason_values is not None and entry.reason_values["outlet"] == "theguardian.com"
    assert entry.not_before is None
    assert reader.session.scalars(select(Claim)).all() == []


def test_a_taken_slug_fails_the_lead_by_name_and_keeps_the_calls_cost(reader: Reader):
    """Scenario: The slug is taken"""
    add_claim(
        reader.session,
        slug="ex-1-antibody-tooth-agenesis",
        headline="A claim that took the slug by hand",
        vertical="mouth-and-teeth",
        intervention="Another drug",
        indication="another condition",
    )
    lead = reader.lead()

    report = reader.read(limit=1)

    entry = reader.entry(lead)
    assert (report.failed, entry.outcome) == (1, WorkOutcome.FAILED)
    assert "'ex-1-antibody-tooth-agenesis'" in (entry.error or "")
    assert lead.read_outcome is None
    assert len(reader.session.scalars(select(LlmUsage)).all()) == 1


def test_a_description_in_place_of_a_name_is_rejected_by_rule_and_kept(session, fake_time):
    """Scenario: A description in place of a name"""
    reader = Reader(session, fake_time, DRAFT | {"intervention": "the experimental drug"})
    lead = reader.lead()

    reader.read()

    claim = claim_of(session, lead)
    assert (lead.read_outcome, claim.review_state) == (ReadOutcome.NEW_CLAIM, ReviewState.REJECTED)


# --- only an article about one treatment for one condition -----------------------------


def test_an_article_that_is_not_about_one_treatment_makes_no_claim(reader: Reader):
    """Scenario: An approach with no one condition"""
    reader.backend.report_kind = NOT_ONE_TREATMENT
    lead = reader.lead()

    report = reader.read()

    assert (report.done, lead.read_outcome) == (0, ReadOutcome.NOT_ONE_TREATMENT)
    assert lead.read_detail == (
        "EX-1 antibody for tooth agenesis; about one treatment for one condition at 0.05"
    )
    assert reader.session.scalars(select(Claim)).all() == []
    assert reader.entry(lead).outcome is WorkOutcome.NOTHING_FOUND
    # Asked of the read's own words, never of the article's.
    [shown] = reader.backend.report_asked
    assert "Headline: Antibody regrows teeth in mice" in shown and MARKER not in shown
    assert funnel(reader.session, pass_above=0.7, reject_below=0.2).not_one_treatment == 1


def test_a_class_of_treatments_makes_no_claim_and_asks_no_decision(session: Session, fake_time):
    """Scenario: A class of treatments"""
    reader = Reader(session, fake_time, DRAFT | {"intervention": "GLP-1 receptor agonists"})
    lead = reader.lead()

    report = reader.read()

    assert (report.done, lead.read_outcome) == (0, ReadOutcome.NOT_ONE_TREATMENT)
    assert lead.read_detail == (
        "GLP-1 receptor agonists for tooth agenesis; a class of treatments, not one"
    )
    assert reader.session.scalars(select(Claim)).all() == []
    assert reader.backend.report_asked == []


def test_a_topics_class_named_without_a_drug_makes_no_claim(session: Session, fake_time):
    """Scenario: A topic's class named without a drug"""
    reader = Reader(session, fake_time, DRAFT | {"intervention": "GLP-1 metabolic therapy"})
    lead = reader.lead()

    reader.read()

    assert lead.read_outcome is ReadOutcome.NOT_ONE_TREATMENT
    assert reader.session.scalars(select(Claim)).all() == []
    assert reader.backend.report_asked == []


def test_an_article_that_is_not_about_one_treatment_joins_no_claim(reader: Reader):
    """Scenario: Not one treatment, though it names a tracked one"""
    claim = tracked_claim(reader.session)
    reader.backend.report_kind = NOT_ONE_TREATMENT
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.NOT_ONE_TREATMENT, None)
    assert len(articles_of(reader.session, claim)) == 1


def test_an_article_about_an_established_treatment_becomes_a_claim_and_says_so(reader: Reader):
    """Scenario: News about an established treatment"""
    reader.backend.report_kind = ESTABLISHED_TREATMENT
    lead = reader.lead()

    reader.read()

    assert lead.read_outcome is ReadOutcome.NEW_CLAIM
    assert lead.read_detail == "an established treatment in the news"
    assert claim_of(reader.session, lead).review_state is ReviewState.PENDING


def test_an_article_about_an_established_treatment_joins_its_claim(reader: Reader):
    """Scenario: News about a tracked, established treatment"""
    claim = tracked_claim(reader.session)
    reader.backend.same_claim = claim.slug
    reader.backend.report_kind = ESTABLISHED_TREATMENT
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    assert (lead.read_detail or "").startswith("an established treatment in the news; read as ")


def test_new_and_established_together_decide_that_it_is_one_treatment(reader: Reader):
    """Scenario: Unsure whether new or established"""
    reader.backend.report_kind, reader.backend.report_probability = ESTABLISHED_TREATMENT, 0.4
    lead = reader.lead()

    reader.read()

    # 0.4 established and 0.3 new: about one treatment at 0.7, whichever it is.
    assert lead.read_outcome is ReadOutcome.NEW_CLAIM


# --- topic leads -----------------------------------------------------------------------


def test_a_held_lead_that_names_a_topic_is_read_and_one_that_does_not_is_not(reader: Reader):
    """Scenarios: A held lead on a topic, A held lead on no topic, A rejected lead on a topic"""
    reader.step = step(topic_terms=("Zepbound", "GLP-1"))
    held_on_topic = reader.lead("https://www.bbc.com/news/health-10", score=0.4)
    held_on_topic.title = "New glp-1 pill cuts weight in a synthetic trial"
    held_off_topic = reader.lead("https://www.bbc.com/news/health-11", score=0.4)
    rejected_on_topic = reader.lead("https://www.bbc.com/news/health-12", score=0.1)
    rejected_on_topic.title = "What Zepbound costs at a synthetic pharmacy"
    reader.session.flush()

    reader.read()

    assert held_on_topic.read_outcome is ReadOutcome.NEW_CLAIM
    assert (held_off_topic.read_outcome, rejected_on_topic.read_outcome) == (None, None)


def test_a_word_inside_another_word_names_no_topic(reader: Reader):
    """Scenario: A word inside another word"""
    reader.step = step(topic_terms=("GLP-1",))
    lead = reader.lead(score=0.4)
    lead.title = "Synthetic study of GLP-12 receptors"
    reader.session.flush()

    reader.read()

    assert lead.read_outcome is None


def test_a_lead_that_names_a_topic_is_read_before_a_more_shared_one(reader: Reader):
    """Scenario: A topic lead and a much-shared lead"""
    reader.step = step(topic_terms=("Zepbound",))
    much_shared = reader.lead("https://www.bbc.com/news/health-20", shares=900)
    on_topic = reader.lead("https://www.theguardian.com/science/2024/jan/04/synthetic", shares=2)
    on_topic.title = "Zepbound approved in a synthetic country"
    reader.session.flush()

    reader.read(limit=1)

    assert (on_topic.read_outcome, much_shared.read_outcome) == (ReadOutcome.NEW_CLAIM, None)


def test_with_no_topics_only_passed_leads_are_read(reader: Reader):
    """Scenario: No topics are listed"""
    held = reader.lead(score=0.4)
    held.title = "Zepbound approved in a synthetic country"
    reader.session.flush()

    reader.read()

    assert held.read_outcome is None


def test_business_news_on_a_topic_makes_no_claim(reader: Reader):
    """Scenario: A shortage of a topic's drug"""
    reader.step = step(topic_terms=("Zepbound",))
    reader.backend.report_kind = BUSINESS_NEWS
    lead = reader.lead()
    lead.title = "Zepbound shortage hits synthetic pharmacies"
    reader.session.flush()

    reader.read()

    assert lead.read_outcome is ReadOutcome.BUSINESS_NEWS
    assert lead.read_detail == (
        "EX-1 antibody for tooth agenesis; on a topic, and about what the treatment does at 0.03"
    )
    assert reader.session.scalars(select(Claim)).all() == []
    assert funnel(reader.session, pass_above=0.7, reject_below=0.2).business_news == 1


def test_evidence_on_a_topic_becomes_a_claim(reader: Reader):
    """Scenario: A trial result for a topic's drug"""
    reader.step = step(topic_terms=("Zepbound",))
    reader.backend.report_kind = ESTABLISHED_TREATMENT
    lead = reader.lead()
    lead.title = "Zepbound cuts heart risk in a synthetic trial"
    reader.session.flush()

    reader.read()

    assert lead.read_outcome is ReadOutcome.NEW_CLAIM


def test_a_backfill_read_keeps_verified_ids_for_claim_preparation(reader: Reader):
    calls = []

    def match_article(session, retrieved, headline, outlet, published):
        calls.append((headline, published))
        assert MARKER in retrieved.text
        return ArticleMatches(("NCT00001111",), ("10.5555/research",), ("2345", "3456"))

    reader.client.match_article = match_article
    lead = reader.lead()

    reader.read()

    assert calls == [(HEADLINE, date(2019, 5, 4))]
    assert reader.client.requests_made == 1
    article = reader.session.get(SourceArticle, lead.source_article_id)
    assert article is not None
    assert article.matched_registry_numbers == ["NCT00001111"]
    assert article.matched_dois == ["10.5555/research"]
    assert article.matched_pubmed_ids == ["2345", "3456"]
    assert article.named_registry_numbers == []
    assert article.named_dois == []
    claim = reader.session.get(Claim, lead.claim_id)
    assert claim is not None and claim.review_state is ReviewState.PENDING


def test_evidence_source_pause_keeps_the_read_due_and_its_cost(reader: Reader):
    def match_article(session, retrieved, headline, outlet, published):
        raise CannotAsk("PubMed allowance used")

    reader.client.match_article = match_article
    lead = reader.lead()

    report = reader.read()

    assert report.stopped == "PubMed allowance used"
    assert lead.read_outcome is None
    assert reader.session.scalars(select(Claim)).all() == []
    assert reader.session.scalar(select(func.count()).select_from(LlmUsage)) == 1


def test_business_news_on_no_topic_starts_no_claim(reader: Reader):
    """Scenario: A price rise with no claim to join"""
    reader.backend.report_kind = BUSINESS_NEWS
    lead = reader.lead()

    reader.read()

    assert lead.read_outcome is ReadOutcome.BUSINESS_NEWS
    assert lead.read_detail == (
        "EX-1 antibody for tooth agenesis; no claim to join, and about what the treatment "
        "does at 0.03"
    )
    assert reader.session.scalars(select(Claim)).all() == []


def test_business_news_on_no_topic_joins_a_claim_that_exists_and_says_so(reader: Reader):
    """Scenario: A price rise for a tracked treatment on no topic"""
    claim = tracked_claim(reader.session)
    reader.backend.same_claim = claim.slug
    reader.backend.report_kind = BUSINESS_NEWS
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    assert (lead.read_detail or "").startswith("business news about a treatment; read as ")


def test_a_title_that_names_nothing_is_on_a_topic_when_the_read_names_its_drug(session, fake_time):
    """Scenario: Shared under a title that names nothing"""
    reader = Reader(
        session,
        fake_time,
        DRAFT | {"intervention": "Wegovy", "intervention_synonyms": [], "indication": "obesity"},
    )
    reader.step = step(topic_terms=("semaglutide", "Wegovy"))
    add_claim(
        session,
        slug="semaglutide-obesity",
        headline="A synthetic headline",
        vertical="diabetes-and-hormones",
        intervention="semaglutide",
        indication="obesity",
    )
    reader.backend.report_kind = BUSINESS_NEWS
    lead = reader.lead()

    reader.read()

    # The title is the default one and names no drug; the read does. Not joined.
    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.BUSINESS_NEWS, None)


def test_a_brand_name_is_offered_the_claim_entered_under_the_generic_name(session, fake_time):
    """Scenario: A brand name and its generic name"""
    reader = Reader(
        session,
        fake_time,
        DRAFT | {"intervention": "Wegovy", "intervention_synonyms": [], "indication": "obesity"},
    )
    claim = add_claim(
        session,
        slug="semaglutide-obesity",
        headline="A synthetic headline",
        vertical="diabetes-and-hormones",
        intervention="semaglutide",
        indication="obesity in adults",
    )
    reader.backend.same_claim = claim.slug
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    assert (
        "- semaglutide-obesity: semaglutide for obesity in adults"
        in (reader.backend.same_claim_asked[0])
    )


def filed_under_a_substance(session: Session, claim: Claim, *names: str) -> None:
    """Keep a synthetic record of the registry of substances with the claim's
    intervention: what the registry calls the substance, then the other names it lists."""
    from thenwhat.db.models import Entity, EntitySubstance
    from thenwhat.domain import EntityType

    entity = session.scalars(
        select(Entity).where(Entity.claim_id == claim.id, Entity.type == EntityType.INTERVENTION)
    ).one()
    session.add(
        EntitySubstance(
            entity_id=entity.id,
            source_name="gsrs",
            external_id="synthetic-substance",
            url="https://gsrs.test/synthetic-substance",
            payload={
                "substance": {"_name": names[0].upper()},
                "names": [{"name": name, "type": "bn"} for name in names],
            },
            fetched_at=NOW,
            codes=[],
        )
    )
    session.flush()


def test_a_brand_the_substance_record_names_joins_the_claim_under_the_generic(session, fake_time):
    """Scenario: A brand the registry of substances lists for a claim's substance"""
    reader = Reader(
        session,
        fake_time,
        DRAFT | {"intervention": "Toothera", "intervention_synonyms": []},
    )
    claim = tracked_claim(session)
    filed_under_a_substance(session, claim, "exampletumab", "Toothera", "exampletumab sodium")
    reader.backend.same_claim = claim.slug
    lead = reader.lead()

    reader.read()

    # The names share no word; the substance's record is what offered the claim. The
    # decision still settles it, shown the claim under the name it was entered by.
    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    assert (
        "- ex-1-tooth-agenesis: EX-1 antibody for tooth agenesis"
        in (reader.backend.same_claim_asked[0])
    )
    assert session.scalar(select(func.count()).select_from(Claim)) == 1


def test_claims_found_by_their_substance_take_no_place_from_a_claim_found_by_name(
    session, fake_time
):
    """Scenario: More claims under the substance than the decision was shown before"""
    reader = Reader(
        session,
        fake_time,
        DRAFT | {"intervention": "Toothera gel", "intervention_synonyms": ["Toothera"]},
    )
    # Eight older claims found only through their substance's record, for other
    # conditions, and then the claim the read's own name finds.
    for number in range(8):
        other = add_claim(
            session,
            slug=f"exampletumab-condition-{number}",
            headline="A synthetic headline",
            vertical="mouth-and-teeth",
            intervention=f"exampletumab form {number}",
            indication=f"condition {number}",
        )
        filed_under_a_substance(session, other, "exampletumab", "Toothera")
    by_name = add_claim(
        session,
        slug="toothera-gel-tooth-agenesis",
        headline="A synthetic headline",
        vertical="mouth-and-teeth",
        intervention="Toothera gel",
        indication="tooth agenesis",
    )
    reader.backend.same_claim = by_name.slug
    lead = reader.lead()

    reader.read()

    shown = reader.backend.same_claim_asked[0]
    assert "- toothera-gel-tooth-agenesis: Toothera gel for tooth agenesis" in shown
    assert all(f"- exampletumab-condition-{number}:" in shown for number in range(8))
    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, by_name.id)


def test_another_treatment_for_the_same_condition_still_drafts_its_own_claim(session, fake_time):
    """Scenario: Another treatment for the condition of a claim filed under a substance"""
    reader = Reader(
        session,
        fake_time,
        DRAFT | {"intervention": "sodium fluoride varnish", "intervention_synonyms": ["Varnex"]},
    )
    claim = tracked_claim(session)
    filed_under_a_substance(session, claim, "exampletumab", "Toothera", "exampletumab sodium")
    # Were the claim offered, the decision would take it: it must not be offered.
    reader.backend.same_claim = claim.slug
    lead = reader.lead()

    reader.read()

    # A word of one of the substance's names ("sodium") is no name for the treatment.
    assert reader.backend.same_claim_asked == []
    assert lead.read_outcome is ReadOutcome.NEW_CLAIM and lead.claim_id != claim.id
    assert claim_of(session, lead).indication == "tooth agenesis"


def test_a_dose_or_assisted_therapy_is_offered_the_claim_and_never_drafts_a_duplicate(
    session, fake_time
):
    """Scenarios: A name with a dose or an assisted therapy, A duplicate refused"""
    reader = Reader(
        session,
        fake_time,
        DRAFT
        | {
            "intervention": "MDMA-assisted psychotherapy",
            "intervention_synonyms": [],
            "indication": "Post-traumatic stress disorder",
        },
    )
    claim = add_claim(
        session,
        slug="mdma-ptsd",
        headline="A synthetic headline",
        vertical="mouth-and-teeth",
        intervention="MDMA",
        indication="Post-traumatic stress disorder (PTSD)",
    )
    # The decision does not establish that they are the same.
    lead = reader.lead()

    reader.read()

    assert (
        "- mdma-ptsd: MDMA for Post-traumatic stress disorder (PTSD)"
        in (reader.backend.same_claim_asked[0])
    )
    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.IDENTITY_UNRESOLVED, None)
    assert lead.read_detail is not None and claim.slug in lead.read_detail


# --- one story, several outlets --------------------------------------------------------

# Four synthetic reads shaped like one much-shared story: each outlet words the treatment
# and the condition its own way.
STORY: list[dict[str, Any]] = [
    DRAFT
    | {
        "intervention": "esketamine",
        "intervention_synonyms": [],
        "indication": "major depressive disorder and suicidal thinking",
    },
    DRAFT
    | {
        "intervention": "esketamine nasal spray",
        "intervention_synonyms": [],
        "indication": "depression",
    },
    DRAFT
    | {
        "intervention": "Esketamine nasal spray",
        "intervention_synonyms": [],
        "indication": "severe depression, particularly with suicidal thinking",
    },
    DRAFT
    | {
        "intervention": "esketamine",
        "intervention_synonyms": [],
        "indication": "treatment-resistant depression",
    },
]
STORY_SLUG = "esketamine-major-depressive-disorder-and-suicidal-thinking"
STORY_URLS = [
    "https://www.theguardian.com/science/2019/mar/05/synthetic-spray",
    "https://www.bbc.com/news/health-synthetic-spray",
    "https://www.statnews.com/2019/03/05/synthetic-spray",
    "https://www.reuters.com/article/synthetic-spray",
]


def story_leads(reader: Reader, count: int = 4) -> list[LinkLead]:
    """Leads for the story's articles, the first the most shared, so it is read first."""
    return [
        reader.lead(url, shares=100 - 10 * number) for number, url in enumerate(STORY_URLS[:count])
    ]


def test_one_story_worded_four_ways_by_four_outlets_becomes_one_claim(session, fake_time):
    """Scenarios: The same story in another outlet's words, A name inside a longer name"""
    reader = Reader(session, fake_time, *STORY)
    reader.backend.same_claim = STORY_SLUG
    leads = story_leads(reader)

    reader.read()

    assert [lead.read_outcome for lead in leads] == [
        ReadOutcome.NEW_CLAIM,
        ReadOutcome.ADDED_TO_CLAIM,
        ReadOutcome.ADDED_TO_CLAIM,
        ReadOutcome.ADDED_TO_CLAIM,
    ]
    [claim] = session.scalars(select(Claim)).all()
    assert claim.slug == STORY_SLUG
    # A join adds an article and rewrites nothing: the claim keeps its first wording.
    assert claim.indication == "major depressive disorder and suicidal thinking"
    assert len(articles_of(session, claim)) == 4
    assert leads[1].read_detail == (
        "read as esketamine nasal spray for depression; the same claim by decision at 0.90, "
        "none of the candidates at 0.10"
    )
    # Asked once per later article with our short summaries, never the source text.
    asked = reader.backend.same_claim_asked
    assert len(asked) == 3
    assert (
        "Article's treatment: esketamine nasal spray\nArticle's condition: depression" in asked[0]
    )
    assert f"- {STORY_SLUG}: esketamine for major depressive disorder" in asked[0]
    assert MARKER not in "".join(asked)


def test_the_same_treatment_for_another_condition_stays_its_own_claim(session, fake_time):
    """Scenario: The same treatment for a different condition"""
    reader = Reader(session, fake_time, STORY[0], STORY[0] | {"indication": "chronic nerve pain"})
    leads = story_leads(reader, 2)

    reader.read()

    assert [lead.read_outcome for lead in leads] == [ReadOutcome.NEW_CLAIM] * 2
    assert sorted(session.scalars(select(Claim.slug))) == [
        "esketamine-chronic-nerve-pain",
        STORY_SLUG,
    ]
    assert len(reader.backend.same_claim_asked) == 1


@pytest.mark.parametrize(
    ("intervention", "indication", "said"),
    [
        ("COVID-19 vaccination", "prevention of COVID-19", "a class of treatments, not one"),
        ("third dose of COVID-19 vaccine", "COVID-19", "a class of treatments, not one"),
        ("Statins", "dementia", "a class of treatments, not one"),
        ("DHA", "Cancer", "no one condition"),
        ("GS-441524", "feline infectious peritonitis", "an animal's condition"),
    ],
)
def test_a_class_a_bare_cancer_or_an_animals_condition_makes_no_claim(
    session, fake_time, intervention, indication, said
):
    """Scenarios: A vaccine or schedule with no product, A condition that is not one
    condition of people"""
    reader = Reader(
        session,
        fake_time,
        DRAFT
        | {"intervention": intervention, "intervention_synonyms": [], "indication": indication},
    )
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.NOT_ONE_TREATMENT, None)
    assert lead.read_detail is not None and lead.read_detail.endswith(said)
    assert session.scalars(select(Claim)).all() == []


@pytest.mark.parametrize("report_kind", [NEW_TREATMENT, BUSINESS_NEWS])
def test_equal_generic_names_do_not_join_different_products(session, fake_time, report_kind):
    """A generic vaccine name cannot override the products the summaries identify. (A
    name such as "COVID-19 vaccine" is refused before this, as a class.)"""
    generic = DRAFT | {
        "intervention": "Ad26 vaccine",
        "intervention_synonyms": [],
        "indication": "COVID-19",
    }
    reader = Reader(
        session,
        fake_time,
        generic | {"summary": "The Oxford-AstraZeneca vaccine was tested in a synthetic trial."},
        generic | {"summary": "The Moderna vaccine was tested in a different synthetic trial."},
    )
    leads = story_leads(reader, 2)
    reader.read(limit=1)
    reader.backend.report_kind = report_kind
    reader.read()

    first = claim_of(session, leads[0])
    assert len(articles_of(session, first)) == 1
    assert (leads[1].read_outcome, leads[1].claim_id) == (ReadOutcome.IDENTITY_UNRESOLVED, None)
    assert leads[1].source_article_id is None
    assert reader.entry(leads[1]).outcome is WorkOutcome.NOTHING_FOUND
    assert len(session.scalars(select(Claim)).all()) == 1
    [asked] = reader.backend.same_claim_asked
    assert "Article summary: The Moderna vaccine" in asked
    assert "Claim summary: The Oxford-AstraZeneca vaccine" in asked
    assert MARKER not in asked
    before = (len(reader.prompts), len(reader.backend.same_claim_asked), len(reader.web.asked))
    assert reader.read().processed == 0
    assert before == (
        len(reader.prompts),
        len(reader.backend.same_claim_asked),
        len(reader.web.asked),
    )
    found = funnel(session, pass_above=0.7, reject_below=0.2)
    assert (found.identity_unresolved, found.read) == (1, 2)


def test_equal_names_still_supply_bounded_identity_context(reader: Reader):
    claim = tracked_claim(reader.session)
    claim.summary = "A synthetic product's context. " * 30 + "OMITTED-CONTEXT-END"
    reader.backend.same_claim = claim.slug
    lead = reader.lead()

    reader.read()

    assert lead.read_outcome is ReadOutcome.ADDED_TO_CLAIM
    [asked] = reader.backend.same_claim_asked
    assert "Article summary: An antibody restored missing teeth in mice." in asked
    assert "Claim summary: A synthetic product's context." in asked
    assert " [truncated]" in asked
    assert "OMITTED-CONTEXT-END" not in asked


def test_exact_name_and_condition_remain_a_candidate_beyond_eight_older_claims(reader: Reader):
    for number in range(8):
        add_claim(
            reader.session,
            slug=f"ex-1-other-{number}",
            headline="Synthetic claim for another condition",
            vertical="mouth-and-teeth",
            intervention="EX-1 antibody",
            indication=f"Other condition {number}",
        )
    claim = tracked_claim(reader.session)
    reader.backend.same_claim = claim.slug
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    [asked] = reader.backend.same_claim_asked
    assert f"- {claim.slug}: " in asked
    assert asked.count("Claim summary:") == 8


# A read for a treatment and condition a claim already has, the condition written another
# way: the slug the rule would give a new claim is that claim's. Synthetic, shaped like
# the read the backfill of 2026-11-16 recorded as failed.
OWNED_DRAFT = DRAFT | {"intervention": "semaglutide", "intervention_synonyms": []}


def claim_owning_the_slug(session: Session, indication: str, *, older: int = 8) -> Claim:
    """Older claims of the same treatment for other conditions, as many as the decision
    is shown, then the claim whose slug a read for `indication` would be given."""
    for number in range(older):
        add_claim(
            session,
            slug=f"semaglutide-other-{number}",
            headline="Synthetic claim for another condition",
            vertical="mouth-and-teeth",
            intervention="semaglutide",
            indication=f"Other condition {number}",
        )
    return add_claim(
        session,
        slug=slug_for("semaglutide", indication),
        headline="A synthetic headline",
        vertical="mouth-and-teeth",
        intervention="semaglutide",
        indication=indication,
    )


def test_a_read_whose_slug_a_claim_has_joins_it_when_the_decision_agrees(session, fake_time):
    """Scenario: A read whose new slug a claim already has"""
    reader = Reader(session, fake_time, OWNED_DRAFT | {"indication": "Alcohol-use disorder"})
    claim = claim_owning_the_slug(session, "alcohol use disorder")
    reader.backend.same_claim = claim.slug
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    [asked] = reader.backend.same_claim_asked
    assert f"- {claim.slug}: " in asked


def test_a_read_whose_slug_a_claim_has_is_an_overlap_when_the_decision_declines(session, fake_time):
    """Scenario: A read whose new slug a claim already has, not established as that claim.
    The conditions differ by an accent, so only the slug says they are one."""
    reader = Reader(session, fake_time, OWNED_DRAFT | {"indication": "Meniere's disease"})
    claim = claim_owning_the_slug(session, "Ménière's disease")
    lead = reader.lead()

    report = reader.read()

    assert report.failed == 0
    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.IDENTITY_UNRESOLVED, None)
    assert f"names overlap {claim.slug}," in (lead.read_detail or "")
    assert f"- {claim.slug}: " in reader.backend.same_claim_asked[0]
    assert session.scalar(select(func.count()).select_from(Claim)) == 9
    assert reader.read().processed == 0


def test_a_read_whose_slug_an_archived_claim_has_is_listed_as_overlapping_it(session, fake_time):
    """Scenario: A read whose new slug an archived claim has"""
    reader = Reader(session, fake_time, OWNED_DRAFT | {"indication": "Alcohol-use disorder"})
    claim = claim_owning_the_slug(session, "alcohol use disorder", older=0)
    archive_claim(session, claim.slug, reason="synthetic fault", now=NOW)
    # Were the decision asked, it would say the article reports that claim.
    reader.backend.same_claim = claim.slug
    lead = reader.lead()

    reader.read()

    # An archived claim is not joined: it is not even offered.
    assert reader.backend.same_claim_asked == []
    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.IDENTITY_UNRESOLVED, None)
    assert len(articles_of(session, claim)) == 0
    assert reads_naming_archived_claims(session) == [(lead, claim)]
    assert reads_naming_live_claims(session) == []


def test_a_read_whose_slug_a_rejected_claim_has_is_listed_as_overlapping_it(session, fake_time):
    """Scenario: A read whose new slug a rejected claim has. The slug stays the rejected
    claim's, as every slug does, so no claim is drafted; the read is listed with it."""
    reader = Reader(session, fake_time, OWNED_DRAFT | {"indication": "Alcohol-use disorder"})
    claim = claim_owning_the_slug(session, "alcohol use disorder", older=0)
    record_decision(claim, ReviewState.REJECTED, by=Decider.RULE, now=NOW)
    lead = reader.lead()

    report = reader.read()

    assert report.failed == 0 and reader.backend.same_claim_asked == []
    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.IDENTITY_UNRESOLVED, None)
    assert reads_naming_live_claims(session) == [(lead, claim)]


def test_rejected_equal_name_is_recorded_as_unresolved_without_retry(reader: Reader):
    claim = tracked_claim(reader.session)
    record_decision(claim, ReviewState.REJECTED, by=Decider.RULE, now=NOW)
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.IDENTITY_UNRESOLVED, None)
    assert len(articles_of(reader.session, claim)) == 1
    assert reader.backend.same_claim_asked == []
    assert reader.read().processed == 0


def test_a_decision_that_leans_to_none_of_them_joins_nothing(session, fake_time):
    """Scenario: An unsure decision"""
    reader = Reader(session, fake_time, STORY[0], STORY[3])
    reader.backend.same_claim_chances = {STORY_SLUG: 0.45, NO_SUCH_CLAIM: 0.55}
    leads = story_leads(reader, 2)

    reader.read()

    assert [lead.read_outcome for lead in leads] == [ReadOutcome.NEW_CLAIM] * 2
    assert len(session.scalars(select(Claim)).all()) == 2


def test_a_same_story_the_decision_is_only_fairly_sure_of_still_joins(session, fake_time):
    """Scenario: A wording the decision is less sure of"""
    reader = Reader(session, fake_time, STORY[0], STORY[3])
    reader.backend.same_claim_chances = {STORY_SLUG: 0.62, NO_SUCH_CLAIM: 0.38}
    leads = story_leads(reader, 2)

    reader.read()

    assert leads[1].read_outcome is ReadOutcome.ADDED_TO_CLAIM
    assert len(session.scalars(select(Claim)).all()) == 1


def test_a_near_tie_between_two_claims_of_one_drug_joins_neither(session, fake_time):
    """Scenario: Two conditions of one drug"""
    other = "esketamine-chronic-nerve-pain"
    reader = Reader(
        session,
        fake_time,
        STORY[0],
        STORY[0] | {"indication": "chronic nerve pain"},
        STORY[0] | {"indication": "pain and low mood"},
    )
    leads = story_leads(reader, 3)
    reader.read(limit=2)
    reader.backend.same_claim_chances = {STORY_SLUG: 0.48, other: 0.47, NO_SUCH_CLAIM: 0.05}

    reader.read()

    assert leads[2].read_outcome is ReadOutcome.NEW_CLAIM
    assert len(session.scalars(select(Claim)).all()) == 3


def test_a_vote_split_with_a_clear_leader_joins_the_leader(session, fake_time):
    """Scenario: The vote is split between two claims"""
    other = "esketamine-chronic-nerve-pain"
    reader = Reader(
        session,
        fake_time,
        STORY[0],
        STORY[0] | {"indication": "chronic nerve pain"},
        STORY[2],
    )
    leads = story_leads(reader, 3)
    reader.read(limit=2)
    reader.backend.same_claim_chances = {STORY_SLUG: 0.51, other: 0.43, NO_SUCH_CLAIM: 0.06}

    reader.read()

    assert leads[2].read_outcome is ReadOutcome.ADDED_TO_CLAIM
    assert claim_of(session, leads[2]).slug == STORY_SLUG


def test_a_rejected_draft_is_never_offered_as_a_candidate(session, fake_time):
    """Scenario: A rejected draft shares the name"""
    reader = Reader(session, fake_time, STORY[1], STORY[0])
    leads = story_leads(reader, 2)

    reader.read()

    # The first read gave a description ("... nasal spray") and was rejected by rule; the
    # second names the drug and is not asked whether it reports that rejected draft.
    first, second = (claim_of(session, lead) for lead in leads)
    assert (first.review_state, second.review_state) == (ReviewState.REJECTED, ReviewState.PENDING)
    assert reader.backend.same_claim_asked == []


def test_a_read_that_shares_no_name_with_any_claim_asks_no_decision(reader: Reader):
    """Scenario: No claim shares the name"""
    add_claim(
        reader.session,
        slug="another-drug-tooth-agenesis",
        headline="A claim for another treatment of the same condition",
        vertical="mouth-and-teeth",
        intervention="Another drug",
        indication="tooth agenesis",
    )
    lead = reader.lead()

    reader.read()

    assert lead.read_outcome is ReadOutcome.NEW_CLAIM
    assert reader.backend.same_claim_asked == []


def test_a_claim_the_title_names_is_offered_even_when_the_read_words_it_differently(
    session, fake_time
):
    """Scenario: A claim screening found in the title"""
    reader = Reader(
        session,
        fake_time,
        DRAFT
        | {"intervention": "Toothgro", "intervention_synonyms": [], "indication": "missing teeth"},
    )
    claim = tracked_claim(session)
    reader.backend.same_claim = claim.slug
    lead = reader.lead()
    link(session, lead, "claim", claim.id, TITLE_NAMES_CLAIM)

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    assert (
        "- ex-1-tooth-agenesis: EX-1 antibody for tooth agenesis"
        in reader.backend.same_claim_asked[0]
    )


def test_a_read_keeps_its_turn_at_settling_the_claim_until_its_transaction_ends(
    reader: Reader, engine
):
    """Scenario: Two articles on one story read at once"""
    reader.lead()

    reader.read()

    # The read's transaction is still open here, so no other read may settle a claim.
    with engine.connect() as another_read:
        free = another_read.scalar(select(func.pg_try_advisory_xact_lock(CLAIM_IDENTITY_LOCK)))
    assert free is False


# --- nothing is read before triage is measured -----------------------------------------


def test_reading_is_refused_until_enough_leads_are_labelled(reader: Reader):
    """Scenario: Too few labels"""
    leads = [reader.lead(f"https://www.bbc.com/news/health-{n}") for n in range(2)]
    reader.session.add(
        LinkLeadLabel(
            link_lead_id=leads[0].id,
            label=LeadVerdict.TREATMENT_REPORT,
            labelled_by=Decider.HUMAN,
            labelled_at=NOW,
        )
    )
    reader.session.flush()

    with pytest.raises(NotMeasured, match="1 more are needed"):
        reader.step.check_ready(reader.session)

    reader.session.add(
        LinkLeadLabel(
            link_lead_id=leads[1].id,
            label=LeadVerdict.NOT_HEALTH,
            labelled_by=Decider.HUMAN,
            labelled_at=NOW,
        )
    )
    reader.session.flush()
    reader.step.check_ready(reader.session)
    with pytest.raises(NotMeasured, match="LEAD_PASS_ABOVE is not set"):
        step(pass_above=None).check_ready(reader.session)


# --- the funnel ------------------------------------------------------------------------


def test_funnel_includes_identity_and_treatment_kind_costs(session: Session):
    for purpose, cost in [(SAME_CLAIM, "0.01"), (TREATMENT_KIND, "0.02"), ("other", "0.04")]:
        session.add(
            LlmUsage(
                purpose=f"decision:{purpose}",
                model="synthetic",
                input_tokens=1,
                output_tokens=0,
                cost_usd=Decimal(cost),
                created_at=NOW,
            )
        )
    session.flush()

    found = funnel(session, pass_above=0.7, reject_below=0.2)

    assert found.reading_cost_usd == Decimal("0.03")


def test_the_funnel_counts_each_outcome_and_the_cost_of_reading(session: Session, fake_time):
    """Scenario: After a limited run"""
    reader = Reader(
        session,
        fake_time,
        DRAFT,
        DRAFT | {"intervention": "the experimental drug", "indication": "hair loss"},
    )
    reader.lead()
    reader.lead("https://www.bbc.com/news/health-2")
    reader.lead("https://www.statnews.com/2019/05/04/undated", serves=page(published=None))
    reader.lead("https://www.bbc.com/news/health-3", score=0.5)
    reader.lead("https://www.bbc.com/news/health-4", score=0.1)
    unlisted = reader.lead("https://github.com/example/repository", score=None)
    unlisted.screen_outcome = ScreenOutcome.UNLISTED_OUTLET
    session.flush()
    asked = len(reader.web.asked)

    reader.read()
    found = funnel(session, pass_above=0.7, reject_below=0.2)

    assert (found.loaded, found.in_scope, found.scored) == (6, 5, 5)
    assert dict(found.standing) == {"passed": 3, "held": 1, "rejected": 1}
    assert (found.read, found.new_approved_by_rule, found.new_rejected_by_rule) == (2, 0, 1)
    assert (found.new_awaiting_preparation, found.new_otherwise) == (1, 0)
    assert found.cannot_be_read == {NO_DATE: 1}
    assert found.undated_outlets == [("statnews.com", 1)]
    # Two reads were paid for; the scripted model's cost is recorded under the leads' name.
    assert found.reading_cost_usd > 0 and found.triage_cost_usd == 0
    # The report itself asks nobody anything.
    after = len(reader.web.asked)
    funnel(session, pass_above=0.7, reject_below=0.2)
    assert len(reader.web.asked) == after > asked


# --- what the page names ---------------------------------------------------------------


def test_what_the_page_names_is_kept_with_its_article_and_asked_for_by_no_read(
    session: Session, fake_time
):
    """Scenarios: An article that links its trial (openspec lead-reading); Two reads at
    once (change one-work-runner): a read asks no registry, so a second read never
    waits on its lookups while the first holds the turn that settles the claim."""
    from claim_support import Registry, Sources, prepare, trial
    from thenwhat.db.models import Entity, EntityMatch, SourceArticle
    from thenwhat.resolve.reasons import NAMED_IN_ARTICLE

    reader = Reader(session, fake_time)
    linked = page().replace(
        "</main>",
        '<a href="https://clinicaltrials.gov/study/NCT04184622">the trial</a>'
        '<a href="https://doi.org/10.1000/named">the paper</a></main>',
    )
    lead = reader.lead(serves=linked)

    reader.read()

    assert (lead.read_outcome, lead.read_detail) == (ReadOutcome.NEW_CLAIM, None)
    article = session.get(SourceArticle, lead.source_article_id)
    assert article is not None
    assert (article.named_registry_numbers, article.named_dois) == (
        ["NCT04184622"],
        ["10.1000/named"],
    )

    # The step of its own looks the trial up, scores it, and approves nothing by it.
    registry = Registry([trial("NCT04184622")])
    prepare(session, Sources(registry), names=("claim_named_records",), match_accept_above=0.0)

    [match] = session.scalars(
        select(EntityMatch)
        .join(Entity, Entity.id == EntityMatch.entity_id)
        .where(Entity.claim_id == lead.claim_id)
    )
    assert (match.external_id, match.reasons) == ("NCT04184622", [NAMED_IN_ARTICLE])
    assert match.review_state is ReviewState.PENDING
    # No literature source is configured, so the paper is left unrecorded.
    assert registry.asked == ["NCT04184622"]


# --- measured ------------------------------------------------------------------------


def test_a_read_is_measured_under_the_leads_address_with_what_it_asked(
    reader: Reader, measured_spans
):
    """processing-metrics, An address can be followed end to end: the read and every
    decision made inside it are measured under the lead's address key, and the page
    reader's request is counted in the read."""
    lead = reader.lead("https://www.theguardian.com/science/2019/may/04/synthetic-teeth")
    measured_spans.clear()

    reader.read()

    read = measured_spans[-1]
    assert (read.step, read.trace, read.outcome) == ("link_read", lead.url_key, "done")
    assert read.requests.get("reader", 0) >= 1
    inside = measured_spans[:-1]
    assert inside, "the read made decisions, and each is measured"
    assert {made.trace for made in inside} == {lead.url_key}
    assert all(made.step.startswith(("decision:", "read")) for made in inside)


def test_an_outlets_turn_is_held_from_the_look_at_its_hold_to_the_readers_answer(
    reader: Reader, engine
):
    """Scenario: Two workers, one stopped outlet. A second worker cannot look at the
    outlet's hold, and so cannot ask, while the first worker's request is in flight; it
    may once the answer, and any hold it brought, is kept."""
    lead = reader.lead()
    turn = select(
        func.pg_try_advisory_lock(OUTLET_TURN_LOCK, func.hashtext(OUTLET_HOLD + "theguardian.com"))
    )
    free_in_flight: list[bool] = []

    def stopped() -> httpx.Response:
        with engine.connect() as another_worker:
            free_in_flight.append(bool(another_worker.scalar(turn)))
        return httpx.Response(
            429,
            json={"success": False, "code": "NOT_NOW", "reason": "stopped", "retryAfter": 3600},
        )

    reader.page_reader.answer = stopped

    began = reader.time.now()

    reader.read(by_the_step_clock=True)

    assert free_in_flight == [False]
    # The hold was kept, and the turn is free again for the worker that waited: it finds
    # the hold and asks nothing. The lead is put off until the hold ends.
    entry = reader.entry(lead)
    assert (entry.outcome, entry.attempts, entry.reason) == (
        WorkOutcome.LATER,
        0,
        "reader_not_now",
    )
    assert entry.not_before == began + timedelta(seconds=3600)
    with engine.connect() as another_worker:
        assert another_worker.scalar(turn) is True
        # The lock is the connection's, and the connection goes back to a pool.
        another_worker.execute(select(func.pg_advisory_unlock_all()))


def test_a_wait_past_a_day_holds_the_outlet_for_a_day_and_ends_no_run(reader: Reader):
    """Scenario: A wait no reader means. Milliseconds, or a number no time can hold, is
    read as a day."""
    lead = reader.lead()
    reader.page_reader.not_now["www.theguardian.com"] = 1e300
    began = reader.time.now()

    report = reader.read(by_the_step_clock=True)

    assert (report.later, report.failed, report.stopped) == (1, 0, None)
    entry = reader.entry(lead)
    assert (entry.outcome, entry.attempts, entry.reason) == (
        WorkOutcome.LATER,
        0,
        "reader_not_now",
    )
    assert entry.not_before == began + timedelta(hours=24)


def test_an_outlet_the_reader_cannot_get_is_left_after_three_pages(reader: Reader):
    """An outlet whose pages the reader keeps saying "not now" for, stating no wait, is
    asked three times in a run and then left: its other leads are put off for an hour,
    cost no request and count no attempt, and the run goes on to other outlets."""
    blocked = [
        reader.lead(f"https://www.theguardian.com/science/2019/may/0{n}/synthetic-teeth-{n}")
        for n in range(1, 7)
    ]
    other = reader.lead("https://www.bbc.co.uk/news/health-synthetic-teeth")
    reader.page_reader.not_now["www.theguardian.com"] = 0
    began = reader.time.now()

    report = reader.read(by_the_step_clock=True)

    asked = [body["url"] for body in reader.page_reader.asked]
    assert sum("theguardian.com" in url for url in asked) == 3
    assert report.later == 6
    assert all(lead.read_outcome is None for lead in blocked)
    assert other.read_outcome is ReadOutcome.NEW_CLAIM
    entries = [reader.entry(lead) for lead in blocked]
    assert {(entry.outcome, entry.attempts, entry.reason) for entry in entries} == {
        (WorkOutcome.LATER, 0, "reader_not_now")
    }
    # An hour from the moment each was put off, which the allowance's interval moves on.
    assert all(
        began + timedelta(hours=1) <= entry.not_before <= began + timedelta(hours=1, seconds=10)
        for entry in entries
        if entry.not_before is not None
    )

    # A later run starts fresh, as each run makes its own step, and finds them due once
    # the hour is over: the outlet is asked again and, answering, is read.
    reader.page_reader.not_now.clear()
    last = max(entry.not_before for entry in entries if entry.not_before is not None)
    reader.time.advance(last - timedelta(seconds=1) - reader.time.now())
    assert count(reader.session, reader.step, 3, now=reader.time.now()).due < len(blocked)
    reader.time.advance(timedelta(seconds=1))
    reader.step = step(time=reader.time)
    reader.read(by_the_step_clock=True)

    assert all(lead.read_outcome is not None for lead in blocked)


def test_one_outlets_pages_are_not_asked_for_back_to_back(reader: Reader):
    """With a gap set, a second lead on an outlet asked a moment ago is put off until the
    gap has passed, with no request and no attempt, and other outlets are read
    meanwhile."""
    reader.step = step(outlet_gap_seconds=30, time=reader.time)
    first = reader.lead("https://www.theguardian.com/science/2019/may/01/synthetic-teeth-1")
    second = reader.lead("https://www.theguardian.com/science/2019/may/02/synthetic-teeth-2")
    other = reader.lead("https://www.bbc.co.uk/news/health-synthetic-teeth")
    began = reader.time.now()

    report = reader.read(by_the_step_clock=True)

    asked = [body["url"] for body in reader.page_reader.asked]
    assert sum("theguardian.com" in url for url in asked) == 1
    assert report.later == 1
    assert sorted(lead.read_outcome is None for lead in (first, second)) == [False, True]
    assert other.read_outcome is not None
    [put_off] = [lead for lead in (first, second) if lead.read_outcome is None]
    entry = reader.entry(put_off)
    assert (entry.outcome, entry.attempts, entry.reason) == (
        WorkOutcome.LATER,
        0,
        "outlet_just_asked",
    )
    assert entry.reason_values is not None and entry.reason_values["outlet"] == "theguardian.com"
    assert entry.not_before == began + timedelta(seconds=30)

    # Once the gap has passed, a later run asks the outlet again.
    assert entry.not_before is not None
    reader.time.advance(entry.not_before - timedelta(seconds=1) - reader.time.now())
    assert count(reader.session, reader.step, 3, now=reader.time.now()).due == 0
    reader.time.advance(timedelta(seconds=1))
    reader.step = step(outlet_gap_seconds=30, time=reader.time)
    reader.read(by_the_step_clock=True)

    assert first.read_outcome is not None and second.read_outcome is not None


def test_a_run_narrowed_to_a_period_leaves_older_leads_due(reader: Reader):
    """With a first day set, only leads first shared on or after it are read; an older
    lead is not read and stays out of the run's count of what is due."""
    older = reader.lead(
        "https://www.theguardian.com/science/2019/may/04/synthetic-teeth",
        shared_at=datetime(2024, 6, 1, tzinfo=UTC),
    )
    newer = reader.lead(
        "https://www.bbc.co.uk/news/health-synthetic-teeth",
        shared_at=datetime(2025, 3, 1, tzinfo=UTC),
    )
    reader.step = step(read_since=date(2025, 1, 1))

    report = reader.read()

    assert (older.read_outcome, report.remaining_due) == (None, 0)
    assert newer.read_outcome is not None
