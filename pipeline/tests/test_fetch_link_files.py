"""scripts/fetch_link_files.py: merging into month files and the fetch windows.

Synthetic month files and a stand-in for the ClickHouse query: no network.
"""

import importlib.util
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "fetch_link_files.py"


def at(text: str) -> datetime:
    return datetime.fromisoformat(text).replace(tzinfo=UTC)


def story(item: int, posted: str, score: int = 1) -> dict:
    return {
        "id": item,
        "type": 1,
        "url": f"https://example.org/{item}",
        "title": f"Story {item}",
        "time": at(posted),
        "score": score,
        "dead": 0,
        "deleted": 0,
    }


@dataclass
class Script:
    """The loaded script, the stories its stand-in query holds, and each query's bounds."""

    module: ModuleType
    held: list[dict] = field(default_factory=list)
    asked: list[tuple[str, str | None]] = field(default_factory=list)


@pytest.fixture
def fetch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Script:
    """The script with its folder in tmp_path and its query answered from `fetch.held`,
    each call's bounds noted in `fetch.asked`."""
    spec = importlib.util.spec_from_file_location("fetch_link_files", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "ROOT", tmp_path)
    script = Script(module)

    def answer(_client, _label, start, end):
        script.asked.append((start, end))
        return [
            row
            for row in script.held
            if row["time"] >= at(start) and (end is None or row["time"] < at(end))
        ]

    monkeypatch.setattr(module, "clickhouse_stories", answer)
    monkeypatch.setattr(module, "archive_months", lambda _client: {})
    (tmp_path / "hackernews").mkdir()
    return script


def month_file(fetch: Script, month: str) -> dict:
    return pq.read_table(fetch.module.ROOT / "hackernews" / f"{month}.parquet").to_pydict()


def write_month(fetch: Script, month: str, rows: list[dict]) -> None:
    table = pa.Table.from_pylist(rows, schema=fetch.module.HACKER_NEWS_SCHEMA)
    pq.write_table(table, fetch.module.ROOT / "hackernews" / f"{month}.parquet")


def last_fetch(fetch: Script) -> str | None:
    record = fetch.module.ROOT / "hackernews" / "last-fetch.json"
    return json.loads(record.read_text())["through"] if record.exists() else None


def test_merge_keeps_held_rows_and_replaces_a_story_fetched_again(fetch: Script) -> None:
    target = fetch.module.ROOT / "hackernews" / "2026-10.parquet"
    # A file from the archive: every column, an author's among them.
    archive = pa.Table.from_pylist(
        [story(1, "2026-10-01"), story(2, "2026-10-30", 5)]
    ).append_column("by", pa.array(["someone", "someone else"]))
    pq.write_table(archive, target)

    added = fetch.module.merge_into(target, [story(2, "2026-10-30", 99), story(3, "2026-10-31")])

    held = month_file(fetch, "2026-10")
    assert added == 1
    assert held["id"] == [1, 2, 3]
    assert held["score"] == [1, 99, 1]
    assert "by" not in held


def test_since_days_reaching_into_last_month_writes_both_files(fetch: Script) -> None:
    write_month(fetch, "2026-10", [story(1, "2026-10-02")])
    fetch.held = [story(2, "2026-10-30"), story(3, "2026-11-01"), story(4, "2026-10-29")]

    fetch.module.main(["hackernews", "--since-days", "3"], now=at("2026-11-02 04:30"))

    assert fetch.asked == [("2026-10-30 00:00:00", None)]
    assert month_file(fetch, "2026-10")["id"] == [1, 2]
    assert month_file(fetch, "2026-11")["id"] == [3]
    assert last_fetch(fetch) == "2026-11-02T04:30:00+00:00"


