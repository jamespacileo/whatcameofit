"""The news search step, its Media Cloud client and the outlet kinds, with synthetic
stories only. Scenario names are from openspec article-leads."""

import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backfill_support import NOW, add_trials, same_session
from thenwhat.backfill.allowance import Allowances
from thenwhat.backfill.errors import SourcePaused
from thenwhat.backfill.leads import hit_rates
from thenwhat.backfill import outlet_kinds
from thenwhat.backfill.ledger import count
from thenwhat.backfill.mediacloud import (
    MediaCloud,
    MissingKey,
    NothingToSearch,
    SourceRejectedKey,
    Story,
)
from thenwhat.backfill.news_search import NewsSearch, query_for
from thenwhat.backfill.outlet_kinds import kind_of, outlet_of
from thenwhat.backfill.runner import run_step
from thenwhat.config import SourceAllowance
from thenwhat.db.models import ArticleLead, RegistryTrial, WorkEntry
from thenwhat.domain import OutletKind, WorkOutcome
from thenwhat.export.build import build_export
from thenwhat.sources.base import MissingContact, SourceError

ALLOWED = {"mediacloud": SourceAllowance(requests=100, period_hours=168, interval_seconds=30)}


class Index:
    """A news index that answers each query from a table and counts its requests."""

    name = "mediacloud"

    def __init__(self, answers: dict[str, list[Story]] | None = None) -> None:
        self.answers = answers or {}
        self.queries: list[str] = []
        self.requests_made = 0

    def search(self, query: str, *, limit: int) -> list[Story]:
        self.queries.append(query)
        self.requests_made += 1
        return self.answers.get(query, [])[:limit]


def story(path: str, outlet: str = "news.example.org") -> Story:
    url = f"https://{outlet}/{path}"
    return Story(url, outlet, f"Synthetic headline {path}", NOW.date(), {"url": url})


def search(session: Session, index: Index, fake_time, **options):
    step = NewsSearch(time=fake_time, **options)
    report = run_step(same_session(session), step, index, now=fake_time.now, attempt_limit=3)
    return step, report


def leads(session: Session) -> list[ArticleLead]:
    return list(session.scalars(select(ArticleLead).order_by(ArticleLead.id)))


# --- the step ------------------------------------------------------------------------


def test_the_query_is_the_name_as_a_phrase_with_any_telling_word():
    assert query_for("Migalastat HCl", "fabry") == '"Migalastat HCl" AND (fabry)'
    assert query_for("Rituximab", "follicular lymphoma") == (
        '"Rituximab" AND (follicular OR lymphoma)'
    )


def test_coverage_found_is_stored_as_leads_and_the_entry_is_done(session: Session, fake_time):
    """Scenario: A trial with coverage"""
    [trial] = add_trials(session, 1)
    query = query_for("drug 0", "condition")
    index = Index({query: [story("a"), story("b", "healio.com")]})

    step, report = search(session, index, fake_time)

    first, second = leads(session)
    assert (report.done, report.nothing_found) == (1, 0)
    assert (first.registry_trial_id, first.url) == (trial.id, "https://news.example.org/a")
    assert (first.outlet, first.title) == ("news.example.org", "Synthetic headline a")
    assert (first.published_date, first.source_name) == (NOW.date(), "mediacloud")
    assert (first.search_query, first.fetched_at) == (query, fake_time.now())
    assert (first.outlet_kind, second.outlet_kind) == (OutletKind.UNKNOWN, OutletKind.TRADE_PRESS)
    [entry] = session.scalars(select(WorkEntry)).all()
    assert (entry.outcome, entry.requests_used) == (WorkOutcome.DONE, 1)


def test_no_coverage_stores_no_lead_and_the_entry_says_nothing_found(session: Session, fake_time):
    """Scenario: A trial with no coverage"""
    add_trials(session, 1)

    step, report = search(session, Index(), fake_time)

    assert leads(session) == []
    assert (report.done, report.nothing_found) == (0, 1)
    assert count(session, step, 3).due == 0


def test_a_trial_with_no_usable_name_is_never_searched(session: Session, fake_time):
    """Scenario: Only a placebo or a description"""
    add_trials(session, 2, name=None)
    index = Index()

    step, report = search(session, index, fake_time)

    assert index.queries == [] and report.processed == 0
    assert session.scalars(select(WorkEntry)).all() == []


def test_at_most_the_configured_number_of_leads_is_kept(session: Session, fake_time):
    add_trials(session, 1)
    query = query_for("drug 0", "condition")
    index = Index({query: [story(str(number)) for number in range(8)]})

    search(session, index, fake_time, leads_per_trial=3)

    assert len(leads(session)) == 3


def test_an_article_found_again_for_the_same_trial_adds_nothing(session: Session, fake_time):
    """Scenario: The same article found twice"""
    [trial] = add_trials(session, 1)
    query = query_for("drug 0", "condition")
    index = Index({query: [story("a")]})
    step = NewsSearch(time=fake_time)

    for _ in range(2):
        step.run(session, trial, index)

    assert len(leads(session)) == 1


