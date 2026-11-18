"""A backfill run in a folder of files: starting a run and its load stage. Scenario names
are from openspec backfill-run-files and link-leads (change file-based-backfill). Every
post here is synthetic, and no test needs a database."""

import csv
import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pyarrow as pa
import pyarrow.parquet as parquet
import pytest
import zstandard
from typer.testing import CliRunner

from thenwhat.backfill.link_readers import HACKER_NEWS, REDDIT
from thenwhat.backfill.run.folder import (
    FolderMissing,
    RunRecord,
    RunRefused,
    mounted_folder,
    open_run,
    start_run,
    write_atomically,
)
from thenwhat.backfill.run.load import (
    LINKS,
    NOT_LISTED,
    QUARANTINE,
    TALLY,
    CountsDisagree,
    FieldsMissing,
    LoadReport,
    OverBudget,
    load,
    read_tally,
    reconcile,
)
from thenwhat.cli import app

WHEN = datetime(2026, 3, 4, 10, 30, tzinfo=UTC)
NOW = datetime(2026, 11, 18, 9, 0, tzinfo=UTC)
LISTED = "https://www.theguardian.com/science/2026/mar/04/synthetic-trial-report"
UNLISTED = "https://github.com/synthetic-owner/synthetic-repository"
AUTHOR = "synthetic_author_name"
POST_ID = "t3syntheticid"
PERMALINK = "/r/science/comments/syntheticid/a_synthetic_post/"
POST_TEXT = "synthetic words a person wrote under a post"


def story(number: int, url: str | None, title: str = "A synthetic headline", **changes) -> dict:
    row = {
        "id": number,
        "type": 1,
        "url": url,
        "title": title,
        "time": WHEN,
        "score": 12,
        "dead": 0,
        "deleted": 0,
    }
    return {**row, **changes}


def hacker_news_file(folder: Path, rows: list[dict], *, without: str | None = None) -> Path:
    path = folder / "2026-03.parquet"
    table = pa.Table.from_pylist(rows)
    if without:
        table = table.drop_columns([without])
    parquet.write_table(table, path)
    return path


def submission(url: str = LISTED, **changes) -> dict:
    row = {
        "url": url,
        "subreddit": "science",
        "created_utc": int(WHEN.timestamp()),
        "score": 4100,
        "title": "A synthetic headline about a trial",
        "is_self": False,
        "removed_by_category": None,
        # What a Reddit line carries and no file of a run may hold.
        "author": AUTHOR,
        "id": POST_ID,
        "permalink": PERMALINK,
        "selftext": POST_TEXT,
    }
    return {**row, **changes}


def reddit_file(folder: Path, lines: list[str]) -> Path:
    path = folder / "science.zst"
    path.write_bytes(zstandard.ZstdCompressor().compress("\n".join(lines).encode()))
    return path


def started(tmp_path: Path, platform: str, path: Path) -> tuple[Path, RunRecord]:
    runs = tmp_path / "runs"
    runs.mkdir(exist_ok=True)
    return start_run(
        runs,
        platform,
        [path],
        device="test-device",
        communities=frozenset({"science"}) if platform == REDDIT else frozenset(),
        now=NOW,
    )


def everything_in(folder: Path) -> str:
    """Every file of a run as one text to search; parquet files read back as rows."""
    found = []
    for path in sorted(folder.iterdir()):
        if path.suffix == ".parquet":
            found.append(repr(pl.read_parquet(path).rows()))
        else:
            found.append(path.read_text("utf-8"))
    return "\n".join(found)


# --- the run folder -------------------------------------------------------------------


def test_a_run_records_its_inputs_and_their_sizes(tmp_path: Path):
    path = hacker_news_file(tmp_path, [story(1, LISTED)])

    folder, record = started(tmp_path, HACKER_NEWS, path)

    assert folder.name == "20261118T090000Z-test-device"
    _, opened = open_run(tmp_path / "runs", folder.name)
    assert opened == record
    [item] = opened.inputs
    assert item.path == str(path.resolve()) and item.size == path.stat().st_size


