"""Duplicate article exceptions account only for the rows and references the store folds."""

import json
import sqlite3
from copy import deepcopy
from datetime import date
from pathlib import Path

from sqlalchemy.orm import Session

import test_export_from_store
from store_support import both_exports, store_of
from test_export import ARTICLE, NOW, SLUG, add_event, new_claim
from thenwhat.claims.entry import add_article, add_promise
from thenwhat.export.compare import compare
from thenwhat.export.parallel import shared_address_keys

ALIAS = ARTICLE + "?utm_source=newsletter"
export_cli = test_export_from_store.invoke


def add_duplicate(session: Session) -> None:
    new_claim(session)
    add_event(session)
    add_article(
        session,
        SLUG,
        url=ALIAS,
        outlet="Example News",
        title="A different report",
        published_date=date(2018, 3, 11),
    )
    add_promise(session, SLUG, article_url=ALIAS, description="results in 2030")
    add_promise(session, SLUG, article_url=ALIAS, description="human trials by 2025")
    session.flush()


def test_a_named_duplicate_only_explains_its_articles_and_their_references(
    session: Session, tmp_path: Path
):
    add_duplicate(session)
    database, store = both_exports(session, tmp_path, NOW)
    known = shared_address_keys(session)
    assert known == {SLUG: {ALIAS: ARTICLE}}
    assert compare(database, store, known=known).unexplained == []
    retained = store["claims"][0]
    assert [article["url"] for article in retained["articles"]] == [ARTICLE]
    assert {promise["article_url"] for promise in retained["promises"]} == {ARTICLE}

    changed_status = deepcopy(store)
    changed_status["claims"][0]["status"]["code"] = "approved"
    result = compare(database, changed_status, known=known)
    assert len(result.unexplained) == 1
    assert any("claim.status.code" in p for p in result.unexplained[0].places)
    assert compare(store, changed_status, known={SLUG: "duplicate address"}).unexplained

    wrong_promise = deepcopy(store)
    wrong_promise["claims"][0]["promises"][0]["description"] = "something else"
    assert compare(database, wrong_promise, known=known).unexplained

    wrong_article = deepcopy(store)
    wrong_article["claims"][0]["articles"][0]["url"] = ALIAS
    assert compare(database, wrong_article, known=known).unexplained


def test_allow_named_fails_when_the_retained_article_also_changed(
    session: Session, tmp_path: Path, export_cli
):
    add_duplicate(session)
    store_of(session, tmp_path, NOW)[0].close()
    file = tmp_path / "store.db"
    report = tmp_path / "comparison.json"
    arguments = ("export-compare", "--store", str(file), "--allow-named", "--report", str(report))
    assert export_cli(*arguments).exit_code == 0
    with sqlite3.connect(file) as db:
        db.execute("UPDATE source_article SET title = 'Unexpected edit' WHERE url = ?", (ARTICLE,))

    result = export_cli(*arguments)
    assert result.exit_code == 1, result.output
    comparison = json.loads(report.read_text())
    assert comparison["unexplained"] == 1
    [unexplained] = [d for d in comparison["differences"] if d["cause"] is None]
    assert any("articles[0].title" in path for path in unexplained["places"])
