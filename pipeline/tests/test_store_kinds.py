"""The lists that say where a kind of record goes agree with one another: the kinds the
service's door takes, the tier each is pushed to, the kinds the inbox keeps, and the
rows the inbox's clearing deletes. A kind added to one list and not the others is how a
trial's papers could be merged into D1, never reach the bulk file, and then stop the
clearing on a foreign key; these tests are what a new kind has to pass.

The service's lists are read from its source as text: no Node is run."""

import re
import sqlite3
from pathlib import Path

from thenwhat.store.tiers import (
    BOTH,
    BULK,
    BULK_KINDS,
    FOLLOWING_KINDS,
    HOT,
    HOT_KINDS,
    TIER,
)

STORE = Path(__file__).resolve().parents[2] / "store"
# The kinds whose rows go to a table of another name.
TABLE_OF = {
    "usage": "llm_usage",
    "decision": "decision_log",
    "action": "claim_action",
    "unlisted_domain": "unlisted_domain_count",
}
# The inbox's own tables, which its clearing empties and no record of the tracker is in.
INBOX_TABLES = {"inbox", "inbox_folded"}


def _list(name: str) -> list[str]:
    text = (STORE / "ingest" / "src" / "kinds.mjs").read_text()
    found = re.search(rf"export const {name} = \[(.*?)\];", text, re.S)
    assert found, name
    return re.findall(r'"([a-z_]+)"', found.group(1))


def _clearing() -> str:
    """The clearing as written: what it selects and what it deletes."""
    text = (STORE / "ingest" / "src" / "store.mjs").read_text()
    found = re.search(r"const FOLDED = .*?const CLEAR = \[.*?\n\];", text, re.S)
    assert found
    return found.group(0)


def _cleared() -> list[str]:
    """The tables the inbox's clearing deletes from, in the order it does."""
    deletes = _clearing().split("const CLEAR = [")[1]
    return [t for t in re.findall(r"DELETE FROM (\w+)", deletes) if t not in INBOX_TABLES]


def test_every_kind_the_door_takes_has_exactly_one_tier() -> None:
    kinds = _list("KINDS")
    assert len(kinds) == len(set(kinds))
    lists = {"hot": HOT_KINDS, "bulk": BULK_KINDS, "following": FOLLOWING_KINDS}
    for kind in kinds:
        assert [name for name, held in lists.items() if kind in held] in (
            ["hot"],
            ["bulk"],
            ["following"],
        ), f"{kind} must be in exactly one of HOT_KINDS, BULK_KINDS and FOLLOWING_KINDS"
    assert set(kinds) == HOT_KINDS | BULK_KINDS | FOLLOWING_KINDS, (
        "a tier names a kind the door does not take"
    )


def test_a_kind_s_table_is_in_the_tier_its_list_says() -> None:
    for kinds, tier in ((HOT_KINDS, HOT), (BULK_KINDS, BULK), (FOLLOWING_KINDS, BOTH)):
        for kind in kinds:
            assert TIER[TABLE_OF.get(kind, kind)] == tier, kind


def test_the_inbox_keeps_exactly_the_bulk_kinds() -> None:
    assert set(_list("INBOX_KINDS")) == BULK_KINDS


def test_clearing_the_inbox_never_deletes_a_row_from_under_another() -> None:
    """Whatever references a table the clearing deletes from is deleted first, or the
    clearing leaves alone the rows it references (`NOT EXISTS (SELECT 1 FROM <it> ...`).
    Otherwise the clearing fails on a foreign key each time it is tried."""
    db = sqlite3.connect(":memory:")
    db.executescript((STORE / "schema.sql").read_text())
    cleared = _cleared()
    tables = [name for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type = 'table'")]
    for parent in cleared:
        assert TIER[parent] == BULK, f"the clearing deletes from {parent}, which is not bulk"
        for child in tables:
            if child == parent:
                continue
            if any(row[2] == parent for row in db.execute(f"PRAGMA foreign_key_list({child})")):
                if f"NOT EXISTS (SELECT 1 FROM {child} " in _clearing():
                    continue
                assert child in cleared, f"{child} references {parent} and is never cleared"
                assert cleared.index(child) < cleared.index(parent), f"{child} after {parent}"
