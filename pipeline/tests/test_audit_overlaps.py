"""Settling a read left unresolved because it overlaps a claim: attaching its article to
that claim, or saying it is no report of it. Scenario names are from openspec
lead-reading. Every page is synthetic and is served by the synthetic page reader."""

from collections.abc import Callable, Generator
from contextlib import contextmanager
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session
from typer.testing import CliRunner, Result

from test_link_reading import (
    HEADLINE,
    MARKER,
    NOW,
    SHARED_TITLE,
    Reader,
    page,
    stored_everywhere,
    tracked_claim,
)
from thenwhat.backfill.address import KEY_VERSION
from thenwhat.backfill.link_read import (
    NO_DATE,
    Attached,
    NotAnOverlap,
    NotAttached,
    dismiss_overlap,
    overlapping_read,
    reads_naming_live_claims,
)
from thenwhat.backfill.outlet_kinds import name_of
from thenwhat.backfill.steps import Deferred
from thenwhat.claims.entry import add_article, archive_claim, articles_of
from thenwhat.cli import app
from thenwhat.db.models import Claim, LinkLead
from thenwhat.domain import Decider, ReadOutcome, ReviewState
from thenwhat.review.decisions import record_decision

URL = "https://www.theguardian.com/science/2019/may/04/synthetic-teeth"


@pytest.fixture
def reader(session: Session, fake_time) -> Reader:
    return Reader(session, fake_time)


def overlapping(reader: Reader, *, serves: str = "") -> tuple[LinkLead, Claim]:
    """A lead whose read drafted the treatment and condition of an approved claim, with
    the decision not saying the article reports it: listed, pointing at nothing."""
    claim = tracked_claim(reader.session)
    lead = reader.lead(URL, serves=serves)
    reader.read()
    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.IDENTITY_UNRESOLVED, None)
    assert reads_naming_live_claims(reader.session) == [(lead, claim)]
    return lead, claim


def asked(reader: Reader) -> int:
    return len(reader.page_reader.asked)


# --- attaching -------------------------------------------------------------------------


def test_an_overlapping_reads_article_is_attached_with_the_pages_headline_and_date(
    reader: Reader,
):
    """Scenario: An overlapping read is attached to its claim"""
    lead, claim = overlapping(reader)
    reviewed = (claim.review_state, claim.reviewed_by, claim.reviewed_at, claim.awaiting_audit_at)
    assert claim.first_reported_date == date(2021, 3, 1)

    answer = reader.step.attach(reader.session, lead, claim, reader.client, by=Decider.ASSISTANT)

    assert isinstance(answer, Attached) and answer.added
    article = answer.article
    # The page's own headline and day, not the words or the time the link was shared with.
    assert (article.title, article.published_date) == (HEADLINE, date(2019, 5, 4))
    assert article.title != SHARED_TITLE and article.published_date != lead.first_shared_at.date()
    assert (article.outlet, article.url) == (name_of(lead.outlet), URL)
    assert article.content_hash is not None
    assert (lead.claim_id, lead.source_article_id) == (claim.id, article.id)
    assert lead.read_outcome is ReadOutcome.ADDED_TO_CLAIM
    assert f"attached to it by the assistant on {reader.time.now():%Y-%m-%d}" in (
        lead.read_detail or ""
    )
    assert "operator" not in (lead.read_detail or "")
    assert reads_naming_live_claims(reader.session) == []
    # The claim is as it was reviewed, on no hold, and is first reported when its
    # earliest article is.
    assert reviewed == (
        claim.review_state,
        claim.reviewed_by,
        claim.reviewed_at,
        claim.awaiting_audit_at,
    )
    assert (claim.review_state, claim.awaiting_audit_at) == (ReviewState.APPROVED, None)
    assert claim.first_reported_date == date(2019, 5, 4)
    # The reader was asked again, under its allowance, and the text is kept nowhere.
    assert (asked(reader), reader.client.requests_made) == (2, 2)
    assert MARKER not in stored_everywhere(reader.session)


