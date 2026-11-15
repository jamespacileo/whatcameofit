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
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backfill_support import same_session
from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.link_funnel import funnel
from thenwhat.backfill.link_read import (
    CLAIM_IDENTITY_LOCK,
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
from thenwhat.decide.steps import (
    ESTABLISHED_TREATMENT,
    NEW_TREATMENT,
    NO_SUCH_CLAIM,
    NOT_ONE_TREATMENT,
    SAME_CLAIM,
    TREATMENT_REPORT,
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
        # What the treatment-report decision answers (a new treatment unless a test says
        # otherwise), with what probability, and what it was shown.
        self.report_kind = NEW_TREATMENT
        self.report_probability = 0.95
        self.report_asked: list[str] = []

    def answer(self, step: str, state: str, options: list[str]) -> BackendAnswer:
        chosen, probability = self.vertical, self.probability
        if step == TREATMENT_REPORT:
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
    reader.backend.report_kind = ESTABLISHED_TREATMENT
    lead = reader.lead()

    reader.read()

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.ADDED_TO_CLAIM, claim.id)
    assert lead.read_detail == "an established treatment in the news"


def test_new_and_established_together_decide_that_it_is_one_treatment(reader: Reader):
    """Scenario: Unsure whether new or established"""
    reader.backend.report_kind, reader.backend.report_probability = ESTABLISHED_TREATMENT, 0.4
    lead = reader.lead()

    reader.read()

    # 0.4 established and 0.3 new: about one treatment at 0.7, whichever it is.
    assert lead.read_outcome is ReadOutcome.NEW_CLAIM


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
    # Asked once for each later article, and shown names and conditions only.
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


def test_a_trial_the_page_names_becomes_a_scored_candidate_and_is_not_approved_by_it(
    session: Session, fake_time
):
    """Scenario: An article that links its trial"""
    from types import SimpleNamespace

    from test_related_research import Registry
    from thenwhat.db.models import Entity, EntityMatch
    from thenwhat.resolve.reasons import NAMED_IN_ARTICLE

    reader = Reader(session, fake_time)
    registry = Registry()
    reader.client.make_research = lambda at: SimpleNamespace(registry=registry, papers=None)
    linked = page().replace(
        "</main>",
        '<a href="https://clinicaltrials.gov/study/NCT04184622">the trial</a>'
        '<a href="https://doi.org/10.1000/named">the paper</a></main>',
    )
    lead = reader.lead(serves=linked)

    reader.read()

    assert (lead.read_outcome, lead.read_detail) == (ReadOutcome.NEW_CLAIM, None)
    [match] = session.scalars(
        select(EntityMatch)
        .join(Entity, Entity.id == EntityMatch.entity_id)
        .where(Entity.claim_id == lead.claim_id)
    )
    assert (match.external_id, match.reasons) == ("NCT04184622", [NAMED_IN_ARTICLE])
    # Scored like any candidate; with no accept rule set it stays pending.
    assert match.score == pytest.approx(0.9) and match.review_state is ReviewState.PENDING
    # No literature source is configured, so the paper is left unrecorded.
    assert registry.fetched == ["NCT04184622"]