def test_one_article_found_for_two_trials_gives_each_its_own_lead(session: Session, fake_time):
    """Scenario: One article, two trials"""
    first, second = add_trials(session, 2)
    shared = story("shared")
    index = Index(
        {query_for("drug 0", "condition"): [shared], query_for("drug 1", "condition"): [shared]}
    )

    search(session, index, fake_time)

    assert [(lead.registry_trial_id, lead.url) for lead in leads(session)] == [
        (first.id, shared.url),
        (second.id, shared.url),
    ]


def test_the_export_is_the_same_before_and_after_leads_are_stored(session: Session, fake_time):
    """Scenario: Export after a search"""
    add_trials(session, 3)
    before = build_export(session, now=NOW).model_dump_json()
    answers = {query_for(f"drug {n}", "condition"): [story(f"article-{n}")] for n in range(3)}

    search(session, Index(answers), fake_time)

    assert len(leads(session)) == 3
    assert build_export(session, now=NOW).model_dump_json() == before


# --- outlet kinds ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("domain", "kind"),
    [
        ("theguardian.com", OutletKind.GENERAL_NEWS),
        ("www.bbc.co.uk", OutletKind.GENERAL_NEWS),
        ("uk.news.yahoo.com", OutletKind.GENERAL_NEWS),
        ("healio.com", OutletKind.TRADE_PRESS),
        ("multiplesclerosisnewstoday.com", OutletKind.TRADE_PRESS),
        ("medicalnewstoday.com", OutletKind.GENERAL_NEWS),
        ("prnewswire.com", OutletKind.PRESS_RELEASE),
        ("a-site-on-no-list.example", OutletKind.UNKNOWN),
        ("notthebbc.com", OutletKind.UNKNOWN),
    ],
)
def test_outlet_kind_is_set_by_rule_from_the_domain(domain: str, kind: OutletKind):
    """Scenarios: A newswire copy, An outlet not yet listed"""
    assert kind_of(domain) is kind


def test_the_outlet_is_the_address_host_without_www():
    assert outlet_of("https://www.Healio.com/news/x?y=1") == "healio.com"


# --- hit rate report ---------------------------------------------------------------------


def test_the_hit_rate_counts_trials_with_a_lead_in_all_and_by_outlet_kind(
    session: Session, fake_time
):
    """Scenario: After a sample run"""
    add_trials(session, 10)
    answers = {
        query_for("drug 0", "condition"): [story("a", "theguardian.com"), story("b", "healio.com")],
        query_for("drug 1", "condition"): [story("c", "healio.com"), story("d", "onclive.com")],
        query_for("drug 2", "condition"): [story("e", "prnewswire.com")],
    }
    step, _ = search(session, Index(answers), fake_time)

    rates = hit_rates(session, step)

    assert (rates.processed, rates.with_a_lead, rates.share(rates.with_a_lead)) == (10, 3, 30)
    assert rates.by_kind == {
        OutletKind.GENERAL_NEWS: 1,
        OutletKind.TRADE_PRESS: 2,
        OutletKind.PRESS_RELEASE: 1,
        OutletKind.UNKNOWN: 0,
    }


def test_the_hit_rate_of_nothing_processed_is_zero(session: Session):
    add_trials(session, 2)

    rates = hit_rates(session, NewsSearch())

    assert (rates.processed, rates.with_a_lead, rates.share(0)) == (0, 0, 0)


# --- Media Cloud client --------------------------------------------------------------------


class Service:
    def __init__(self, answer: httpx.Response) -> None:
        self.answer = answer
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.answer


def media_cloud(session: Session, fake_time, service: Service, **options) -> MediaCloud:
    options.setdefault("api_key", "synthetic-key")
    options.setdefault("contact_email", "ops@thenwhat.test")
    options.setdefault("collection_ids", "34412234")
    return MediaCloud(
        allowances=Allowances(same_session(session), ALLOWED, fake_time),
        transport=httpx.MockTransport(service),
        time=fake_time,
        **options,
    )


def test_a_search_asks_for_stories_and_returns_address_outlet_title_and_date(
    session: Session, fake_time, fixture_json
):
    service = Service(httpx.Response(200, json=fixture_json("mediacloud/story_list.json")))
    client = media_cloud(
        session, fake_time, service, collection_ids="34412234, 9272347", source_ids=" 236253"
    )

    stories = client.search('"Exampletrep" AND (migraine)', limit=20)

    [request] = service.requests
    params = dict(request.url.params)
    assert request.url.path == "/api/search/story-list"
    assert params["q"] == '"Exampletrep" AND (migraine)'
    assert (params["start"], params["end"]) == ("2010-01-01", fake_time.now().date().isoformat())
    assert (params["platform"], params["page_size"]) == ("onlinenews-mediacloud", "20")
    assert (params["cs"], params["ss"]) == ("34412234,9272347", "236253")
    assert "expanded" not in params
    assert request.headers["Authorization"] == "Token synthetic-key"
    assert "mailto:ops@thenwhat.test" in request.headers["User-Agent"]
    assert client.requests_made == 1
    first, second, third = stories
    assert first.url == "https://www.news.example.org/health/exampletrep-migraine"
    assert (first.outlet, str(first.published)) == ("news.example.org", "2026-10-03")
    assert first.title.startswith("Synthetic headline")
    assert (second.outlet, third.outlet) == ("healio.com", "prnewswire.com")
    assert third.published is None


