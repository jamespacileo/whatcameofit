"""Screening link leads by rule and from stored data. Scenario names are from openspec
lead-screening. Every lead, claim and trial here is synthetic."""

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backfill_support import NOW, Client, add_trials, same_session
from thenwhat.backfill.address import article_key
from thenwhat.backfill.link_load import load_links
from thenwhat.backfill.link_readers import HACKER_NEWS, REDDIT, SharedLink
from thenwhat.backfill.link_report import screening_report
from thenwhat.backfill.link_screen import (
    CLAIM,
    FOUND_BY_NEWS_SEARCH,
    REGISTRY_TRIAL,
    TITLE_NAMES_CLAIM,
    TITLE_NAMES_TRIAL,
    LinkScreen,
)
from thenwhat.backfill.runner import run_step
from thenwhat.claims.entry import add_article, add_claim
from thenwhat.db.models import (
    ArticleLead,
    Claim,
    DecisionLog,
    Entity,
    LinkLead,
    LinkLeadLink,
    LlmUsage,
    RegistryTrial,
)
from thenwhat.domain import EntityType, OutletKind, ScreenOutcome

WHEN = datetime(2019, 5, 4, 10, 30, tzinfo=UTC)


def share(
    session: Session,
    url: str,
    title: str = "A synthetic headline",
    *,
    platform: str = HACKER_NEWS,
    community: str = HACKER_NEWS,
    item: int | None = 1,
) -> LinkLead:
    post = SharedLink(
        url=url, community=community, shared_at=WHEN, score=10, title=title, item_number=item
    )
    load_links(same_session(session), platform, [post], steps=[])
    return session.scalars(select(LinkLead).where(LinkLead.url_key == article_key(url))).one()


def screen(session: Session, step: LinkScreen | None = None) -> Client:
    client = Client()
    run_step(same_session(session), step or LinkScreen(), client, now=lambda: NOW, attempt_limit=3)
    return client


def links(session: Session, lead: LinkLead) -> list[tuple[str, int, str]]:
    return [
        (link.record_kind, link.record_id, link.reason)
        for link in session.scalars(
            select(LinkLeadLink)
            .where(LinkLeadLink.link_lead_id == lead.id)
            .order_by(LinkLeadLink.id)
        )
    ]


def claim(session: Session, slug: str = "exa-one-condition", intervention: str = "Exavir") -> Claim:
    return add_claim(
        session,
        slug=slug,
        headline="A synthetic claim",
        vertical="mouth-and-teeth",
        intervention=intervention,
        indication="synthetic condition",
    )


def trial(session: Session, name: str, indication: str, number: int) -> RegistryTrial:
    record = RegistryTrial(
        registry_name="demo-registry",
        external_id=f"S{number:04d}",
        title=f"A synthetic trial of {name}",
        conditions=[indication],
        interventions=[{"type": "DRUG", "name": name}],
        phases=["PHASE3"],
        search_name=name,
        search_indication=indication,
        raw_payload={},
        fetched_at=NOW,
    )
    session.add(record)
    session.flush()
    return record


# --- the outlet rule and articles already tracked ------------------------------------


def test_a_lead_on_a_listed_outlet_is_in_scope(session: Session):
    """Scenario: A link to a listed outlet"""
    lead = share(session, "https://www.theguardian.com/science/2019/synthetic-report")

    screen(session)

    assert lead.screen_outcome is ScreenOutcome.IN_SCOPE


def test_a_lead_on_a_domain_on_no_list_goes_no_further(session: Session):
    """Scenario: A link to a code repository"""
    lead = share(session, "https://github.com/example/synthetic-repository")

    screen(session)

    assert lead.screen_outcome is ScreenOutcome.UNLISTED_OUTLET
    assert links(session, lead) == []


