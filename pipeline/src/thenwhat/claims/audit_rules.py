"""Sample membership and clearance eligibility for sampled publication audits.

Persistence resolves judgement provenance and staleness before these pure functions are called.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from fractions import Fraction
from typing import Literal

Refusal = Literal["unfinished", "threshold_unset", "over_threshold"]


@dataclass(frozen=True, slots=True)
class AuditAssessment:
    """Outcome of an audit; ``clear`` is empty whenever ``refusal`` is set."""

    clear: tuple[int, ...]
    wrong: tuple[int, ...]
    missing: tuple[int, ...]
    refusal: Refusal | None


def draw_claims(claim_ids: Iterable[int], *, size: int, seed: str) -> tuple[int, ...]:
    """Return a sorted sample of ``size`` claims, reproducible from ``seed``.

    Each claim is ranked by a SHA-256 digest of the seed and its ID, so the draw does not depend
    on input order. A size at or above the population size returns the whole population.
    """
    population = _claim_ids(claim_ids, "population")
    if type(size) is not int or size < 1:
        raise ValueError(f"sample size must be a positive integer, got {size!r}")
    if not isinstance(seed, str) or not seed:
        raise ValueError("seed must be a non-empty string")

    seed_bytes = seed.encode("utf-8")
    prefix = len(seed_bytes).to_bytes(8, "big") + seed_bytes

    def rank(claim_id: int) -> tuple[bytes, int]:
        digest = hashlib.sha256(prefix + str(claim_id).encode("ascii")).digest()
        return digest, claim_id

    return tuple(sorted(sorted(population, key=rank)[:size]))


def assess_release(
    population: Iterable[int],
    sampled: Iterable[int],
    judgements: Mapping[int, bool],
    *,
    max_wrong_share: Decimal | None,
) -> AuditAssessment:
    """Decide which claims of a frozen population may be released after an audit.

    A complete audit of the whole population clears the right claims at any error share. A
    partial sample must be fully judged and its wrong share must be at or below
    ``max_wrong_share``; then every claim except the wrong ones is cleared.
    """
    population_ids = _claim_ids(population, "population")
    sample_ids = _claim_ids(sampled, "sample")
    outside = set(sample_ids) - set(population_ids)
    if outside:
        raise ValueError(f"sample contains claims outside the population: {sorted(outside)}")
    _check_threshold(max_wrong_share)

    sample_set = set(sample_ids)
    for claim_id, verdict in judgements.items():
        if type(claim_id) is not int or claim_id not in sample_set:
            raise ValueError(f"judgement for claim not in the sample: {claim_id!r}")
        if type(verdict) is not bool:
            raise ValueError(f"judgement for claim {claim_id} is not a boolean: {verdict!r}")

    wrong = tuple(c for c in sample_ids if c in judgements and not judgements[c])
    missing = tuple(c for c in sample_ids if c not in judgements)

    if missing:
        return AuditAssessment(clear=(), wrong=wrong, missing=missing, refusal="unfinished")

    if sample_set == set(population_ids):
        right = tuple(c for c in sample_ids if judgements[c])
        return AuditAssessment(clear=right, wrong=wrong, missing=(), refusal=None)

    if max_wrong_share is None:
        return AuditAssessment(clear=(), wrong=wrong, missing=(), refusal="threshold_unset")

    if Fraction(len(wrong), len(sample_ids)) > Fraction(max_wrong_share):
        return AuditAssessment(clear=(), wrong=wrong, missing=(), refusal="over_threshold")

    wrong_set = set(wrong)
    clear = tuple(c for c in population_ids if c not in wrong_set)
    return AuditAssessment(clear=clear, wrong=wrong, missing=(), refusal=None)


def _claim_ids(claim_ids: Iterable[int], label: str) -> tuple[int, ...]:
    """Return the IDs sorted, rejecting empty input, non-positive or non-int IDs and duplicates."""
    ids = tuple(claim_ids)
    if not ids:
        raise ValueError(f"{label} is empty")
    for claim_id in ids:
        if type(claim_id) is not int or claim_id < 1:
            raise ValueError(f"{label} contains an invalid claim ID: {claim_id!r}")
    if len(set(ids)) != len(ids):
        raise ValueError(f"{label} contains duplicate claim IDs")
    return tuple(sorted(ids))


def _check_threshold(max_wrong_share: Decimal | None) -> None:
    if max_wrong_share is None:
        return
    if not isinstance(max_wrong_share, Decimal) or not max_wrong_share.is_finite():
        raise ValueError(f"maximum wrong share must be a finite Decimal: {max_wrong_share!r}")
    if not Decimal(0) <= max_wrong_share <= Decimal(1):
        raise ValueError(f"maximum wrong share must be between 0 and 1: {max_wrong_share}")
