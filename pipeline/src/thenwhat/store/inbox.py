"""The inbox of the bulk tier: the bulk records a run handed to D1, usually a reader's
lookup, which the daily job folds into the bulk file and then has the service clear
(`design.md` decision 20, task 4.9; the routes are `store/ingest/README.md`, "The inbox
of the bulk tier").

Folding and clearing are two steps on purpose: the service clears only after the bulk file
holds the records and the day's delta that carries them is kept in R2, so nothing is lost
between the two.
"""

from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from itertools import groupby
from pathlib import Path
from typing import Any

import httpx

from thenwhat.store.build import BuildFailed, merge_into
from thenwhat.store.form import Record

PAGE = 2_000


class InboxFailed(Exception):
    """The service did not give or clear the inbox."""


@dataclass
class Folded:
    records: list[Record] = field(default_factory=list)
    # The folded runs by their local names, for the delta.
    named: list[tuple[str, list[Record]]] = field(default_factory=list)
    # How many of them this fold merged; the others the file already held.
    runs: int = 0
    # The last seq folded: what `clear` is then given.
    through: int = 0


def read(client: httpx.Client, after: int = 0) -> Iterator[dict[str, Any]]:
    """Every inbox record after `after`, oldest first, page by page."""
    while True:
        answer = client.get("/inbox", params={"after": after, "limit": PAGE})
        if answer.status_code != 200:
            raise InboxFailed(
                f"The service refused the inbox: {answer.status_code} {answer.text[:300]}"
            )
        page = answer.json()
        yield from page["records"]
        after = int(page["through"])
        if not page.get("more"):
            return


def fold(
    client: httpx.Client, bulk: Path, *, store_sql: Path, now: datetime, after: int = 0
) -> Folded:
    """Merge the inbox into the bulk file, one local run for each run that handed the
    records over, named by that run's id whole, in the order the service gives them: a
    share's lead, if a lookup brought it, is then in the file before the share. A run the
    file already holds as merged, by an earlier fold that stopped, is not merged again; a
    run that fails stops the fold, and a fold again merges it or fails again."""
    folded = Folded(through=after)
    for run, entries in groupby(read(client, after), key=lambda entry: entry["run"]):
        given = list(entries)
        records = [Record(entry["kind"], entry["key"], entry["body"]) for entry in given]
        name = f"inbox-{run}"
        try:
            _, merged = merge_into(bulk, [(name, records)], store_sql=store_sql, now=now)
        except BuildFailed as fault:
            raise InboxFailed(
                f"Run {run}'s records did not merge into the bulk file: {fault}"
            ) from fault
        folded.runs += bool(merged)
        folded.named.append((name, records))
        folded.records.extend(records)
        folded.through = int(given[-1]["seq"])
    return folded


def clear(client: httpx.Client, through: int) -> dict[str, Any]:
    """Have the service remove the inbox up to `through` and what those runs added to D1."""
    answer = client.post("/inbox/clear", json={"through": through})
    if answer.status_code != 200:
        raise InboxFailed(
            f"The service did not clear the inbox: {answer.status_code} {answer.text[:300]}"
        )
    return answer.json()
