"""Run with uv run --with openpyxl python -I extension/test-corpus/test_cache.py."""

import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from corpus_cache import edit_cache, load_cache, store_checks, store_result  # noqa: E402


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.here = self.root / "worktree"
        self.here.mkdir()
        self.work = self.here / ".work"
        self.work.mkdir()
        self.cache = self.root / "persistent"
        self.environment = patch.dict(os.environ, {"CORPUS_CACHE_DIR": str(self.cache)})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.url = "https://example.com/research"
        self.response = {
            "mode": "address",
            "http": 200,
            "ms": 10,
            "body": {
                "about_a_treatment": True,
                "treatment": "example",
                "condition": "example",
                "candidates": [],
            },
        }
        self.write_rows(self.url)

    def write_rows(self, url):
        with (self.here / "urls.csv").open("w", newline="") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=[
                    "id",
                    "group",
                    "page_type",
                    "url",
                    "outlet",
                    "intervention_condition",
                    "expected_answer",
                    "source_of_row",
                    "notes",
                ],
            )
            writer.writeheader()
            writer.writerow(
                {
                    "id": "A001",
                    "url": url,
                    "group": "Article",
                    "expected_answer": "claim found -> registry search",
                }
            )

    def seed_legacy(self):
        (self.work / "results.json").write_text(
            json.dumps({"A001": self.response, "A001:browser": self.response})
        )
        (self.work / "checked.json").write_text(json.dumps({self.url: {"http_status": 200}}))

    def test_migration_survives_cleanup_and_id_reuse(self):
        self.seed_legacy()
        saved = load_cache(self.here)
        self.assertEqual(
            saved["results"][self.url], {"address": self.response, "browser": self.response}
        )
        shutil.rmtree(self.here)
        self.here = self.root / "replacement-worktree"
        self.here.mkdir()
        self.write_rows("https://example.com/different")
        restored = load_cache(self.here)
        self.assertEqual(restored, saved)
        self.assertNotIn("https://example.com/different", restored["results"])

    def test_stale_legacy_files_do_not_replace_new_results(self):
        self.seed_legacy()
        load_cache(self.here)
        newer = {"body": {"about_a_treatment": False}}
        store_result(self.url, "address", newer)
        store_checks({self.url: {"http_status": 403}})
        restored = load_cache(self.here)
        self.assertEqual(restored["results"][self.url]["address"], newer)
        self.assertEqual(restored["results"][self.url]["browser"], self.response)
        self.assertEqual(restored["checked"][self.url]["http_status"], 403)

    def test_concurrent_process_updates_are_merged(self):
        def write(index):
            subprocess.run(
                [
                    sys.executable,
                    "-I",
                    str(HERE / "corpus_cache.py"),
                    "put-result",
                    f"https://example.com/{index}",
                    "address",
                ],
                input=json.dumps(self.response),
                text=True,
                check=True,
                capture_output=True,
            )

        with ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(write, range(18)))
        self.assertEqual(len(load_cache(self.here)["results"]), 18)

    def test_failed_update_preserves_previous_file(self):
        store_result(self.url, "address", self.response)
        path = self.cache / "cache.json"
        before = path.read_bytes()
        with self.assertRaises(TypeError), edit_cache() as state:
            state["results"][self.url]["address"] = object()
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual({p.name for p in self.cache.iterdir()}, {"cache.json", "cache.lock"})

    def test_corrupt_cache_is_not_overwritten(self):
        self.cache.mkdir()
        path = self.cache / "cache.json"
        path.write_text("broken")
        with self.assertRaises(json.JSONDecodeError):
            store_result(self.url, "address", self.response)
        self.assertEqual(path.read_text(), "broken")

    def test_failed_replace_cleans_up_temporary_file(self):
        store_result(self.url, "address", self.response)
        path = self.cache / "cache.json"
        before = path.read_bytes()
        with (
            patch("corpus_cache.os.replace", side_effect=OSError("interrupted")),
            self.assertRaises(OSError),
        ):
            store_result(self.url, "browser", self.response)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual({p.name for p in self.cache.iterdir()}, {"cache.json", "cache.lock"})

    def test_entry_points_restore_after_worktree_cleanup_without_lookups(self):
        self.seed_legacy()
        load_cache(self.here)
        shutil.rmtree(self.work)
        for name in [
            "check.py",
            "assemble.py",
            "corpus_cache.py",
            "lookups.mjs",
            "rows.mjs",
            "findings.csv",
        ]:
            shutil.copy2(HERE / name, self.here / name)
        check = subprocess.run(
            [sys.executable, "-I", str(self.here / "check.py")],
            text=True,
            capture_output=True,
            check=True,
        )
        self.assertIn("checked 0 address(es)", check.stdout)
        (self.work / "match.json").write_text("{}")
        subprocess.run(
            [sys.executable, "-I", str(self.here / "assemble.py")], check=True, capture_output=True
        )
        with (self.work / "extension-test-urls.csv").open() as source:
            row = next(csv.DictReader(source))
        self.assertEqual(row["lookup_answer"], "example for example")
        self.assertEqual(row["http_status"], "200")
        for mode in [[], ["--browser", str(self.root / "inputs.json")]]:
            (self.root / "inputs.json").write_text(json.dumps({"A001": {"text": "test"}}))
            run = subprocess.run(
                ["node", str(self.here / "lookups.mjs"), *mode],
                check=True,
                capture_output=True,
                text=True,
                env={**os.environ, "LOOKUP_API": "http://127.0.0.1:1/never-called"},
            )
            self.assertIn("asked 0; 2 answers on record", run.stdout)


if __name__ == "__main__":
    unittest.main()