def test_a_domain_added_to_the_list_puts_its_leads_in_scope_on_the_next_screening(
    session: Session, monkeypatch
):
    """Scenario: A domain is added to the list"""
    added = share(session, "https://health.example.org/news/synthetic-report")
    other = share(session, "https://github.com/example/another", item=2)
    screen(session)
    monkeypatch.setattr(
        "thenwhat.backfill.link_screen.kind_of",
        lambda domain: (
            OutletKind.TRADE_PRESS if domain == "health.example.org" else OutletKind.UNKNOWN
        ),
    )
    again = LinkScreen()
    again.version += 1

    screen(session, again)

    assert added.screen_outcome is ScreenOutcome.IN_SCOPE
    assert added.outlet_kind is OutletKind.TRADE_PRESS
    assert other.screen_outcome is ScreenOutcome.UNLISTED_OUTLET


def test_a_shared_article_that_a_claim_already_has_is_already_tracked(session: Session):
    """Scenario: A shared article that a claim already has"""
    tracked = claim(session)
    add_article(
        session,
        tracked.slug,
        url="https://www.theguardian.com/science/2019/synthetic-report",
        outlet="The Guardian",
        title="A synthetic headline",
        published_date=date(2019, 5, 4),
    )
    lead = share(
        session, "https://amp.theguardian.com/science/2019/synthetic-report?utm_source=share"
    )

    screen(session)

    assert lead.screen_outcome is ScreenOutcome.ALREADY_TRACKED
    assert [(kind, record) for kind, record, _ in links(session, lead)] == [(CLAIM, tracked.id)]


# --- links to stored records ---------------------------------------------------------


def test_an_address_the_news_search_found_is_linked_to_its_trial(session: Session):
    """Scenario: An address the news search already found"""
    [found_for] = add_trials(session, 1)
    session.add(
        ArticleLead(
            registry_trial_id=found_for.id,
            url="https://www.statnews.com/2019/05/04/synthetic-report/",
            outlet="statnews.com",
            title="A synthetic headline",
            outlet_kind=OutletKind.TRADE_PRESS,
            source_name="mediacloud",
            search_query="synthetic",
            raw_result={},
            fetched_at=NOW,
        )
    )
    session.flush()
    lead = share(session, "https://statnews.com/2019/05/04/synthetic-report")

    screen(session)

    assert links(session, lead) == [(REGISTRY_TRIAL, found_for.id, FOUND_BY_NEWS_SEARCH)]


def test_a_title_that_names_a_tracked_intervention_is_linked_to_its_claim(session: Session):
    """Scenario: A title that names a tracked intervention"""
    tracked = claim(session)
    intervention = session.scalars(
        select(Entity).where(Entity.claim_id == tracked.id, Entity.type == EntityType.INTERVENTION)
    ).one()
    intervention.synonyms = ["EXA-101"]
    session.flush()
    by_name = share(session, "https://www.bbc.com/news/health-1", "Exavir clears synthetic trial")
    by_code = share(
        session, "https://www.bbc.com/news/health-2", "New drug exa-101 shows promise", item=2
    )

    screen(session)

    assert links(session, by_name) == [(CLAIM, tracked.id, TITLE_NAMES_CLAIM)]
    assert links(session, by_code) == [(CLAIM, tracked.id, TITLE_NAMES_CLAIM)]


def test_a_name_inside_a_longer_word_is_not_a_match(session: Session):
    """Scenario: A name inside a longer word"""
    trial(session, "Iron", "anaemia", 1)
    lead = share(session, "https://www.bbc.com/news/sport-1", "Ironman finisher beats anaemia")

    screen(session)

    assert lead.screen_outcome is ScreenOutcome.IN_SCOPE
    assert links(session, lead) == []


def test_a_trial_is_linked_only_when_a_word_of_its_indication_is_in_the_title(session: Session):
    """Scenario: A common name without the indication"""
    for_anaemia = trial(session, "Iron", "anaemia", 1)
    trial(session, "Iron", "restless legs", 2)
    with_word = share(session, "https://www.bbc.com/news/health-3", "Iron eases anaemia in trial")
    without = share(session, "https://www.bbc.com/news/business-4", "Iron ore prices rise", item=2)

    screen(session)

    assert links(session, with_word) == [(REGISTRY_TRIAL, for_anaemia.id, TITLE_NAMES_TRIAL)]
    assert links(session, without) == []


