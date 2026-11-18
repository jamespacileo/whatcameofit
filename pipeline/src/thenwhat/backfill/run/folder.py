"""The run folder: where it lives, what `run.json` records, and writing a file so that
it is whole or absent. Behavior: openspec backfill-run-files.

A run is `<BACKFILL_RUNS_DIR>/<run id>/`. Its identifier is the time it was started and
the device's name. Deleting the folder is the cleanup.
"""

import json
import os
import re
import socket
import subprocess
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from thenwhat.backfill.address import KEY_VERSION
from thenwhat.backfill.link_readers import HACKER_NEWS, REDDIT
from thenwhat.backfill.outlet_kinds import OUTLET_LIST_VERSION
from thenwhat.work.errors import BackfillError

RECORD = "run.json"
REPORT = "report.json"
# The platforms a run can read. GDELT's listings go through `load-links` until their
# own change moves them.
PLATFORMS = (HACKER_NEWS, REDDIT)
# The version of each stage's own rules, recorded so a run says what made its files.
# Triage and read add theirs when they become stages of a run.
STAGE_VERSIONS = {"load": 1}
REPOSITORY = Path(__file__).resolve().parents[5]


class FolderMissing(BackfillError):
    """A folder a run needs is not set, or not there."""


class RunRefused(BackfillError):
    """A run cannot be started, or a stage cannot run in it."""


def mounted_folder(value: Path | None, setting: str) -> Path:
    """The folder a setting names, which must already exist. It is never created: when
    it is on a volume that is not mounted, making it would put the files on another
    disk without a word."""
    if value is None:
        raise FolderMissing(
            f"{setting} is not set. Name the folder for it in .env; nothing in the "
            "repository stands in for it."
        )
    folder = value.expanduser()
    if not folder.is_dir():
        raise FolderMissing(
            f"{setting} is {folder}, which is not there. If it is on an external volume, "
            "the volume is not mounted. Nothing was written."
        )
    return folder


def device_name(configured: str | None) -> str:
    """The device's name as a run records it: WORK_DEVICE_NAME, or the host's name."""
    name = configured or socket.gethostname().split(".", 1)[0]
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-") or "device"


def current_commit() -> str | None:
    """The code's commit, or None outside a git checkout."""
    try:
        answer = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY,
            capture_output=True,
            text=True,
            check=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return answer.stdout.strip() or None


@dataclass(frozen=True, slots=True)
class InputFile:
    path: str
    size: int


@dataclass(slots=True)
class RunRecord:
    """What `run.json` holds."""

    run_id: str
    platform: str
    device: str
    started_at: str
    commit: str | None
    inputs: list[InputFile]
    communities: list[str] = field(default_factory=list)
    address_key_version: int = KEY_VERSION
    outlet_list_version: int = OUTLET_LIST_VERSION
    stage_versions: dict[str, int] = field(default_factory=lambda: dict(STAGE_VERSIONS))
    # The reference file the run leaves out what the store knows by. None until the
    # reference file exists (change file-based-backfill, section 3).
    reference_file: str | None = None

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "RunRecord":
        inputs = [InputFile(**item) for item in data.pop("inputs")]
        return cls(inputs=inputs, **data)


def write_atomically(path: Path, write: Callable[[Path], object]) -> None:
    """Have `write` write to a temporary name beside `path`, then rename it into place.
    A write that fails or is stopped leaves nothing under the final name."""
    partial = path.with_name(f".{path.name}.partial")
    try:
        write(partial)
        os.replace(partial, path)
    finally:
        partial.unlink(missing_ok=True)


def write_json(path: Path, data: Any) -> None:
    write_atomically(
        path, lambda partial: partial.write_text(json.dumps(data, indent=2) + "\n", "utf-8")
    )


def start_run(
    runs_dir: Path,
    platform: str,
    files: Sequence[Path],
    *,
    device: str,
    communities: frozenset[str],
    now: datetime,
) -> tuple[Path, RunRecord]:
    """Make a run's folder and its record. Refused, with nothing made, when the platform
    has no reader, no file is named, a file is not there, or a Reddit run has no
    community chosen."""
    if platform not in PLATFORMS:
        raise RunRefused(
            f"A run cannot read the platform '{platform}'. Platforms: {', '.join(PLATFORMS)}."
        )
    if not files:
        raise RunRefused("Name at least one bulk file for the run.")
    missing = [str(path) for path in files if not path.is_file()]
    if missing:
        raise RunRefused(f"Not a file: {', '.join(missing)}.")
    if platform == REDDIT and not communities:
        raise RunRefused(
            "No Reddit community is chosen. Name the communities to load in "
            "LINK_LEAD_SUBREDDITS, separated by commas."
        )
    run_id = f"{now.astimezone(UTC):%Y%m%dT%H%M%SZ}-{device}"
    folder = runs_dir / run_id
    folder.mkdir()
    record = RunRecord(
        run_id=run_id,
        platform=platform,
        device=device,
        started_at=now.astimezone(UTC).isoformat(),
        commit=current_commit(),
        inputs=[InputFile(str(path.resolve()), path.stat().st_size) for path in files],
        communities=sorted(communities),
    )
    write_json(folder / RECORD, asdict(record))
    return folder, record


def open_run(runs_dir: Path, run: str) -> tuple[Path, RunRecord]:
    """A run's folder and record, by its identifier."""
    folder = runs_dir / run
    record = folder / RECORD
    if not record.is_file():
        raise RunRefused(f"No run '{run}' in {runs_dir}. Start one with `backfill runs start`.")
    return folder, RunRecord.from_json(json.loads(record.read_text("utf-8")))


def check_inputs(record: RunRecord) -> None:
    """Refuse when an input file is gone or its size is not the one the run recorded."""
    for item in record.inputs:
        path = Path(item.path)
        if not path.is_file():
            raise RunRefused(f"The run's input file {path} is not there.")
        size = path.stat().st_size
        if size != item.size:
            raise RunRefused(
                f"The run's input file {path} is {size:,} bytes; the run recorded "
                f"{item.size:,}. Start a new run over the file as it is now."
            )


def stage_reports(folder: Path) -> dict[str, Any]:
    path = folder / REPORT
    return json.loads(path.read_text("utf-8")) if path.is_file() else {}


def record_stage(folder: Path, stage: str, report: dict[str, Any]) -> None:
    """Add a completed stage's report to `report.json`."""
    write_json(folder / REPORT, {**stage_reports(folder), stage: report})
