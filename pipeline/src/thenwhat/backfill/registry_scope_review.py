"""Offline evidence receipts for protocol scope review.

A scope review receipt records, for one registry trial, which (regimen,
indication) pairs a reviewer identified and the verbatim registry quotes that
support each half of every pair.  This module only checks structure and that
quotes are literally present in supplied registry text; it does not judge
semantic correctness or publication eligibility.

Pure standard library; no network access, no mutation of inputs or files.
"""

import json
import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NoReturn

__all__ = [
    "SCHEMA_VERSION",
    "ScopePair",
    "ScopeReview",
    "confirm_protocol_evidence",
    "load_protocol_evidence",
    "load_scope_reviews",
    "validate_scope_review",
]

SCHEMA_VERSION = 1

_NCT_RE = re.compile(r"NCT[0-9]{8}")
_SHA256_RE = re.compile(r"[0-9a-f]{64}")

_DOCUMENT_FIELDS = frozenset({"schema_version", "reviews"})
_REVIEW_FIELDS = frozenset({"trial_id", "registry_sha256", "reviewed_by", "pairs"})
_PAIR_FIELDS = frozenset({"regimen", "indication", "intervention_quotes", "indication_quotes"})


@dataclass(frozen=True, slots=True)
class ScopePair:
    """One reviewed (regimen, indication) pair with its supporting quotes."""

    regimen: tuple[str, ...]
    indication: str
    intervention_quotes: tuple[str, ...]
    indication_quotes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ScopeReview:
    """An immutable scope review receipt for a single registry trial."""

    trial_id: str
    registry_sha256: str
    reviewed_by: str
    pairs: tuple[ScopePair, ...]


def load_protocol_evidence(path: Path) -> dict[str, dict[str, Any]]:
    """Read cached detailed protocols keyed by their registry identifiers."""
    records = json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_constant,
    )
    if not isinstance(records, dict) or not all(
        _NCT_RE.fullmatch(identifier)
        and isinstance(record, dict)
        and isinstance(record.get("protocolSection"), dict)
        for identifier, record in records.items()
    ):
        raise ValueError("Expected cached protocol records keyed by NCT identifier.")
    return records


def _scope_fields(protocol: dict[str, Any]) -> dict[str, Any]:
    """Study fields shared by the bulk and detailed registry requests."""
    identity = protocol.get("identificationModule") or {}
    design = protocol.get("designModule") or {}
    assignment = design.get("designInfo") or {}
    treatment = protocol.get("armsInterventionsModule") or {}
    return {
        "titles": (identity.get("briefTitle"), identity.get("officialTitle")),
        "conditions": (protocol.get("conditionsModule") or {}).get("conditions") or [],
        "study_type": design.get("studyType"),
        "purpose": assignment.get("primaryPurpose"),
        "intervention_model": assignment.get("interventionModel"),
        "arms": [
            {field: arm.get(field) for field in ("label", "type", "interventionNames")}
            for arm in treatment.get("armGroups") or []
        ],
        "interventions": [
            {field: item.get(field) for field in ("name", "type", "otherNames", "armGroupLabels")}
            for item in treatment.get("interventions") or []
        ],
    }


def _posted_date(protocol: dict[str, Any]) -> str | None:
    status = protocol.get("statusModule") or {}
    return (status.get("lastUpdatePostDateStruct") or {}).get("date")


def confirm_protocol_evidence(
    trial_id: str,
    stored: dict[str, Any],
    detailed: dict[str, Any],
    *,
    stored_update: str | None = None,
) -> None:
    """Require the same NCT, update date and shared scope before using detailed evidence."""
    try:
        bulk = stored.get("protocolSection") or {}
        full = detailed.get("protocolSection") or {}
        bulk_id = (bulk.get("identificationModule") or {}).get("nctId")
        full_id = (full.get("identificationModule") or {}).get("nctId")
        bulk_date = _posted_date(bulk) or stored_update
        full_date = _posted_date(full)
        before, after = _scope_fields(bulk), _scope_fields(full)
    except (AttributeError, TypeError) as error:
        raise ValueError(f"Malformed cached protocol for {trial_id}.") from error
    if (
        bulk_id != trial_id
        or full_id != trial_id
        or not bulk_date
        or bulk_date != full_date
        or (stored_update is not None and stored_update != bulk_date)
    ):
        raise ValueError(f"Cached evidence for {trial_id} differs from the stored trial version.")
    changed = [field for field in before if before[field] != after[field]]
    if changed:
        raise ValueError(
            f"Cached evidence for {trial_id} differs from the stored trial version "
            f"in {', '.join(changed)}."
        )