def test_an_interrupted_write_leaves_no_file_under_its_final_name(tmp_path: Path):
    target = tmp_path / LINKS

    def stopped(partial: Path) -> None:
        partial.write_bytes(b"half a file")
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        write_atomically(target, stopped)

    assert list(tmp_path.iterdir()) == []


def test_a_folder_on_a_volume_that_is_not_mounted_is_refused(tmp_path: Path):
    unmounted = tmp_path / "Volumes" / "external" / "scratch"

    with pytest.raises(FolderMissing, match="BACKFILL_RUNS_DIR .* not mounted"):
        mounted_folder(unmounted, "BACKFILL_RUNS_DIR")
    assert not unmounted.exists()


def test_an_input_file_that_changed_stops_the_stage(tmp_path: Path):
    """Scenario: An input file changed"""
    path = hacker_news_file(tmp_path, [story(1, LISTED)])
    folder, record = started(tmp_path, HACKER_NEWS, path)
    hacker_news_file(tmp_path, [story(1, LISTED), story(2, UNLISTED)])

    with pytest.raises(RunRefused, match=path.name):
        load(folder, record, error_budget=0.01)


# --- the load -------------------------------------------------------------------------


def test_only_the_post_on_a_listed_outlet_is_written_as_a_share(tmp_path: Path):
    """Scenario: A file of stories"""
    path = hacker_news_file(tmp_path, [story(1, LISTED), story(2, UNLISTED)])
    folder, record = started(tmp_path, HACKER_NEWS, path)

    report = load(folder, record, error_budget=0.01)

    [share] = pl.read_parquet(folder / LINKS).to_dicts()
    assert share["address"] == LISTED
    assert share["outlet"] == "theguardian.com" and share["kind"] == "general_news"
    assert share["platform"] == HACKER_NEWS and share["item_number"] == 1
    assert (report.read, report.shares, report.addresses) == (2, 1, 1)
    assert report.skipped == {NOT_LISTED: 1}


def test_the_tally_holds_domains_and_counts_and_no_other_file_holds_an_unlisted_link(
    tmp_path: Path,
):
    """Scenario: A code repository's domain"""
    rows = [story(1, LISTED)] + [
        story(n, f"{UNLISTED}/{n}", title="Semaglutide in a synthetic repository")
        if n == 2
        else story(n, f"{UNLISTED}/{n}")
        for n in range(2, 6)
    ]
    path = hacker_news_file(tmp_path, rows)
    folder, record = started(tmp_path, HACKER_NEWS, path)

    load(folder, record, error_budget=0.01)

    assert read_tally(folder / TALLY) == [
        {"domain": "github.com", "platform": HACKER_NEWS, "link_posts": "4", "topic_posts": "1"}
    ]
    assert "synthetic-repository" not in everything_in(folder)
    assert "Semaglutide" not in everything_in(folder)


def test_counts_that_do_not_add_up_fail_the_stage():
    """Scenario: Counts that do not add up"""
    report = LoadReport(read=10, shares=6, quarantined=1)
    report.skipped[NOT_LISTED] = 2

    with pytest.raises(CountsDisagree, match="10 posts read, 6 shares written, 2 left out"):
        reconcile(report)


def test_a_malformed_line_is_quarantined_by_file_line_and_kind_only(tmp_path: Path):
    """Scenario: One malformed line"""
    broken = '{"url": "' + LISTED + '", "author": "' + AUTHOR + '", '
    path = reddit_file(tmp_path, [json.dumps(submission()), broken, json.dumps(submission())])
    folder, record = started(tmp_path, REDDIT, path)

    report = load(folder, record, error_budget=0.5)

    with (folder / QUARANTINE).open(newline="") as stream:
        assert list(csv.reader(stream)) == [
            ["file", "position", "error"],
            ["science.zst", "2", "JSONDecodeError"],
        ]
    assert report.quarantined == 1 and report.shares == 1
    assert AUTHOR not in (folder / QUARANTINE).read_text()


