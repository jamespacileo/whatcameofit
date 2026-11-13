"""Keep URL checks and lookup responses outside disposable worktrees."""

import argparse
import csv
import fcntl
import hashlib
import json
import os
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path


def cache_directory():
    override = os.environ.get("CORPUS_CACHE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "WhatCameOfIt" / "extension-test-corpus"


@contextmanager
def edit_cache():
    directory = cache_directory()
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / "cache.json"
    with (directory / "cache.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = (
            json.loads(path.read_text())
            if path.exists()
            else {"version": 1, "checked": {}, "results": {}}
        )
        if state.get("version") != 1:
            raise ValueError(f"Unsupported corpus cache version in {path}")
        before = json.dumps(state, ensure_ascii=False)
        yield state
        if path.exists() and json.dumps(state, ensure_ascii=False) == before:
            return
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=directory, delete=False
            ) as output:
                temporary = Path(output.name)
                json.dump(state, output, ensure_ascii=False, indent=1)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary, path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)


def load_cache(here):
    """Import legacy worktree files once, preserving existing durable answers."""
    work = here / ".work"
    checks_file = work / "checked.json"
    results_file = work / "results.json"
    checks = json.loads(checks_file.read_text()) if checks_file.exists() else {}
    results = json.loads(results_file.read_text()) if results_file.exists() else {}
    with (here / "urls.csv").open(newline="") as source:
        urls = {row["id"]: row["url"] for row in csv.DictReader(source) if row["id"]}
    with edit_cache() as state:
        for url, check in checks.items():
            state["checked"].setdefault(url, check)
        for key, result in results.items():
            row_id, _, suffix = key.partition(":")
            if row_id not in urls:
                continue
            imported = state.setdefault("legacy_results", {}).setdefault(
                str(results_file.resolve()), {}
            )
            fingerprint = hashlib.sha256(json.dumps(result, sort_keys=True).encode()).hexdigest()
            if imported.get(key) == fingerprint:
                continue
            mode = "browser" if suffix == "browser" else "address"
            state["results"].setdefault(urls[row_id], {}).setdefault(mode, result)
            imported[key] = fingerprint
        return state


def store_checks(checks):
    with edit_cache() as state:
        state["checked"].update(checks)
        return state["checked"]


def store_result(url, mode, result):
    with edit_cache() as state:
        state["results"].setdefault(url, {})[mode] = result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    read = commands.add_parser("read")
    read.add_argument("here", type=Path)
    put = commands.add_parser("put-result")
    put.add_argument("url")
    put.add_argument("mode", choices=["address", "browser"])
    args = parser.parse_args()
    if args.command == "read":
        print(json.dumps(load_cache(args.here), ensure_ascii=False))
    else:
        store_result(args.url, args.mode, json.load(sys.stdin))


if __name__ == "__main__":
    main()
