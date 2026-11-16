"""Bringing stored link leads to the current form of the address key. Scenario names
are from openspec address-identity. Every lead here is synthetic, and the backend is a fake."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backfill_support import Client, same_session
from test_link_triage import Clock, Headlines
from thenwhat.backfill.address import KEY_VERSION
from thenwhat.backfill.errors import KeysOutOfDate
from thenwhat.backfill.link_load import load_links
from thenwhat.backfill.link_readers import HACKER_NEWS, SharedLink
from thenwhat.backfill.link_rekey import rekey_links, survey
from thenwhat.backfill.link_screen import LinkScreen
from thenwhat.backfill.link_triage import DecisionClient, LinkTriage
from thenwhat.backfill.outlet_kinds import kind_of
from thenwhat.backfill.runner import run_step
from thenwhat.db.models import LinkLead, LinkLeadLabel, LinkShare, WorkEntry
from thenwhat.domain import Decider, LeadVerdict, ScreenOutcome

NOW = datetime(2026, 11, 20, 9, 0, tzinfo=UTC)
WHEN = datetime(2019, 5, 4, 10, 30, tzinfo=UTC)
STORY = "https://www.bbc.com/news/health-1"


def earlier_lead(
    session: Session, url: str, key: str, *, shared_at: datetime = WHEN, item: int = 1
) -> LinkLead:
    """A lead as the first form of the key stored it, with one share."""
    outlet = key.split("/", 1)[0]
    lead = LinkLead(
        url=url,
        url_key=key,
        url_key_version=1,
        outlet=outlet,
        outlet_kind=kind_of(outlet),
        title="A trial result",
        first_shared_at=shared_at,
    )
    session.add(lead)
    session.flush()
    session.add(
        LinkShare(
            link_lead_id=lead.id,
            platform=HACKER_NEWS,
            community=HACKER_NEWS,
            shared_at=shared_at,
            score=10,
            item_number=item,
        )
    )
    session.flush()
    return lead


def leads(session: Session) -> list[LinkLead]:
    session.expire_all()
    return list(session.scalars(select(LinkLead).order_by(LinkLead.id)))


def screen(session: Session, step: LinkScreen):
    return run_step(same_session(session), step, Client(), now=lambda: NOW, attempt_limit=3)


def triage(session: Session, step: LinkTriage, backend: Headlines):
    return run_step(
        same_session(session),
        step,
        DecisionClient(lambda _: backend),
        now=lambda: NOW,
        attempt_limit=3,
    )


def test_two_leads_of_one_article_become_one_lead_with_the_shares_of_both(session: Session):
    """Scenario: Two stored leads are one article under the current form"""
    plain = earlier_lead(session, STORY, "bbc.com/news/health-1")
    earlier_lead(
        session,
        f"{STORY}?mbid=synd_feed",
        "bbc.com/news/health-1?mbid=synd_feed",
        shared_at=WHEN - timedelta(days=2),
        item=2,
    )

    report = rekey_links(same_session(session), steps=[])

    [lead] = leads(session)
    assert (report.checked, report.unchanged, report.merged, report.shares_moved) == (2, 1, 1, 1)
    assert (lead.id, lead.url_key, lead.url_key_version) == (
        plain.id,
        "bbc.com/news/health-1",
        KEY_VERSION,
    )
    assert lead.first_shared_at == WHEN - timedelta(days=2)
    shares = session.scalars(select(LinkShare)).all()
    assert {share.link_lead_id for share in shares} == {lead.id}
    assert sorted(share.item_number or 0 for share in shares) == [1, 2]


def test_a_share_both_leads_hold_is_kept_once_and_a_label_moves(session: Session):
    """Scenario: Two stored leads are one article under the current form"""
    first = earlier_lead(session, f"{STORY}?_r=0", "bbc.com/news/health-1?_r=0")
    second = earlier_lead(session, f"{STORY}?_r=1", "bbc.com/news/health-1?_r=1")
    session.add(
        LinkLeadLabel(
            link_lead_id=second.id,
            label=LeadVerdict.TREATMENT_REPORT,
            labelled_by=Decider.HUMAN,
            labelled_at=NOW,
        )
    )
    session.flush()

    report = rekey_links(same_session(session), steps=[])

    [lead] = leads(session)
    assert (lead.id, lead.url_key) == (first.id, "bbc.com/news/health-1")
    assert (report.rekeyed, report.merged, report.shares_moved) == (1, 1, 0)
    assert len(session.scalars(select(LinkShare)).all()) == 1
    [label] = session.scalars(select(LinkLeadLabel)).all()
    assert label.link_lead_id == lead.id


def test_a_lead_that_was_scored_is_kept_and_is_not_scored_again(session: Session):
    """Scenario: A lead that was scored is not scored again"""
    unscored_first = earlier_lead(session, f"{STORY}?mbid=a", "bbc.com/news/health-1?mbid=a")
    scored = earlier_lead(session, STORY, "bbc.com/news/health-1", item=2)
    alone = earlier_lead(
        session, "https://www.bbc.com/news/health-2?_r=0", "bbc.com/news/health-2?_r=0", item=3
    )
    screening, scoring = LinkScreen(), LinkTriage(Clock())
    steps = [screening, scoring]
    screen(session, screening)
    # The first lead is left unscored, as a lead loaded after a triage run would be.
    unscored_first.screen_outcome = ScreenOutcome.UNLISTED_OUTLET
    session.flush()
    backend = Headlines(session)
    triage(session, scoring, backend)
    assert [len(call) for call in backend.calls] == [2]
    paid_for = {lead.id: lead.triage_score for lead in (scored, alone)}

    rekey_links(same_session(session), steps)
    rescreened = screen(session, screening)
    again = triage(session, scoring, backend)

    remaining = leads(session)
    assert [lead.id for lead in remaining] == [scored.id, alone.id]
    assert [lead.url_key for lead in remaining] == [
        "bbc.com/news/health-1",
        "bbc.com/news/health-2",
    ]
    # Screening asks nothing and looks again at the lead whose key changed. Triage
    # asks a model, and is not asked again for either.
    assert rescreened.done == 1
    assert (again.processed, again.remaining_due) == (0, 0)
    assert [len(call) for call in backend.calls] == [2]
    assert {lead.id: lead.triage_score for lead in remaining} == paid_for
    entries = session.scalars(select(WorkEntry).where(WorkEntry.step == "link_triage")).all()
    assert sorted(entry.record_id for entry in entries) == [scored.id, alone.id]


def test_a_second_run_finds_nothing_to_do(session: Session):
    """Scenario: Bringing the leads up to date twice"""
    earlier_lead(session, f"{STORY}?_r=0", "bbc.com/news/health-1?_r=0")
    rekey_links(same_session(session), steps=[])

    second = rekey_links(same_session(session), steps=[])

    assert second.checked == 0
    assert survey(session).checked == 0


def test_a_survey_says_what_would_be_done_and_changes_nothing(session: Session):
    """Scenario: Looking before bringing the leads up to date"""
    earlier_lead(session, STORY, "bbc.com/news/health-1")
    earlier_lead(session, f"{STORY}?mbid=a", "bbc.com/news/health-1?mbid=a", item=2)
    earlier_lead(session, "https://www.bbc.com/news/health-2?_r=0", "bbc.com/news/health-2?_r=0")

    report = survey(session)

    assert (report.checked, report.unchanged, report.rekeyed, report.merged) == (3, 1, 1, 1)
    assert [lead.url_key_version for lead in leads(session)] == [1, 1, 1]


def test_a_load_is_refused_while_a_lead_is_keyed_under_an_earlier_form(session: Session):
    """Scenario: Loading before the stored leads are up to date"""
    earlier_lead(session, f"{STORY}?_r=0", "bbc.com/news/health-1?_r=0")
    post = SharedLink(
        url=STORY, community=HACKER_NEWS, shared_at=WHEN, score=10, title="T", item_number=9
    )

    with pytest.raises(KeysOutOfDate, match="rekey-links"):
        load_links(same_session(session), HACKER_NEWS, [post], steps=[])

    assert len(leads(session)) == 1
