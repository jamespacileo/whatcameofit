"""Migration 0037 gives every link lead read before reasons were codes the code its stored
words stand for, and refuses words it has no code for. Scenario names are from openspec
lead-reading (change one-work-runner), "Every lead's reason is a code"."""

from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, text

SITE = "the page could not be retrieved (the site answered {})"
# What each stored lead held, and what its entry holds after the migration: the outcome,
# the code, the attempts, and whether the lead is still said to have been read.
LEADS = {
    "refused": (
        "cannot_be_read",
        SITE.format(403),
        ("needs_fix", "site_refused", 0, True),
    ),
    "gone": ("cannot_be_read", SITE.format(404), ("nothing_found", "page_gone", 1, True)),
    "busy": ("cannot_be_read", SITE.format(503), ("later", "site_busy", 0, False)),
    "unknown-status": ("cannot_be_read", SITE.format(594), ("later", "site_busy", 0, False)),
    "outlet-refuses": (
        "cannot_be_read",
        "not asked: its outlet answered 401 to the page reader for 50 pages and served none",
        ("needs_fix", "outlet_refuses", 0, True),
    ),
    "no-date": (
        "cannot_be_read",
        "the page gives no publication date",
        ("needs_fix", "no_date", 0, True),
    ),
    "no-headline": (
        "cannot_be_read",
        "the page gives no headline",
        ("needs_fix", "no_headline", 0, True),
    ),
    "thin": ("cannot_be_read", "too little article text", ("needs_fix", "thin_page", 0, True)),
    "no-name": (
        "cannot_be_read",
        "its outlet has no display name",
        ("needs_fix", "no_outlet_name", 0, True),
    ),
    "not-allowed": (
        "cannot_be_read",
        "the page reader does not allow the address: robots.txt",
        ("nothing_found", "not_allowed", 1, True),
    ),
    "class": (
        "not_one_treatment",
        "GLP-1 drugs for obesity; a class of treatments, not one",
        ("nothing_found", "not_one_treatment", 1, True),
    ),
    "business": (
        "business_news",
        "a drug for a condition; on a topic",
        ("nothing_found", "business_news", 1, True),
    ),
    "overlap": (
        "identity_unresolved",
        "a drug for a condition; names overlap a-claim, but not established",
        ("nothing_found", "identity_unresolved", 1, True),
    ),
    "enough": (
        "enough_articles",
        "the claim it names has enough articles: a-claim",
        ("nothing_found", "enough_articles", 1, True),
    ),
    "vertical": (
        "needs_vertical",
        "a drug for a condition; the nearest vertical was x at 0.50",
        ("needs_fix", "needs_vertical", 0, True),
    ),
}

LEAD = text(
    "INSERT INTO link_lead (url, url_key, url_key_version, outlet, outlet_kind, title,"
    " first_shared_at, screen_outcome, read_outcome, read_detail)"
    " VALUES (:url, :key, 1, 'news.example.org', 'general_news', 'a synthetic title', now(),"
    " :screen, :outcome, :detail) RETURNING id"
)
ENTRY = text(
    "INSERT INTO work_entry (record_kind, record_id, step, step_version, outcome, attempts,"
    " requests_used, fingerprint, last_attempt_at)"
    " VALUES (:kind, :id, :step, 1, :outcome, 1, 1, 'earlier', now())"
)


def add_lead(connection, name: str, outcome: str | None, detail: str | None, screen: str) -> int:
    lead_id = connection.execute(
        LEAD,
        {
            "url": f"https://news.example.org/{name}",
            "key": f"news.example.org/{name}",
            "screen": screen,
            "outcome": outcome,
            "detail": detail,
        },
    ).scalar_one()
    connection.execute(
        ENTRY, {"kind": "link_lead", "id": lead_id, "step": "link_read", "outcome": "nothing_found"}
    )
    return lead_id


@pytest.fixture
def at_0036(engine: Engine, alembic_config: Config) -> Iterator[dict[str, int]]:
    """Leads read before the codes: each with the words its detail held, and an entry
    that says nothing found and gives no reason."""
    command.downgrade(alembic_config, "0036")
    ids: dict[str, int] = {}
    with engine.begin() as connection:
        for name, (outcome, detail, _) in LEADS.items():
            ids[name] = add_lead(connection, name, outcome, detail, "in_scope")
        ids["tracked"] = add_lead(connection, "tracked", None, None, "already_tracked")
        # A trial the news search found no story for: an entry of another step.
        connection.execute(
            ENTRY,
            {"kind": "registry_trial", "id": 1, "step": "news_search", "outcome": "nothing_found"},
        )
    try:
        yield ids
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM work_entry"))
            connection.execute(text("DELETE FROM link_lead"))
        command.upgrade(alembic_config, "head")