def test_since_last_fetch_goes_on_from_the_record(fetch: Script) -> None:
    # Five nights missed: the window starts a day before the last fetch, not three days back.
    (fetch.module.ROOT / "hackernews" / "last-fetch.json").write_text(
        json.dumps({"through": "2026-11-10T04:31:00+00:00"})
    )
    fetch.held = [story(1, "2026-11-08"), story(2, "2026-11-09 12:00"), story(3, "2026-11-12")]

    fetch.module.main(["hackernews", "--since-last-fetch", "3"], now=at("2026-11-17 04:30"))

    assert fetch.asked == [("2026-11-09 00:00:00", None)]
    assert month_file(fetch, "2026-11")["id"] == [2, 3]
    assert last_fetch(fetch) == "2026-11-17T04:30:00+00:00"


def test_since_last_fetch_with_no_record_takes_the_given_days(fetch: Script) -> None:
    fetch.module.main(["hackernews", "--since-last-fetch", "3"], now=at("2026-11-17 04:30"))

    assert fetch.asked == [("2026-11-14 00:00:00", None)]


def test_a_long_gap_is_caught_up_oldest_first(fetch: Script, capsys) -> None:
    (fetch.module.ROOT / "hackernews" / "last-fetch.json").write_text(
        json.dumps({"through": "2026-10-01T04:30:00+00:00"})
    )
    now = at("2026-11-17 04:30")

    fetch.module.main(["hackernews", "--since-last-fetch", "3"], now=now)
    fetch.module.main(["hackernews", "--since-last-fetch", "3"], now=now)
    fetch.module.main(["hackernews", "--since-last-fetch", "3"], now=now)

    assert fetch.asked == [
        ("2026-09-30 00:00:00", "2026-10-20 00:00:00"),
        ("2026-10-19 00:00:00", "2026-11-08 00:00:00"),
        ("2026-11-07 00:00:00", None),
    ]
    assert last_fetch(fetch) == "2026-11-17T04:30:00+00:00"
    assert "still behind, the next run goes on from 2026-10-20" in capsys.readouterr().out


def test_a_window_after_a_gap_does_not_move_the_record(fetch: Script) -> None:
    (fetch.module.ROOT / "hackernews" / "last-fetch.json").write_text(
        json.dumps({"through": "2026-11-01T04:30:00+00:00"})
    )

    fetch.module.main(["hackernews", "--since-days", "3"], now=at("2026-11-17 04:30"))

    assert last_fetch(fetch) == "2026-11-01T04:30:00+00:00"


def test_months_are_pending_before_the_fetch_cursor_moves(fetch: Script, tmp_path, monkeypatch):
    pending = tmp_path / "pending-link-loads"
    pending.mkdir()
    monkeypatch.setenv("THENWHAT_PENDING_LINK_LOADS", str(pending))

    def interrupted(folder, through):
        assert sorted(marker.name for marker in pending.iterdir()) == ["2026-10", "2026-11"]
        raise InterruptedError

    monkeypatch.setattr(fetch.module, "write_last_fetch", interrupted)
    with pytest.raises(InterruptedError):
        fetch.module.main(["hackernews", "--since-last-fetch", "3"], now=at("2026-11-02 04:30"))
    assert last_fetch(fetch) is None


def test_month_form_with_merge_fills_a_past_month(fetch: Script) -> None:
    write_month(fetch, "2026-10", [story(1, "2026-10-02")])
    fetch.held = [story(1, "2026-10-02", 7), story(2, "2026-10-20")]

    fetch.module.main(["hackernews", "2026-10", "2026-10"])
    assert fetch.asked == []

    fetch.module.main(["hackernews", "2026-10", "2026-10", "--merge"])
    assert fetch.asked == [("2026-10-01 00:00:00", "2026-11-01 00:00:00")]
    assert month_file(fetch, "2026-10")["id"] == [1, 2]
    assert month_file(fetch, "2026-10")["score"] == [7, 1]


def test_a_window_outside_one_to_28_days_is_refused(fetch: Script) -> None:
    with pytest.raises(SystemExit, match="1 to 28"):
        fetch.module.main(["hackernews", "--since-last-fetch", "40"])