def _normalize(text: str) -> str:
    """Identity key: case-insensitive, whitespace-collapsed."""
    return " ".join(text.split()).casefold()


def _type_name(value: Any) -> str:
    return "null" if value is None else type(value).__name__


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key {key!r}")
        result[key] = value
    return result


def _reject_constant(name: str) -> NoReturn:
    raise ValueError(f"non-standard JSON constant {name!r} is not allowed")


def _check_fields(obj: Any, allowed: frozenset[str], where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise ValueError(f"{where}: expected a JSON object, got {_type_name(obj)}")
    unknown = sorted(set(obj) - allowed)
    if unknown:
        raise ValueError(f"{where}: unknown field(s) {', '.join(map(repr, unknown))}")
    missing = sorted(allowed - set(obj))
    if missing:
        raise ValueError(f"{where}: missing field(s) {', '.join(map(repr, missing))}")
    return obj


def _require_text(value: Any, where: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{where}: expected a string, got {_type_name(value)}")
    if not value.strip():
        raise ValueError(f"{where}: must not be empty or whitespace-only")
    return value


def _require_text_list(value: Any, where: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{where}: expected a JSON array, got {_type_name(value)}")
    if not value:
        raise ValueError(f"{where}: must contain at least one entry")
    return tuple(_require_text(item, f"{where}[{index}]") for index, item in enumerate(value))


def _parse_pair(raw: Any, where: str) -> ScopePair:
    obj = _check_fields(raw, _PAIR_FIELDS, where)
    regimen = _require_text_list(obj["regimen"], f"{where}.regimen")
    seen: dict[str, int] = {}
    for index, component in enumerate(regimen):
        key = _normalize(component)
        if key in seen:
            raise ValueError(
                f"{where}.regimen[{index}]: duplicate regimen component {component!r} "
                f"(same as regimen[{seen[key]}])"
            )
        seen[key] = index
    indication = _require_text(obj["indication"], f"{where}.indication")
    intervention_quotes = _require_text_list(
        obj["intervention_quotes"], f"{where}.intervention_quotes"
    )
    indication_quotes = _require_text_list(obj["indication_quotes"], f"{where}.indication_quotes")
    return ScopePair(
        regimen=regimen,
        indication=indication,
        intervention_quotes=intervention_quotes,
        indication_quotes=indication_quotes,
    )


def _pair_identity(pair: ScopePair) -> tuple[frozenset[str], str]:
    return frozenset(_normalize(c) for c in pair.regimen), _normalize(pair.indication)


def _parse_review(raw: Any, where: str) -> ScopeReview:
    if isinstance(raw, dict) and isinstance(raw.get("trial_id"), str):
        where = f"{where} (trial {raw['trial_id']!r})"
    obj = _check_fields(raw, _REVIEW_FIELDS, where)

    trial_id = _require_text(obj["trial_id"], f"{where}.trial_id")
    if not _NCT_RE.fullmatch(trial_id):
        raise ValueError(
            f"{where}.trial_id: {trial_id!r} is not a valid NCT identifier (NCT + 8 digits)"
        )

    digest = _require_text(obj["registry_sha256"], f"{where}.registry_sha256")
    if not _SHA256_RE.fullmatch(digest):
        raise ValueError(
            f"{where}.registry_sha256: {digest!r} is not a lowercase hex SHA-256 digest"
        )

    reviewed_by = _require_text(obj["reviewed_by"], f"{where}.reviewed_by")

    raw_pairs = obj["pairs"]
    if not isinstance(raw_pairs, list):
        raise ValueError(f"{where}.pairs: expected a JSON array, got {_type_name(raw_pairs)}")
    if not raw_pairs:
        raise ValueError(f"{where}.pairs: must contain at least one pair")

    pairs: list[ScopePair] = []
    identities: dict[tuple[frozenset[str], str], int] = {}
    for index, raw_pair in enumerate(raw_pairs):
        pair = _parse_pair(raw_pair, f"{where}.pairs[{index}]")
        identity = _pair_identity(pair)
        if identity in identities:
            raise ValueError(
                f"{where}.pairs[{index}]: duplicate pair (regimen {list(pair.regimen)!r}, "
                f"indication {pair.indication!r}) repeats pairs[{identities[identity]}]"
            )
        identities[identity] = index
        pairs.append(pair)

    return ScopeReview(
        trial_id=trial_id,
        registry_sha256=digest,
        reviewed_by=reviewed_by,
        pairs=tuple(pairs),
    )


def load_scope_reviews(path: Path) -> dict[str, ScopeReview]:
    """Load and structurally validate a scope review document.

    Returns a dict keyed by NCT identifier.  Raises ValueError for any
    unsupported, malformed, or ambiguous content.
    """
    source = Path(path)
    try:
        text = source.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{source}: not valid UTF-8 ({exc})") from exc
    try:
        document = json.loads(
            text,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"{source}: invalid JSON ({exc})") from exc
    except ValueError as exc:
        raise ValueError(f"{source}: {exc}") from exc

    where = str(source)
    obj = _check_fields(document, _DOCUMENT_FIELDS, where)
    version = obj["schema_version"]
    if type(version) is not int or version != SCHEMA_VERSION:
        raise ValueError(
            f"{where}: unsupported schema_version {version!r} (expected {SCHEMA_VERSION})"
        )
    raw_reviews = obj["reviews"]
    if not isinstance(raw_reviews, list):
        raise ValueError(f"{where}.reviews: expected a JSON array, got {_type_name(raw_reviews)}")

    reviews: dict[str, ScopeReview] = {}
    for index, raw_review in enumerate(raw_reviews):
        review = _parse_review(raw_review, f"{where}.reviews[{index}]")
        if review.trial_id in reviews:
            raise ValueError(
                f"{where}.reviews[{index}]: duplicate review record for trial {review.trial_id}"
            )
        reviews[review.trial_id] = review
    return reviews


def validate_scope_review(
    review: ScopeReview,
    *,
    trial_id: str,
    registry_sha256: str,
    source_text: Iterable[str],
) -> None:
    """Check a receipt is bound to the given registry record and its quotes.

    Raises ValueError if the receipt's trial ID or registry hash differs from
    the expected values, or if any quote is not an exact, case-sensitive,
    contiguous substring of at least one supplied source string.  Does not
    assess whether the pairs are semantically correct or publishable.
    """
    if not isinstance(review, ScopeReview):
        raise ValueError(f"expected a ScopeReview, got {_type_name(review)}")
    context = f"scope review for trial {review.trial_id}"
    if review.trial_id != trial_id:
        raise ValueError(f"{context}: trial ID does not match expected {trial_id!r}")
    if review.registry_sha256 != registry_sha256:
        raise ValueError(
            f"{context}: registry_sha256 {review.registry_sha256} does not match "
            f"expected {registry_sha256!r}"
        )
    if isinstance(source_text, (str, bytes)):
        raise ValueError(
            f"{context}: source_text must be an iterable of strings, not a single string"
        )
    sources = list(source_text)
    for index, item in enumerate(sources):
        if not isinstance(item, str):
            raise ValueError(f"{context}: source_text[{index}] is {_type_name(item)}, not a string")

    for pair_index, pair in enumerate(review.pairs):
        for kind in ("intervention_quotes", "indication_quotes"):
            for quote_index, quote in enumerate(getattr(pair, kind)):
                if not any(quote in source for source in sources):
                    raise ValueError(
                        f"{context}: pairs[{pair_index}].{kind}[{quote_index}] {quote!r} "
                        f"(regimen {list(pair.regimen)!r}, indication {pair.indication!r}) "
                        "is not an exact substring of any supplied source text"
                    )