def entries(engine: Engine) -> dict[int, tuple]:
    with engine.connect() as connection:
        rows = connection.execute(
            text(
                "SELECT e.record_id, e.outcome, e.reason, e.attempts, e.reason_values,"
                " e.not_before IS NOT NULL, l.read_outcome, l.read_detail"
                " FROM work_entry e JOIN link_lead l ON l.id = e.record_id"
                " WHERE e.step = 'link_read'"
            )
        )
        return {row[0]: tuple(row[1:]) for row in rows}


def test_every_lead_read_before_the_codes_is_given_its_code(
    engine: Engine, alembic_config: Config, at_0036: dict[str, int]
):
    """Scenario: A lead from an earlier run"""
    command.upgrade(alembic_config, "0037")

    after = entries(engine)
    for name, (outcome, detail, (entry_outcome, code, attempts, still_said)) in LEADS.items():
        got_outcome, got_code, got_attempts, values, has_time, read_outcome, read_detail = after[
            at_0036[name]
        ]
        assert (got_outcome, got_code, got_attempts) == (entry_outcome, code, attempts), name
        assert values["outlet"] == "news.example.org", name
        assert has_time == (entry_outcome == "later"), name
        # A lead put off is no longer said to be unreadable; every other keeps its words.
        assert (read_outcome, read_detail) == ((outcome, detail) if still_said else (None, None))
    assert after[at_0036["refused"]][3]["status"] == 403
    assert after[at_0036["busy"]][3]["status"] == 503
    assert after[at_0036["outlet-refuses"]][3]["pages"] == 50
    assert after[at_0036["not-allowed"]][3]["why"] == "robots.txt"
    assert after[at_0036["tracked"]][:2] == ("nothing_found", "already_tracked")
    with engine.connect() as connection:
        searched = connection.execute(
            text("SELECT reason FROM work_entry WHERE step = 'news_search'")
        ).scalar_one()
    assert searched == "no_stories"


def test_manual_attachment_overrides_the_earlier_unsuccessful_read(
    engine: Engine, alembic_config: Config, at_0036: dict[str, int]
):
    lead_id = at_0036["overlap"]
    with engine.begin() as connection:
        claim = connection.execute(
            text(
                "INSERT INTO claim (slug, headline, summary, vertical, indication)"
                " VALUES ('attach-upgrade', 'h', '', 'other', 'a condition') RETURNING id"
            )
        ).scalar_one()
        article = connection.execute(
            text(
                "INSERT INTO source_article (claim_id, url, outlet, title, published_date)"
                " VALUES (:claim, 'https://news.example.org/overlap', 'outlet', 'h', current_date)"
                " RETURNING id"
            ),
            {"claim": claim},
        ).scalar_one()
        connection.execute(
            text(
                "UPDATE link_lead SET read_outcome = 'added_to_claim', claim_id = :claim,"
                " source_article_id = :article, read_detail = 'attached by editor' WHERE id = :lead"
            ),
            {"claim": claim, "article": article, "lead": lead_id},
        )
    try:
        command.upgrade(alembic_config, "0037")
        assert entries(engine)[lead_id] == (
            "done",
            None,
            1,
            None,
            False,
            "added_to_claim",
            "attached by editor",
        )
        with engine.connect() as connection:
            assert connection.execute(
                text("SELECT claim_id, source_article_id FROM link_lead WHERE id = :lead"),
                {"lead": lead_id},
            ).one() == (claim, article)
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM link_lead WHERE id = :lead"), {"lead": lead_id})
            connection.execute(text("DELETE FROM source_article WHERE id = :id"), {"id": article})
            connection.execute(text("DELETE FROM claim WHERE id = :id"), {"id": claim})


def test_words_with_no_code_stop_the_migration_and_change_nothing(
    engine: Engine, alembic_config: Config, at_0036: dict[str, int]
):
    with engine.begin() as connection:
        add_lead(connection, "odd", "cannot_be_read", "words no rule knows", "in_scope")

    with pytest.raises(RuntimeError, match=r"1 x 'cannot_be_read: words no rule knows'"):
        command.upgrade(alembic_config, "0037")

    assert {entry[:2] for entry in entries(engine).values()} == {("nothing_found", None)}


def test_going_back_says_again_what_each_lead_was_said_to_be(
    engine: Engine, alembic_config: Config, at_0036: dict[str, int]
):
    command.upgrade(alembic_config, "0037")
    command.downgrade(alembic_config, "0036")

    after = entries(engine)
    for name, (outcome, detail, _) in LEADS.items():
        got = after[at_0036[name]]
        assert (got[0], got[1], got[2], got[5], got[6]) == (
            "nothing_found",
            None,
            1,
            outcome,
            detail,
        ), name
