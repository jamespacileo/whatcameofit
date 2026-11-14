"""Behavior every registry client shares, tested through a minimal client on a fake transport.

Scenario names are from openspec source-clients.
"""

from datetime import timedelta

import httpx
import pytest
from sqlalchemy.orm import Session

from thenwhat.db.models import HttpCache
from thenwhat.sources.base import (
    MissingContact,
    Pacer,
    Source,
    SourceError,
    SourceUnavailable,
    TermsNotRecorded,
)
from thenwhat.sources.terms import SOURCES


class Demo(Source):
    name = "demo"
    default_rate_per_second = 3.0

    def get(self, path: str, *, force: bool = False):
        return self._get(f"https://demo.test/{path}", force=force)


class Unread(Demo):
    """A source whose terms nobody has read."""

    name = "unread"


@pytest.fixture(autouse=True)
def demo_is_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    """The minimal client stands for a source whose terms are recorded."""
    monkeypatch.setitem(SOURCES, "demo", SOURCES["ror"])


class Server:
    """Answers requests from a queue of responses and remembers what it was asked."""

    def __init__(self, *responses: httpx.Response | Exception) -> None:
        self.responses = list(responses)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        answer = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


def ok(body: dict | None = None) -> httpx.Response:
    return httpx.Response(200, json=body or {"ok": True})


def client(session: Session, fake_time, server: Server, **options) -> Demo:
    options.setdefault("contact_email", "ops@thenwhat.test")
    return Demo(session, transport=httpx.MockTransport(server), time=fake_time, **options)


# --- recorded terms ------------------------------------------------------------


def test_source_with_no_recorded_terms_is_not_asked(session: Session, fake_time):
    """Scenario: Source not yet recorded"""
    server = Server(ok())
    unread = Unread(
        session,
        contact_email="ops@thenwhat.test",
        transport=httpx.MockTransport(server),
        time=fake_time,
    )

    with pytest.raises(TermsNotRecorded, match="'unread' are not recorded"):
        unread.get("thing")

    assert server.requests == []


# --- caching -------------------------------------------------------------------


def test_repeated_request_is_served_from_the_cache(session: Session, fake_time):
    """Scenario: Repeated request"""
    server = Server(ok({"n": 1}))
    demo = client(session, fake_time, server)

    first = demo.get("thing")
    fake_time.advance(timedelta(hours=1))
    second = demo.get("thing")

    assert len(server.requests) == 1
    assert first is not None and second is not None
    assert second.payload == {"n": 1}
    assert second.fetched_at == first.fetched_at


def test_forced_refresh_fetches_again_and_updates_the_fetch_time(session: Session, fake_time):
    """Scenario: Forced refresh"""
    server = Server(ok({"n": 1}), ok({"n": 2}))
    demo = client(session, fake_time, server)
    first = demo.get("thing")
    fake_time.advance(timedelta(hours=1))

    second = demo.get("thing", force=True)

    assert len(server.requests) == 2
    assert first is not None and second is not None
    assert second.payload == {"n": 2}
    assert second.fetched_at == first.fetched_at + timedelta(hours=1)


def test_cache_entry_past_its_lifetime_is_fetched_again(session: Session, fake_time):
    server = Server(ok())
    demo = client(session, fake_time, server, cache_ttl=timedelta(hours=24))
    demo.get("thing")

    fake_time.advance(timedelta(hours=25))
    demo.get("thing")

    assert len(server.requests) == 2


def test_cache_is_shared_between_client_instances(session: Session, fake_time):
    server = Server(ok())
    client(session, fake_time, server).get("thing")

    client(session, fake_time, server).get("thing")

    assert len(server.requests) == 1


# --- rate limiting ---------------------------------------------------------------


def test_burst_of_requests_is_spread_out(session: Session, fake_time):
    """Scenario: Burst of requests"""
    demo = client(session, fake_time, Server(ok()), rate_per_second=3)

    for number in range(10):
        demo.get(f"thing-{number}")

    assert fake_time.elapsed >= 3.0 - 1e-9  # nine gaps of a third of a second


def test_clients_that_share_a_pacer_take_turns(session: Session, fake_time):
    """Scenario: Several clients of one registry at once"""
    shared = Pacer()
    first = client(session, fake_time, Server(ok()), pacer=shared)
    second = client(session, fake_time, Server(ok()), pacer=shared)

    first.get("a")
    second.get("b")
    first.get("c")

    # Together they keep to the registry's rate: three a second here.
    assert fake_time.slept == pytest.approx([1 / 3, 1 / 3])


