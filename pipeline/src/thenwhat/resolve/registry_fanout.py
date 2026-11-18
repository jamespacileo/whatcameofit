"""Supplement broad trial search with bounded title and sponsor queries."""

import re
import sqlite3
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from heapq import nsmallest
from typing import NamedTuple

from thenwhat.backfill.trial_terms import words_of
from thenwhat.resolve.stored import is_a_kind_of_care, keys_written, parts_of

_TITLE_SCAN = 80
_ROLE_LIMIT = 8
_SPONSOR_SCAN = 5000
_STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "of",
        "on",
        "or",
        "the",
        "to",
        "using",
        "with",
    ]
    + [
        "adult",
        "adults",
        "advanced",
        "clinical",
        "cohort",
        "data",
        "efficacy",
        "phase",
        "trial",
        "study",
    ]
    + [
        "participants",
        "patient",
        "patients",
        "result",
        "results",
        "safety",
        "treatment",
        "versus",
        "vs",
    ]
)
_SPONSOR_SUFFIX = frozenset(
    ["co", "company", "corp", "corporation", "gmbh", "inc", "llc", "limited", "ltd", "plc", "sa"]
)
_PHASE = re.compile(r"\bphase\s*(iv|iii|ii|i|[1-4])(?:[ab])?\b", re.IGNORECASE)
_ROMAN = {"i": "1", "ii": "2", "iii": "3", "iv": "4"}
_FIELDS = """r.external_id, r.title, r.conditions, r.intervention_names, r.acronym,
             r.phases, r.overall_status"""


@dataclass(frozen=True, slots=True)
class TrialHit:
    external_id: str
    strategy: str


class _Trial(NamedTuple):
    external_id: str
    title: str
    conditions: str
    interventions: str
    acronym: str | None
    phases: str
    status: str | None


def _terms(value: str) -> set[str]:
    return {word for word in words_of(value) if word not in _STOP}


def _phrases(words: tuple[str, ...]) -> list[tuple[str, ...]]:
    phrases = [
        words[start : start + length]
        for length in (4, 3, 2)
        for start in range(len(words) - length + 1)
    ]
    return [
        phrase
        for phrase in dict.fromkeys(phrases)
        if sum(word not in _STOP for word in phrase) >= 2 and len("".join(phrase)) >= 8
    ][:12]


def _phase_keys(value: str) -> set[str]:
    return {"phase" + _ROMAN.get(token.lower(), token.lower()) for token in _PHASE.findall(value)}


def _score(
    row: _Trial,
    *,
    query: set[str],
    condition: set[str],
    phrases: list[tuple[str, ...]],
    phases: set[str],
) -> tuple[int, int, int, str]:
    title_tokens = words_of(" ".join(part for part in (row.title, row.acronym) if part))
    title_text = " " + " ".join(title_tokens) + " "
    intervention_words = _terms(row.interventions)
    condition_words = _terms(row.conditions)
    title_span = max(
        (len(phrase) for phrase in phrases if f" {' '.join(phrase)} " in title_text),
        default=0,
    )
    contextual = len(condition & condition_words)
    query_fit = len(query & (set(title_tokens) | intervention_words | condition_words))
    score = (
        3 * title_span
        + 3 * len(query & intervention_words)
        + 2 * query_fit
        + 2 * contextual
        + int(any(phase in row.phases.lower() for phase in phases))
        + int(
            query_fit > 0 and (row.status or "").lower() in {"active_not_recruiting", "completed"}
        )
    )
    return -score, -contextual, -query_fit, row.external_id


def _rows_matching_title(
    db: sqlite3.Connection, phrases: list[tuple[str, ...]]
) -> Iterable[_Trial]:
    if not phrases:
        return ()
    quoted = " OR ".join('"' + " ".join(phrase) + '"' for phrase in phrases)
    rows = db.execute(
        f"""SELECT {_FIELDS} FROM registry_trial_fts
            JOIN registry_trial r ON r.id = registry_trial_fts.rowid
            WHERE registry_trial_fts MATCH ? ORDER BY rank, external_id LIMIT ?""",
        (f"title : ({quoted})", _TITLE_SCAN),
    )
    return (_Trial(*row) for row in rows)