def test_an_article_is_attached_only_to_an_approved_claim_that_is_not_archived(reader: Reader):
    """Scenario: An overlapping read of a claim that is not published is refused"""
    lead, claim = overlapping(reader)
    detail = lead.read_detail
    record_decision(claim, ReviewState.REJECTED, by=Decider.HUMAN, now=NOW)

    answer = reader.step.attach(reader.session, lead, claim, reader.client, by=Decider.HUMAN)

    assert isinstance(answer, NotAttached) and "is rejected" in answer.reason
    assert (lead.read_outcome, lead.read_detail) == (ReadOutcome.IDENTITY_UNRESOLVED, detail)
    assert (lead.claim_id, asked(reader)) == (None, 1)
    assert len(articles_of(reader.session, claim)) == 1

    record_decision(claim, ReviewState.APPROVED, by=Decider.HUMAN, now=NOW)
    archive_claim(reader.session, claim.slug, reason="synthetic fault", now=NOW)
    with pytest.raises(NotAnOverlap, match="is archived"):
        overlapping_read(reader.session, lead.id)


def test_a_lead_whose_address_the_claim_has_joins_that_article_without_a_request(reader: Reader):
    """Scenario: The claim already has the overlapping read's address"""
    lead, claim = overlapping(reader)
    had = add_article(
        reader.session,
        claim.slug,
        url=URL + "?utm_source=synthetic",
        outlet="The Guardian",
        title="A synthetic headline",
        published_date=date(2022, 1, 1),
    )

    answer = reader.step.attach(reader.session, lead, claim, reader.client, by=Decider.HUMAN)

    assert isinstance(answer, Attached) and not answer.added and answer.article is had
    assert (lead.claim_id, lead.source_article_id) == (claim.id, had.id)
    assert lead.read_outcome is ReadOutcome.ADDED_TO_CLAIM
    assert "by the operator" in (lead.read_detail or "")
    assert (asked(reader), len(articles_of(reader.session, claim))) == (1, 2)


def test_attaching_asks_the_reader_under_the_rules_of_a_read(reader: Reader):
    """Scenario: An overlapping read whose outlet is held, or whose page has no date"""
    lead, claim = overlapping(reader)
    detail = lead.read_detail
    reader.page_reader.not_now["www.theguardian.com"] = 7200

    stopped = reader.step.attach(reader.session, lead, claim, reader.client, by=Decider.HUMAN)
    held = reader.step.attach(reader.session, lead, claim, reader.client, by=Decider.HUMAN)

    # The reader's "not now" is kept as the outlet's hold: the second try asks nothing.
    assert isinstance(stopped, Deferred) and isinstance(held, Deferred)
    assert asked(reader) == 2

    # After the wait the page is given, now without a date: nothing dates the article.
    reader.page_reader.not_now.clear()
    reader.time.advance(timedelta(hours=2, seconds=1))
    reader.web.pages["www.theguardian.com/science/2019/may/04/synthetic-teeth"] = page(
        published=None
    )
    undated = reader.step.attach(reader.session, lead, claim, reader.client, by=Decider.HUMAN)

    assert undated == NotAttached(NO_DATE)
    assert (lead.read_outcome, lead.read_detail) == (ReadOutcome.IDENTITY_UNRESOLVED, detail)
    assert reads_naming_live_claims(reader.session) == [(lead, claim)]
    assert len(articles_of(reader.session, claim)) == 1


# --- dismissing ------------------------------------------------------------------------


def test_a_dismissed_read_keeps_its_outcome_and_leaves_the_list(reader: Reader):
    """Scenario: An overlapping read is dismissed"""
    lead, claim = overlapping(reader)

    dismiss_overlap(
        reader.session, lead.id, reason=" another  product ", by=Decider.ASSISTANT, now=NOW
    )

    assert (lead.read_outcome, lead.claim_id) == (ReadOutcome.IDENTITY_UNRESOLVED, None)
    detail = lead.read_detail or ""
    assert detail.endswith(
        f"; not a report of {claim.slug}, decided by the assistant on 2026-11-20: another product"
    )
    assert detail.startswith("EX-1 antibody for tooth agenesis; ")
    assert reads_naming_live_claims(reader.session) == []
    assert (len(articles_of(reader.session, claim)), asked(reader)) == (1, 1)
    # Settled once: it is no longer such a read, and is not read again.
    with pytest.raises(NotAnOverlap):
        dismiss_overlap(reader.session, lead.id, reason="again", by=Decider.HUMAN, now=NOW)
    assert reader.read().processed == 0