def test_an_entry_another_session_wrote_meanwhile_is_replaced_not_collided_with(
    session: Session, fake_time
):
    """Scenario: Two lookups fetch the same page at once"""

    def answer_after_someone_else_cached_it(request: httpx.Request) -> httpx.Response:
        session.add(
            HttpCache(
                request_key=f"demo GET {request.url}",
                source_name="demo",
                payload={"n": "theirs"},
                fetched_at=fake_time.now(),
                expires_at=fake_time.now() + timedelta(hours=24),
            )
        )
        session.flush()
        session.expunge_all()
        return ok({"n": "ours"})

    demo = Demo(
        session,
        contact_email="ops@thenwhat.test",
        transport=httpx.MockTransport(answer_after_someone_else_cached_it),
        time=fake_time,
    )

    fetched = demo.get("thing")

    assert fetched is not None and fetched.payload == {"n": "ours"}
    kept = session.get(HttpCache, "demo GET https://demo.test/thing")
    assert kept is not None and kept.payload == {"n": "ours"}


def test_cached_answers_do_not_wait(session: Session, fake_time):
    demo = client(session, fake_time, Server(ok()), rate_per_second=3)
    demo.get("thing")

    for _ in range(10):
        demo.get("thing")

    assert fake_time.slept == []


# --- client identification ---------------------------------------------------------


def test_every_request_names_the_project_and_the_contact_address(session: Session, fake_time):
    server = Server(ok())

    client(session, fake_time, server, contact_email="ops@thenwhat.test").get("thing")

    user_agent = server.requests[0].headers["User-Agent"]
    assert "thenwhat" in user_agent
    assert "ops@thenwhat.test" in user_agent


@pytest.mark.parametrize("contact", [None, "", "   "])
def test_missing_contact_address_sends_nothing(session: Session, fake_time, contact):
    """Scenario: Missing contact address"""
    server = Server(ok())

    with pytest.raises(MissingContact, match="CONTACT_EMAIL"):
        client(session, fake_time, server, contact_email=contact).get("thing")

    assert server.requests == []


# --- not found and failures ----------------------------------------------------------


def test_not_found_is_a_result_not_a_failure(session: Session, fake_time):
    server = Server(httpx.Response(404, text="not found"))

    assert client(session, fake_time, server).get("missing") is None
    assert len(server.requests) == 1


def test_stated_retry_delay_is_honoured(session: Session, fake_time):
    """Scenario: Source asks the client to slow down"""
    server = Server(httpx.Response(429, headers={"Retry-After": "7"}), ok({"n": 1}))

    fetched = client(session, fake_time, server).get("thing")

    assert fetched is not None and fetched.payload == {"n": 1}
    assert max(fake_time.slept) >= 7


def test_transient_failures_are_retried_with_growing_delays(session: Session, fake_time):
    server = Server(httpx.Response(503), httpx.ConnectError("connection refused"), ok({"n": 1}))

    fetched = client(session, fake_time, server).get("thing")

    assert fetched is not None and fetched.payload == {"n": 1}
    delays = [delay for delay in fake_time.slept if delay >= 1]
    assert len(delays) == 2 and delays[1] > delays[0]


def test_source_that_stays_down_fails_after_the_allowed_attempts(session: Session, fake_time):
    """Scenario: Source stays down"""
    server = Server(httpx.Response(503))

    with pytest.raises(SourceUnavailable):
        client(session, fake_time, server, max_attempts=4).get("thing")

    assert len(server.requests) == 4


def test_failed_fetch_is_not_cached(session: Session, fake_time):
    server = Server(httpx.Response(503), httpx.Response(503), ok({"n": 1}))
    demo = client(session, fake_time, server, max_attempts=2)
    with pytest.raises(SourceUnavailable):
        demo.get("thing")

    fetched = demo.get("thing")

    assert fetched is not None and fetched.payload == {"n": 1}


def test_refusal_by_the_source_is_an_error_and_is_not_retried(session: Session, fake_time):
    server = Server(httpx.Response(403, text="forbidden"))

    with pytest.raises(SourceError):
        client(session, fake_time, server).get("thing")

    assert len(server.requests) == 1
