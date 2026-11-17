"""Build fingerprints offline from the bulk store, with progress and per-stage spans."""

import hashlib
import json
import random
import sqlite3
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping
from contextlib import closing
from dataclasses import asdict
from itertools import batched
from pathlib import Path
from typing import Any

from thenwhat.backfill.trial_fingerprint import AcronymContext, Words, fingerprint_of
from thenwhat.backfill.trial_terms import words_of
from thenwhat.measure.spans import measured
from thenwhat.store.form import R2_PREFIX, Record, payload_value
from thenwhat.work.errors import BackfillError

_CORPUS = """
SELECT t.id, t.title, t.conditions,
       json_extract(p.body, '$.protocolSection.identificationModule.officialTitle') AS official,
       CASE WHEN p.body IS NULL THEN t.payload_sha256 END AS object_hash
FROM registry_trial t LEFT JOIN payload p ON p.sha256 = t.payload_sha256
"""
_BATCH = 100


def _matches(text: str, terms: Mapping[str, set[Words]]) -> set[Words]:
    words = words_of(text)
    return {
        term
        for index, word in enumerate(words)
        for term in terms.get(word, ())
        if words[index : index + len(term)] == term
    }


def _protocol(body: str | None, checksum: str, payloads: Path | None) -> dict[str, Any]:
    if body is not None:
        return json.loads(body).get("protocolSection", {})
    if payloads is None:
        raise BackfillError(f"Trial payload {checksum} needs the store's --payloads folder.")
    if len(checksum) != 64 or any(character not in "0123456789abcdef" for character in checksum):
        raise BackfillError("The store has an invalid trial payload checksum.")
    record = Record("payload", checksum, {"sha256": checksum})
    raw = (payloads / f"{R2_PREFIX}{checksum}").read_text(encoding="utf-8")
    return payload_value(record, raw).get("protocolSection", {})


def _sample(
    trials: Mapping[int, str | None], limit: int | None, extra: int, seed: int
) -> dict[int, str]:
    if limit is None:
        if extra:
            raise BackfillError("--acronym-sample needs --limit.")
        return dict.fromkeys(trials, "all")
    rng = random.Random(seed)
    selected = dict.fromkeys(rng.sample(list(trials), min(limit, len(trials))), "random")
    eligible = [row_id for row_id, acronym in trials.items() if acronym and row_id not in selected]
    selected.update(
        dict.fromkeys(rng.sample(eligible, min(extra, len(eligible))), "acronym_sample")
    )
    return selected


def _context(
    rows: Iterable[sqlite3.Row],
    candidates: Mapping[str, set[Words]],
    own_acronyms: Mapping[int, Words],
    payloads: Path | None,
    total: int,
    progress: Callable[[str], None],
) -> tuple[set[Words], Counter[Words], set[int]]:
    condition_terms: set[Words] = set()
    titles: Counter[Words] = Counter()
    own_title_hits: set[int] = set()
    for number, row in enumerate(rows, start=1):
        official = row["official"]
        if row["object_hash"] is not None:
            protocol = _protocol(None, row["object_hash"], payloads)
            official = protocol.get("identificationModule", {}).get("officialTitle")
        hits = _matches(row["title"], candidates) | _matches(official or "", candidates)
        titles.update(hits)
        if own_acronyms.get(row["id"]) in hits:
            own_title_hits.add(row["id"])
        for condition in json.loads(row["conditions"]):
            condition_terms.update(_matches(condition, candidates))
        if number % 50_000 == 0:
            progress(f"Checked titles and conditions for {number:,}/{total:,} trials.")
    return condition_terms, titles, own_title_hits