def test_a_dismissal_needs_a_reason_and_a_person_or_an_assistant(reader: Reader):
    lead, claim = overlapping(reader)

    with pytest.raises(NotAnOverlap, match="reason"):
        dismiss_overlap(reader.session, lead.id, reason="  ", by=Decider.HUMAN, now=NOW)
    with pytest.raises(ValueError, match="operator or by an assistant"):
        dismiss_overlap(reader.session, lead.id, reason="no", by=Decider.RULE, now=NOW)

    assert reads_naming_live_claims(reader.session) == [(lead, claim)]


# --- the commands ----------------------------------------------------------------------


@pytest.fixture
def run(reader: Reader, monkeypatch: pytest.MonkeyPatch) -> Callable[..., Result]:
    """`thenwhat audit …` with the read step, its client and its session stood in."""

    @contextmanager
    def test_session() -> Generator[Session]:
        yield reader.session
        reader.session.flush()

    monkeypatch.setattr("thenwhat.cli.session.open_session", test_session)
    monkeypatch.setattr("thenwhat.cli.entry.open_session", test_session)
    monkeypatch.setattr(
        "thenwhat.cli.backfill.registered_steps", lambda settings, **_: [reader.step]
    )
    monkeypatch.setattr(
        "thenwhat.cli.backfill.make_allowances", lambda settings: reader.client.allowances
    )
    monkeypatch.setattr(
        "thenwhat.cli.backfill.make_client", lambda step, settings, shared: reader.client
    )
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://unused/unused")
    monkeypatch.setenv("CONTACT_EMAIL", "ops@thenwhat.test")
    runner = CliRunner()

    def invoke(*arguments: str) -> Result:
        return runner.invoke(app, ["audit", *arguments])

    return invoke


def test_audit_attach_attaches_the_article_and_carries_on_past_a_refused_lead(run, reader: Reader):
    lead, claim = overlapping(reader)
    lead.url_key_version = KEY_VERSION
    reader.session.flush()

    attached = run("attach", str(lead.id), "--as-assistant")

    assert attached.exit_code == 0, attached.output
    said = " ".join(attached.output.split())
    assert f"lead {lead.id} attached to {claim.slug} 2019-05-04" in said
    assert HEADLINE in said and SHARED_TITLE not in said
    assert "Attached 1 article, decided by the assistant" in said
    assert lead.read_outcome is ReadOutcome.ADDED_TO_CLAIM
    assert len(articles_of(reader.session, claim)) == 2

    # Attached once: it is no longer such a read. A lead that does not exist is refused
    # too, each by name, and nothing more is asked of the reader.
    again = run("attach", str(lead.id), "0")

    assert again.exit_code == 1
    refused = " ".join(again.output.split())
    assert f"Lead {lead.id} is not a read left unresolved" in refused
    assert "Lead 0 is not a read left unresolved" in refused
    assert "Attached 0 articles; 2 not attached" in refused
    assert (asked(reader), len(articles_of(reader.session, claim))) == (2, 2)


def test_audit_dismiss_takes_the_read_off_the_list_and_refuses_one_that_is_not_listed(
    run, reader: Reader
):
    lead, claim = overlapping(reader)
    assert f"lead {lead.id} overlaps {claim.slug}" in " ".join(run("list").output.split())

    dismissed = run("dismiss", str(lead.id), "--reason", "another product")

    assert dismissed.exit_code == 0, dismissed.output
    assert f"lead {lead.id} not a report of {claim.slug}" in " ".join(dismissed.output.split())
    assert "by the operator" in (lead.read_detail or "")
    assert f"lead {lead.id}" not in run("list").output

    again = run("dismiss", str(lead.id), "--reason", "another product")

    assert again.exit_code == 1
    assert f"Lead {lead.id} is not a read left unresolved" in " ".join(again.output.split())