def test_a_trial_named_by_its_own_disease_is_not_linked_by_that_one_word(session: Session):
    """Scenario: A name that is also the indication"""
    trial(session, "Diphtheria", "diphtheria", 1)
    with_another_word = trial(session, "Vitamin D", "vitamin deficiency", 2)
    outbreak = share(
        session, "https://www.bbc.com/news/health-6", "Two cases of deadly diphtheria detected"
    )
    advice = share(
        session,
        "https://www.bbc.com/news/health-7",
        "Scientist urges vitamin D supplements",
        item=2,
    )
    report = share(
        session, "https://www.bbc.com/news/health-8", "Vitamin D eases deficiency in trial", item=3
    )

    screen(session)

    assert links(session, outbreak) == []
    # "vitamin" is a word of the name, so it does not count as a word of the indication.
    assert links(session, advice) == []
    assert links(session, report) == [(REGISTRY_TRIAL, with_another_word.id, TITLE_NAMES_TRIAL)]


def test_at_most_the_configured_number_of_links_is_kept(session: Session):
    for number in range(5):
        trial(session, "Exavir", "synthetic condition", number)
    lead = share(session, "https://www.bbc.com/news/health-5", "Exavir tested in condition")

    screen(session, LinkScreen(links_max=3))

    assert len(links(session, lead)) == 3


# --- what screening costs --------------------------------------------------------------


def test_screening_sends_no_request_calls_no_model_and_records_no_spend(session: Session):
    """Scenario: Screening a million leads"""
    claim(session)
    for number in range(30):
        share(session, f"https://www.bbc.com/news/health-{number}", "Exavir again", item=number)

    client = screen(session)

    # The test suite fails any connection, so finishing at all shows no request was sent.
    assert client.requests_made == 0
    assert session.scalars(select(LlmUsage)).all() == []
    assert session.scalars(select(DecisionLog)).all() == []
    assert all(
        lead.screen_outcome is ScreenOutcome.IN_SCOPE for lead in session.scalars(select(LinkLead))
    )


# --- the report ------------------------------------------------------------------------


def test_the_report_counts_leads_by_where_they_were_shared(session: Session):
    """Scenario: After a load and a screening run"""
    tracked = claim(session)
    add_article(
        session,
        tracked.slug,
        url="https://www.statnews.com/2019/tracked",
        outlet="STAT",
        title="A synthetic headline",
        published_date=date(2019, 5, 4),
    )
    share(session, "https://www.bbc.com/news/health-1", "Exavir clears trial", item=1)
    share(session, "https://www.healio.com/news/2019/other", "Something else", item=2)
    share(session, "https://www.statnews.com/2019/tracked", "Tracked already", item=3)
    for number in range(3):
        share(session, f"https://github.com/example/{number}", "Code", item=10 + number)
    share(session, "https://gitlab.com/example/1", "Code", item=20)
    share(
        session,
        "https://www.bbc.com/news/health-1",
        "Exavir clears trial",
        platform=REDDIT,
        community="science",
        item=None,
    )
    screen(session)

    report = screening_report(session)

    hacker_news, reddit = report.places
    assert (hacker_news.platform, hacker_news.loaded, hacker_news.screened) == (HACKER_NEWS, 7, 7)
    assert hacker_news.in_scope == {
        OutletKind.GENERAL_NEWS: 1,
        OutletKind.TRADE_PRESS: 1,
        OutletKind.PRESS_RELEASE: 0,
    }
    assert (hacker_news.already_tracked, hacker_news.unlisted) == (1, 4)
    assert (hacker_news.linked_to_claim, hacker_news.linked_to_trial) == (1, 0)
    assert hacker_news.share(hacker_news.in_scope_total) == 29
    assert (reddit.community, reddit.loaded, reddit.linked_to_claim) == ("science", 1, 1)
    assert report.unlisted_domains == [("github.com", 3), ("gitlab.com", 1)]