def test_a_file_over_the_error_budget_stops_the_load(tmp_path: Path):
    """Scenario: A file in an unexpected shape"""
    path = reddit_file(tmp_path, [json.dumps(submission()), "not json", "[1, 2]"])
    folder, record = started(tmp_path, REDDIT, path)

    with pytest.raises(OverBudget, match="2 of 3 rows of science.zst"):
        load(folder, record, error_budget=0.1)
    assert not (folder / LINKS).exists()


def test_the_load_refuses_while_the_error_budget_is_not_set(tmp_path: Path):
    path = hacker_news_file(tmp_path, [story(1, LISTED)])
    folder, record = started(tmp_path, HACKER_NEWS, path)

    with pytest.raises(RunRefused, match="LOAD_ERROR_BUDGET"):
        load(folder, record, error_budget=None)


def test_a_file_without_a_url_column_is_refused_before_anything_is_written(tmp_path: Path):
    """Scenario: A column is missing"""
    path = hacker_news_file(tmp_path, [story(1, LISTED)], without="url")
    folder, record = started(tmp_path, HACKER_NEWS, path)

    with pytest.raises(FieldsMissing, match="no url"):
        load(folder, record, error_budget=0.01)
    assert sorted(path.name for path in folder.iterdir()) == ["run.json"]


def test_nothing_about_the_person_who_shared_reaches_any_file_of_the_run(tmp_path: Path):
    """Scenario: A Reddit submission"""
    lines = [json.dumps(submission()), json.dumps(submission(url=UNLISTED)), "{broken"]
    path = reddit_file(tmp_path, lines)
    folder, record = started(tmp_path, REDDIT, path)

    load(folder, record, error_budget=0.5)

    found = everything_in(folder)
    assert "synthetic-trial-report" in found  # the article's address is what is kept
    for private in (AUTHOR, POST_ID, PERMALINK, "syntheticid", POST_TEXT):
        assert private not in found
    [share] = pl.read_parquet(folder / LINKS).to_dicts()
    assert share["item_number"] is None


# --- the commands ---------------------------------------------------------------------


def test_a_dry_run_prints_the_report_and_writes_only_the_tally(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Scenario: A dry run before a load"""
    runs = tmp_path / "runs"
    runs.mkdir()
    monkeypatch.setenv("BACKFILL_RUNS_DIR", str(runs))
    monkeypatch.setenv("LOAD_ERROR_BUDGET", "0.01")
    monkeypatch.setenv("WORK_DEVICE_NAME", "Mac mini")
    path = hacker_news_file(tmp_path, [story(1, LISTED), story(2, UNLISTED)])
    runner = CliRunner()

    started_run = runner.invoke(app, ["backfill", "runs", "start", HACKER_NEWS, str(path)])
    assert started_run.exit_code == 0, started_run.output
    [folder] = runs.iterdir()
    assert folder.name.endswith("-mac-mini")
    result = runner.invoke(app, ["backfill", "runs", "load", folder.name, "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "Read 2 posts: 1 shares on listed outlets" in result.output
    assert f"left out, {NOT_LISTED}: 1" in result.output
    assert sorted(path.name for path in folder.iterdir()) == ["run.json", TALLY]


def test_starting_a_run_refuses_while_its_folder_is_not_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.delenv("BACKFILL_RUNS_DIR", raising=False)
    path = hacker_news_file(tmp_path, [story(1, LISTED)])

    result = CliRunner().invoke(app, ["backfill", "runs", "start", HACKER_NEWS, str(path)])

    assert result.exit_code == 1
    assert "BACKFILL_RUNS_DIR is not set" in result.output