def test_any_text_field_is_removed_before_a_result_is_kept(session: Session, fake_time):
    """Scenario: The index returns an excerpt"""
    made_up = "MADE-UP WORDS STANDING IN FOR AN ARTICLE"
    result = {
        "url": "https://news.example.org/a",
        "title": "Synthetic headline",
        "publish_date": "2026-10-03",
        "text": made_up,
        "Snippet": made_up,
        "excerpt": made_up,
        "summary": made_up,
    }
    [trial] = add_trials(session, 1)
    client = media_cloud(
        session, fake_time, Service(httpx.Response(200, json={"stories": [result]}))
    )

    NewsSearch(time=fake_time).run(session, trial, client)

    [lead] = leads(session)
    assert lead.raw_result == {
        "url": "https://news.example.org/a",
        "title": "Synthetic headline",
        "publish_date": "2026-10-03",
    }
    assert made_up not in str(lead.raw_result)


def test_no_search_is_sent_without_a_key_a_contact_address_or_anything_to_search(
    session: Session, fake_time
):
    service = Service(httpx.Response(200, json={"stories": []}))

    with pytest.raises(MissingKey, match="MEDIACLOUD_API_KEY"):
        media_cloud(session, fake_time, service, api_key=None).search("q", limit=5)
    with pytest.raises(MissingContact, match="CONTACT_EMAIL"):
        media_cloud(session, fake_time, service, contact_email=None).search("q", limit=5)
    with pytest.raises(NothingToSearch, match="MEDIACLOUD_COLLECTION_IDS"):
        media_cloud(session, fake_time, service, collection_ids=" ").search("q", limit=5)
    assert service.requests == []


def test_too_many_requests_pauses_the_source(session: Session, fake_time):
    service = Service(httpx.Response(429, headers={"Retry-After": "900"}))
    client = media_cloud(session, fake_time, service)

    with pytest.raises(SourcePaused, match="asked too often"):
        client.search("q", limit=5)
    with pytest.raises(SourcePaused):
        client.search("q", limit=5)
    assert len(service.requests) == 1


def test_a_rejected_key_stops_the_run_and_counts_no_attempt(session: Session, fake_time):
    add_trials(session, 3)
    client = media_cloud(session, fake_time, Service(httpx.Response(403, text="forbidden")))
    step = NewsSearch(time=fake_time)

    with pytest.raises(SourceRejectedKey):
        client.search("q", limit=5)
    report = run_step(same_session(session), step, client, now=fake_time.now, attempt_limit=3)

    assert report.processed == 0 and "did not accept the key" in (report.stopped or "")
    assert session.scalars(select(WorkEntry)).all() == []


def test_another_refusal_fails_the_record(session: Session, fake_time):
    client = media_cloud(session, fake_time, Service(httpx.Response(400, text="bad query")))

    with pytest.raises(SourceError, match="status 400"):
        client.search("q", limit=5)


def test_trials_seeded_for_these_tests_are_in_the_steps_scope(session: Session):
    add_trials(session, 2)
    add_trials(session, 1, registry="other", name=None)

    in_scope = session.scalars(select(RegistryTrial).where(NewsSearch().scope())).all()

    assert len(in_scope) == 2


# --- outlet names ----------------------------------------------------------------------


def test_every_listed_outlet_has_a_display_name_and_no_name_is_for_an_unlisted_one():
    listed = outlet_kinds.GENERAL_NEWS | outlet_kinds.TRADE_PRESS | outlet_kinds.PRESS_RELEASE

    assert set(outlet_kinds.OUTLET_NAMES) == listed
    assert all(name == name.strip() and name for name in outlet_kinds.OUTLET_NAMES.values())


@pytest.mark.parametrize(
    ("domain", "name"),
    [
        ("theguardian.com", "The Guardian"),
        ("www.bbc.co.uk", "BBC News"),
        ("ca.news.yahoo.com", "Yahoo News"),
        ("sciencedaily.com", "ScienceDaily"),
        # Listed by its ending only, so it has a kind and no name.
        ("multiplesclerosisnewstoday.com", None),
        ("a-site-on-no-list.example", None),
        ("notthebbc.com", None),
    ],
)
def test_an_outlet_is_named_from_the_list_and_never_from_its_domain(domain, name):
    assert outlet_kinds.name_of(domain) == name