def _rows_matching_words(db: sqlite3.Connection, words: set[str]) -> Iterable[_Trial]:
    tokens = [word for word in sorted(words) if len(word) >= 2 and not word.isdecimal()]
    if not tokens:
        return ()
    quoted = " OR ".join(f'"{word}"' for word in tokens)
    rows = db.execute(
        f"""SELECT {_FIELDS} FROM registry_trial_fts
            JOIN registry_trial r ON r.id = registry_trial_fts.rowid
            WHERE registry_trial_fts MATCH ? ORDER BY rank, external_id LIMIT ?""",
        (quoted, _ROLE_LIMIT),
    )
    return (_Trial(*row) for row in rows)


def sponsor_words(sponsor: str) -> tuple[str, ...]:
    return tuple(word for word in words_of(sponsor) if word not in _SPONSOR_SUFFIX)


def _rows_matching_sponsor(db: sqlite3.Connection, sponsor: str) -> Iterable[_Trial]:
    tokens = sponsor_words(sponsor)
    if not tokens or len(tokens[0]) < 4:
        return ()
    sponsor_pattern = "%" + "%".join(tokens[:2]) + "%"
    rows = db.execute(
        f"""SELECT {_FIELDS} FROM registry_trial r
            WHERE lower(r.lead_sponsor_name) LIKE ? ORDER BY external_id LIMIT ?""",
        (sponsor_pattern, _SPONSOR_SCAN),
    )
    return (_Trial(*row) for row in rows)


def _rows_matching_product(
    db: sqlite3.Connection, interventions: Sequence[str]
) -> Iterable[_Trial]:
    names = {
        key
        for intervention in interventions
        for part in parts_of(intervention)
        if not is_a_kind_of_care(part)
        for key in keys_written(part)
        if key not in {"placebo", "control", "other", "sham"}
    }
    if not names:
        return ()
    placeholders = ", ".join("?" for _ in names)
    rows = db.execute(
        f"""SELECT {_FIELDS} FROM registry_trial r
            WHERE lower(r.search_name) IN ({placeholders}) ORDER BY external_id LIMIT ?""",
        (*sorted(names), _SPONSOR_SCAN),
    )
    return (_Trial(*row) for row in rows)


def trial_fanout(
    db: sqlite3.Connection,
    terms: str,
    *,
    indication: str,
    sponsor: str = "",
    context: str = "",
    interventions: Sequence[str] = (),
) -> list[TrialHit]:
    """Rank separate title-phrase and sponsor-constrained lists on a stored trial corpus.

    The sponsor lane can find a result filed under earlier names or development codes.
    Candidate retrieval leaves the article-to-study decision to the verifier.
    """
    query = _terms(terms)
    if not query:
        return []
    requested_phases = _phase_keys(terms)
    phases = requested_phases or _phase_keys(context)
    condition = _terms(indication)
    phrases = _phrases(words_of(terms))

    def rank(row: _Trial) -> tuple[int, int, int, str]:
        return _score(row, query=query, condition=condition, phrases=phrases, phases=phases)

    identifiers = sorted(set(re.findall(r"\bNCT[0-9]{8}\b", terms.upper())))
    found = {
        external_id: TrialHit(external_id, "registry_id")
        for identifier in identifiers
        for (external_id,) in db.execute(
            "SELECT external_id FROM registry_trial WHERE external_id = ?", (identifier,)
        )
    }
    sponsor_rows = list(_rows_matching_sponsor(db, sponsor))
    for strategy, rows in (
        ("title_phrase", _rows_matching_title(db, phrases)),
        ("sponsor_context", sponsor_rows),
        ("registered_product", _rows_matching_product(db, interventions)),
        ("query_words", _rows_matching_words(db, query)),
    ):
        scored = ((rank(row), row.external_id) for row in rows)
        for (score, contextual, query_fit, _), external_id in nsmallest(_ROLE_LIMIT, scored):
            if score >= 0 or contextual == query_fit == 0:
                continue
            found.setdefault(external_id, TrialHit(external_id, strategy))
    # A small sponsor's registry title may use an old product code and an umbrella
    # condition. Keep the explicitly requested phase for the verifier in that case.
    if len(sponsor_rows) <= _ROLE_LIMIT and requested_phases:
        for row in sponsor_rows:
            if any(phase in row.phases.lower() for phase in requested_phases):
                found.setdefault(row.external_id, TrialHit(row.external_id, "sponsor_phase"))
    return list(found.values())
