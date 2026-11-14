"""Reading a passed link lead's article into a source article or a new claim. Scenario
names are from openspec lead-reading. The outlets, pages and model here are fakes, and
every word of every page is synthetic: no article text may be stored, tests included."""

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

import httpx
import pytest
from pydantic_ai.messages import ModelResponse, ToolCallPart
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backfill_support import same_session
from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.link_funnel import funnel
from thenwhat.backfill.link_read import (
    NO_DATE,
    NO_HEADLINE,
    NO_NAME,
    REFUSED_BY_ROBOTS,
    LinkRead,
    NotMeasured,
    ReadClient,
)
from thenwhat.backfill.link_screen import REGISTRY_TRIAL, TITLE_NAMES_CLAIM
from thenwhat.backfill.runner import RunReport, run_step
from thenwhat.claims.entry import add_article, add_claim, articles_of
from thenwhat.db.models import (
    Base,
    Claim,
    LinkLead,
    LinkLeadLabel,
    LinkLeadLink,
    LinkShare,
    LlmUsage,
    WorkEntry,
)
from thenwhat.decide.core import BackendAnswer
from thenwhat.domain import (
    Decider,
    LeadVerdict,
    OutletKind,
    ReadOutcome,
    ReviewState,
    ScreenOutcome,
    WorkOutcome,
)
from thenwhat.extract.retrieve import ArticleRetriever
from thenwhat.llm.client import Llm, LlmSettings
from thenwhat.review.decisions import record_decision
from thenwhat.statements.service import StatementChecker

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
        self.forbidding: set[str] = set()
        self.asked: list[str] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        host, path = request.url.host, request.url.path
        if path == "/robots.txt":
            rules = "Disallow: /" if host in self.forbidding else "Allow: /"
            return httpx.Response(200, text=f"User-agent: *\n{rules}\n")
        if host == "archive.org":
            return httpx.Response(200, json={"archived_snapshots": {}})
        self.asked.append(f"{host}{path}")
        found = self.pages.get(f"{host}{path}")
        return httpx.Response(200, text=found) if found else httpx.Response(404)


class Verticals:
    """A decision backend that chooses one vertical with one probability, and says every
    reported statement is in its article."""

    name = "fake"

    def __init__(self, vertical: str = "mouth-and-teeth", probability: float = 0.93) -> None:
        self.vertical = vertical
        self.probability = probability

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        rest = (1 - self.probability) / (len(options) - 1)
        chances = {option: rest for option in options}
        chances[self.vertical] = self.probability
        return BackendAnswer(self.vertical, chances)

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
            retriever=ArticleRetriever(
                contact_email="ops@thenwhat.test", transport=httpx.MockTransport(self.web)
            ),
            allowances=Allowances(same_session(session), {}, fake_time, outlet_interval_seconds=10),
            make_llm=lambda at: Llm(at, settings, model=model, now=lambda: NOW),
            make_checker=lambda at: StatementChecker(self.backend),
            make_backend=lambda at: self.backend,
        )
        self.step = step()

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

    def read(self, limit: int | None = None) -> RunReport:
        return run_step(
            same_session(self.session),
            self.step,
            self.client,
            now=lambda: NOW,
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
    assert (claim.review_state, claim.reviewed_by) == (ReviewState.APPROVED, Decider.RULE)
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


# --- a claim that exists ---------------------------------------------------------------


def test_an_article_for_a_tracked_claim_is_added_and_the_claim_is_left_as_reviewed(
    reader: Reader,
):
    """Scenarios: An earlier report of a tracked claim, A decided claim"""
    claim = tracked_claim(reader.session)
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    assert len(articles_of(reader.session, claim)) == 2
    assert claim.first_reported_date == date(2019, 5, 4)
    assert (claim.headline, claim.summary) == ("The reviewed headline", "The reviewed summary.")
    assert (claim.review_state, claim.reviewed_by) == (ReviewState.APPROVED, Decider.HUMAN)
    assert reader.session.scalars(select(Claim)).all() == [claim]


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


def test_an_outlet_that_forbids_the_fetch_is_not_asked_for_the_page(reader: Reader):
    """Scenario: Robots.txt forbids the fetch"""
    lead = reader.lead()
    reader.web.forbidding.add("www.theguardian.com")

    first = reader.read()
    second = reader.read()

    assert (lead.read_outcome, lead.read_detail) == (ReadOutcome.CANNOT_BE_READ, REFUSED_BY_ROBOTS)
    assert (first.nothing_found, second.processed) == (1, 0)
    assert (reader.web.asked, reader.prompts) == ([], [])


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


def test_a_dead_link_with_no_snapshot_cannot_be_read(reader: Reader):
    """Scenario: A dead link with no snapshot"""
    lead = reader.lead(serves=None)

    reader.read()

    assert lead.read_outcome is ReadOutcome.CANNOT_BE_READ
    assert "no archived snapshot" in (lead.read_detail or "")
    assert reader.prompts == []


def test_two_leads_on_one_outlet_are_fetched_the_interval_apart(reader: Reader):
    """Scenario: Two processes, one outlet"""
    reader.lead()
    reader.lead(
        "https://www.theguardian.com/science/2019/may/04/other", serves=page(published=None)
    )

    reader.read()

    assert reader.time.slept == [10.0]


# --- enough articles, and the order of reading -------------------------------------------


def link(session: Session, lead: LinkLead, kind: str, record_id: int, reason: str) -> None:
    session.add(
        LinkLeadLink(link_lead_id=lead.id, record_kind=kind, record_id=record_id, reason=reason)
    )
    session.flush()


def test_a_lead_for_a_claim_with_enough_articles_is_held_unless_it_is_earlier(reader: Reader):
    """Scenarios: A much-reported claim, An earlier article"""
    claim = tracked_claim(reader.session, articles=3, first=date(2021, 3, 1))
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


# --- no claim --------------------------------------------------------------------------


def test_an_unsure_vertical_makes_no_claim_and_lists_the_lead(reader: Reader):
    """Scenario: No confident vertical"""
    reader.backend.probability = 0.5
    lead = reader.lead()

    report = reader.read()

    assert (report.nothing_found, lead.read_outcome) == (1, ReadOutcome.NEEDS_VERTICAL)
    assert "EX-1 antibody for tooth agenesis" in (lead.read_detail or "")
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
    assert (found.read, found.new_approved_by_rule, found.new_rejected_by_rule) == (2, 1, 1)
    assert found.cannot_be_read == {NO_DATE: 1}
    assert found.undated_outlets == [("statnews.com", 1)]
    # Two reads were paid for; the scripted model's cost is recorded under the leads' name.
    assert found.reading_cost_usd > 0 and found.triage_cost_usd == 0
    # The report itself asks nobody anything.
    after = len(reader.web.asked)
    funnel(session, pass_above=0.7, reject_below=0.2)
    assert len(reader.web.asked) == after > asked