def run_fingerprints(
    store: Path,
    output: Path,
    word_lists: list[Path],
    *,
    payloads: Path | None,
    limit: int | None,
    acronym_sample: int,
    seed: int,
    max_other_titles: int,
    progress: Callable[[str], None],
) -> dict[str, Any]:
    with measured("trial_fingerprint.word_list"):
        word_list: set[Words] = set()
        word_list_hashes = {}
        for path in word_lists:
            raw = path.read_bytes()
            word_list_hashes[str(path)] = hashlib.sha256(raw).hexdigest()
            word_list.update(words_of(line) for line in raw.decode("utf-8").splitlines())
        word_list.discard(())
        if not word_list:
            raise BackfillError("Give a word list with words or names, one per line.")

    with closing(sqlite3.connect(f"{store.resolve().as_uri()}?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        db.execute("BEGIN")
        with measured("trial_fingerprint.select"):
            trials = dict(
                db.execute("SELECT id, acronym FROM registry_trial ORDER BY id").fetchall()
            )
            if not trials:
                raise BackfillError("The store has no registry trials. Give the bulk store file.")
            selected = _sample(trials, limit, acronym_sample, seed)
            own_acronyms = {row_id: words_of(trials[row_id] or "") for row_id in selected}
            candidates: dict[str, set[Words]] = defaultdict(set)
            for words in own_acronyms.values():
                if words:
                    candidates[words[0]].add(words)
        progress(
            f"Selected {len(selected):,} trials. Checking ambiguity across {len(trials):,} records."
        )

        with measured("trial_fingerprint.context", batch=len(trials)):
            condition_terms, titles, own_title_hits = _context(
                db.execute(_CORPUS), candidates, own_acronyms, payloads, len(trials), progress
            )

        terms_by_kind: Counter[str] = Counter()
        fit_by_kind: Counter[str] = Counter()
        rejections: Counter[str] = Counter()
        identifier_only: Counter[str] = Counter()
        records = 0
        staging = output / "fingerprints.jsonl.part"
        with staging.open("x", encoding="utf-8") as stream:
            for ids in batched(sorted(selected), _BATCH):
                placeholders = ", ".join("?" for _ in ids)
                with measured("trial_fingerprint.read", batch=len(ids)):
                    rows = db.execute(
                        f"""SELECT t.id, t.external_id, t.registry_name, t.interventions,
                            t.lead_sponsor_name, t.payload_sha256, p.body
                            FROM registry_trial t LEFT JOIN payload p ON p.sha256 = t.payload_sha256
                            WHERE t.id IN ({placeholders}) ORDER BY t.id""",
                        ids,
                    ).fetchall()
                with measured("trial_fingerprint.build", batch=len(rows)):
                    lines = []
                    for row in rows:
                        row_id = row["id"]
                        acronym = own_acronyms[row_id]
                        other_titles = titles[acronym] - (row_id in own_title_hits)
                        context = AcronymContext(
                            word_list, condition_terms, {acronym: other_titles}, max_other_titles
                        )
                        protocol = _protocol(row["body"], row["payload_sha256"], payloads)
                        terms = fingerprint_of(
                            row["external_id"],
                            interventions=json.loads(row["interventions"]),
                            protocol=protocol,
                            lead_sponsor_name=row["lead_sponsor_name"],
                            context=context,
                        )
                        cohort = selected[row_id]
                        terms_by_kind.update(term.kind for term in terms)
                        fit_by_kind.update(term.kind for term in terms if term.fit)
                        rejections.update(term.reason for term in terms if term.reason is not None)
                        if all(term.kind == "registry_number" or not term.fit for term in terms):
                            identifier_only[cohort] += 1
                        lines.append(
                            json.dumps(
                                {
                                    "registry": row["registry_name"],
                                    "number": row["external_id"],
                                    "cohort": cohort,
                                    "terms": [asdict(term) for term in terms],
                                },
                                ensure_ascii=False,
                            )
                            + "\n"
                        )
                with measured("trial_fingerprint.write", batch=len(rows)) as span:
                    stream.writelines(lines)
                    stream.flush()
                    span.wrote(len(lines))
                records += len(lines)
                progress(f"Built {records:,}/{len(selected):,} fingerprints.")

        if records != len(selected):
            raise BackfillError(f"Expected {len(selected):,} fingerprints, wrote {records:,}.")
        staging.rename(output / "fingerprints.jsonl")

    summary = {
        "store": str(store),
        "corpus": len(trials),
        "selected": dict(Counter(selected.values())),
        "fingerprints": records,
        "terms": dict(terms_by_kind),
        "fit": dict(fit_by_kind),
        "acronym_rejections": dict(rejections),
        "registry_number_only": dict(identifier_only),
        "sample_seed": seed,
        "max_other_titles": max_other_titles,
        "word_list_hashes": word_list_hashes,
    }
    with (output / "summary.json").open("x", encoding="utf-8") as stream:
        json.dump(summary, stream, indent=2)
        stream.write("\n")
    return summary
